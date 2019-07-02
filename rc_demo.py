"""
Remote Control Demo

Use this script to control the vehicle from a separate computer over WiFi, no phone required.

You can send movement commands via a connected USB gamepad or your keyboard.

This script uses an RTP stream from the vehicle to create an opencv window.
"""
# prep for python 3.0
from __future__ import absolute_import
from __future__ import print_function
import argparse
import os
import threading
import time

# Include rtp when importing opencv so we can process the video stream from the vehicle.
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = "protocol_whitelist;file,rtp,udp"
import cv2  # pylint: disable=import-error

from skydio.comms.http_client import HTTPClient
from skydio.comms.udp_link import UDPLink
from skydio.input_devices.gamepad import Gamepad

# Hit q to exit the program
QUIT = ord('q')

# Key mapping for controlling the drone
UP = ord('i')
DOWN = ord('k')
ROTATE_LEFT = ord('j')
ROTATE_RIGHT = ord('l')
LEFT = ord('a')
RIGHT = ord('d')
FORWARD = ord('w')
BACK = ord('s')
GIMBAL_UP = ord('r')
GIMBAL_DOWN = ord('f')


def key_to_command(key):
    """
    Convert a keycode to a movement command tuple.
    """
    # The format of the command is [vx, vy, vz, yaw_rate, pitch_rate]
    if key == FORWARD:
        cmd = [1, 0, 0, 0, 0]
    elif key == BACK:
        cmd = [-1, 0, 0, 0, 0]
    elif key == LEFT:
        cmd = [0, 1, 0, 0, 0]
    elif key == RIGHT:
        cmd = [0, -1, 0, 0, 0]
    elif key == UP:
        cmd = [0, 0, 1, 0, 0]
    elif key == DOWN:
        cmd = [0, 0, -1, 0, 0]
    elif key == ROTATE_LEFT:
        cmd = [0, 0, 0, 1, 0]
    elif key == ROTATE_RIGHT:
        cmd = [0, 0, 0, -1, 0]
    elif key == GIMBAL_UP:
        cmd = [0, 0, 0, 0, -1]
    elif key == GIMBAL_DOWN:
        cmd = [0, 0, 0, 0, 1]
    else:
        cmd = [0, 0, 0, 0, 0]
    return cmd


def main():
    parser = argparse.ArgumentParser(
        description="Control R1 from a computer with a connected gamepad.")
    parser.add_argument('--baseurl', metavar='URL', default='http://192.168.10.1',
                        help='the url of the vehicle')

    parser.add_argument('--skill-key', required=True, type=str,
                        help='name of the RemoteControl skill to run on the vehicle. '
                        'e.g. my_skillset.remote_control.RemoteControl')

    # NOTE: you'll need a token file in order to connect to a simulator.
    # Tokens are NOT required for real R1s.
    parser.add_argument('--token-file',
                        help='path to the auth token for your simulator')

    parser.add_argument('--takeoff', action='store_true',
                        help='send a takeoff command (must be pilot)')

    parser.add_argument('--land', action='store_true',
                        help='send a land command (must be pilot)')

    parser.add_argument('--update-skillsets-email', type=str,
                        help='The email of the user to get skillsets for and send them to the '
                             'vehicle (must be pilot)')
    parser.add_argument('--skydio-api-url', type=str, help='Override the skydio api url')

    parser.add_argument('--stream', choices=['h264', 'jpeg'], default='jpeg',
                        help='The video stream type that the vehicle should produce')

    args = parser.parse_args()

    if 'sim' in args.baseurl:
        # Due to Network Address Translation, RTP tends not to work on the open internet.
        # The sim will send packets, but your firewall will reject them.
        # You may be able to add port-forwarding to your firewall to fix this.
        raise RuntimeError('RTP streaming is not supported in the simulator yet.')

    if args.stream == 'h264':
        # H264 is the 720P 15fps h264 encoded stream directly from the camera.
        stream_settings = {'source': 'H264', 'port': 55004}
        # TODO: this stream seems like have client-induced lag
        # Perhaps due to incorrect timestamps.
        stream_file = 'h264_stream.sdp'
    elif args.stream == 'jpeg':
        # NATIVE is the raw images, though we convert to 240p jpeg by default before sending.
        stream_settings = {'source': 'NATIVE', 'port': 55004}
        stream_file = 'jpeg_stream.sdp'
    else:
        raise ValueError('Unknown stream format {}'.format(args.stream))

    # Create the client to use for all requests.
    client = HTTPClient(args.baseurl,
                        pilot=True,
                        token_file=args.token_file,
                        stream_settings=stream_settings)

    if not client.check_min_api_version():
        print('Your vehicle is running an older api version.'
              ' Update recommended in order to enable streaming.')

    if args.land:
        client.land()
        # Dont do anything else after landing.
        return

    if args.update_skillsets_email:
        client.update_skillsets(args.update_skillsets_email,
                                api_url=args.skydio_api_url)

    # Periodically poll the status endpoint to keep ourselves the active pilot.
    def update_loop():
        while True:
            client.update_pilot_status()
            time.sleep(2)
    status_thread = threading.Thread(target=update_loop)
    status_thread.setDaemon(True)
    status_thread.start()

    # Create a low-latency udp link for quickly sending messages to the vehicle.
    remote_address = client.get_udp_link_address()
    link = UDPLink(client.client_id, local_port=50112, remote_address=remote_address)

    # Connect the UDPLink to the vehicle before trying to takeoff.
    link.connect()

    if args.takeoff:
        # Ensure that the vehicle has taken off before continuing.
        client.takeoff()

    if Gamepad.available():
        controller = Gamepad()
    else:
        print('USB gamepad not available, falling back to using keyboard input instead.')
        controller = None

    # Switch into the RemoteControl skill so that our commands are followed.
    # If the skill isn't on the vehicle, the commands will be ignored.
    client.set_skill(args.skill_key)

    # Create an opencv video input source from the RTP stream description file.
    cap = cv2.VideoCapture(stream_file)

    while True:
        # Get a frame and show it.
        _, frame = cap.read()
        cv2.imshow('skydio', frame)
        key = cv2.waitKey(66)

        # Quit the program if you press Q
        if key & 0xff == QUIT:
            break

        # Get the current values for the command axes, either from the gamepad or the keyboard.
        # Axis values range from -1 to 1
        if controller:
            cmd_axes = controller.get_command()
        else:
            cmd_axes = key_to_command(key)

        # Scale each axis into the correct units.
        scales = [
            10,  # x-velocity [m/s]
            10,  # y-velocity [m/s]
            10,  # z-velocity [m/s]
            1,  # yaw-rate [rad/s]
            1,  # pitch-rate [rad/s]
        ]
        request = {}
        request['move'] = [scale * axis for scale, axis in zip(scales, cmd_axes)]

        # Continously send movement commands to the Gamepad skill.
        link.send_json(args.skill_key, request)


if __name__ == '__main__':
    main()
