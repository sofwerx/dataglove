#!/usr/bin/env python
# pylint: skip-file
"""
Skydio HTTP Client
v0.2

Communicate with a vehicle using HTTP apis.
"""

# Prep for python3
from __future__ import absolute_import
from __future__ import print_function

import base64
import json
import os
import requests
import sys
import threading
import time
from uuid import uuid4

try:
    # Python 3
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse


def fmt_out(fmt, *args, **kwargs):
    """ Helper for printing formatted text to stdout. """
    sys.stdout.write(fmt.format(*args, **kwargs))
    sys.stdout.flush()


def fmt_err(fmt, *args, **kwargs):
    """ Helper for printing formatted text to stderr. """
    sys.stderr.write(fmt.format(*args, **kwargs))
    sys.stderr.flush()


# Gstreamer pipeline description for the vehicle to produce an MJPEG stream over RTP.
JPEG_RTP = """
videoscale ! video/x-raw, width=360, height=240 ! videoconvert ! video/x-raw, format=YUY2
! jpegenc ! rtpjpegpay ! udpsink host={} port={} sync=false
""".replace('\n', ' ')


class HTTPClient(object):
    """
    HTTP client for communicating with a Skydio drone.

    Use this to connect a laptop over Wifi or an onboard computer over ethernet.

    Args:
        baseurl (str): The url of the vehicle.
            If you're directly connecting to a real R1 via WiFi, use 192.168.10.1
            If you're connected to a simulator over the Internet, use https://sim####.sim.skydio.com

        client_id (str): A unique id for this remote user. Used to identify the same device
            accross different runs or different connection methods. Defaults to a new uuid.

        pilot (bool): Set to True in order to directly control the drone. Disables phone access.

        token_file (str): Path to a file that contains the auth token for simulator access.

        stream_settings (dict): Configuration for receiving an RTP video stream.
            This feature is coming soon to R1 and will not work in the simulator.
    """

    def __init__(self, baseurl, client_id=None, pilot=False, token_file=None, stream_settings=None):
        self.client_id = client_id or str(uuid4())
        self.baseurl = baseurl
        self.access_token = None
        self.session_id = None
        self.access_level = None
        self.stream_settings = stream_settings
        self._authenticate(pilot, token_file)

    def _authenticate(self, pilot=False, token_file=None):
        """ Request an access token from the vehicle. If using a sim, a token_file is required. """
        request = {
            'client_id': self.client_id,
            'requested_level': (8 if pilot else 4),
            'commandeer': True,
        }

        if token_file:
            if not os.path.exists(token_file):
                fmt_err("Token file does not exist: {}\n", token_file)
                sys.exit(1)

            with open(token_file, 'r') as tokenf:
                token = tokenf.read()
                request['credentials'] = token.strip()

        response = self.request_json('authentication', request)
        self.access_level = response.get('accessLevel')
        if pilot and self.access_level != 'PILOT':
            fmt_err("Did not successfully auth as pilot\n")
            sys.exit(1)
        self.access_token = response.get('accessToken')
        fmt_out("Received access token:\n{}\n", self.access_token)

    def update_skillsets(self, user_email, api_url=None):
        """
        Update the skillsets available on the vehicle without needing a Skydio Mobile App to do so.

        If this is the first time running this function on this computer an interactive prompt
        will be shown to get the login_code sent to the user_email. Subsequent requests should not.

        Be sure that the user has uploaded a skillset to the Developer Console with the com_link
        skill available. Based on the skillset name you use you will need to provide
        --skill-key <skillset_name>.com_link.ComLink to actually use the skill delivered
        by this function.

        Args:
            user_email (str): The user to download skillsets for, this should match the email
                    used on the Developer Console and on Mobile Apps
            api_url (str): [optional] Override the Skydio Cloud API url to use

        """
        from skydio.cloud.update_util import update_cloud_config_on_vehicle

        return update_cloud_config_on_vehicle(user_email=user_email,
                                              vehicle_url=self.baseurl,
                                              vehicle_access_token=self.access_token,
                                              cloud_url=api_url)

    def request_json(self, endpoint, json_data=None, timeout=20):
        """ Send a GET or POST request to the vehicle and get a parsed JSON response.

        Args:
            endpoint (str): the path to request.
            json_data (dict): an optional JSON dictionary to send.
            timeout (int): number of seconds to wait for a response.

        Raises:
            HTTPError: if the server responds with 4XX or 5XX status code
            IOError: if the response body cannot be read.
            RuntimeError: if the response is poorly formatted.

        Returns:
            dict: the servers JSON response
        """
        url = '{}/api/{}'.format(self.baseurl, endpoint)
        headers = {'Accept': 'application/json'}
        if self.access_token:
            headers['Authorization'] = 'Bearer {}'.format(self.access_token)
        if json_data is not None:
            headers['Content-Type'] = 'application/json'
            res = requests.post(url, json=json_data, headers=headers)
        else:
            res = requests.get(url, headers=headers)

        try:
            res.raise_for_status()
        except requests.HTTPError as err:
            print(err.message)
            raise

        if res.headers['Content-Type'] == 'application/json':
            try:
                reply = res.json()
            except ValueError as err:
                print('unable to decode json')
                raise
            return reply['data']
        return res

    def send_custom_comms(self, skill_key, data, no_response=False):
        """
        Send custom bytes to the vehicle and optionally return a response

        Args:
            skill_key (str): The identifer for the Skill you want to receive this message.
            data (bytes): The payload to send.
            no_response (bool): Set this to True if you don't want a response.

        Returns:
            dict: a dict with metadata for the response and a 'data' field, encoded by the Skill.
        """

        rpc_request = {
            'data': base64.b64encode(data),
            'skill_key': skill_key,
            'no_response': no_response,  # this key is option and defaults to False
        }

        # Post rpc to the server as json.
        try:
            rpc_response = self.request_json('custom_comms', rpc_request)
        except Exception as error:  # pylint: disable=broad-except
            fmt_err('Comms Error: {}\n', error)
            return None

        # Parse and return the rpc.
        if rpc_response:
            if 'data' in rpc_response:
                rpc_response['data'] = base64.b64decode(rpc_response['data'])
        return rpc_response

    def update_pilot_status(self):
        """ Ping the vehicle to keep session alive and get status back.

        The session will expire after 10 seconds of inactivity from the pilot.
        If the session expires, the video stream will stop.
        """
        args = {
            'inForeground': True,
            'mediaMode': 'FLIGHT_CONTROL',
            'recordingMode': 'VIDEO_4K_30FPS',
            'takeoffType': 'GROUND_TAKEOFF',
            'wouldAcceptPilot': True,
        }
        if self.session_id:
            args['sessionId'] = self.session_id
        if self.stream_settings:
            args['streamSettings'] = self.stream_settings
        response = self.request_json('status', args)
        self.session_id = response['sessionId']
        return response

    def takeoff(self):
        """ Request takeoff. Blocks until flying. """
        if self.access_level != 'PILOT':
            fmt_err('Cannot takeoff: not pilot\n')
            return

        self.update_pilot_status()
        self.disable_faults()

        while True:
            time.sleep(1)  # downsample to prevent spamming the endpoint
            phase = self.update_pilot_status().get('flightPhase')
            if not phase:
                continue
            fmt_out('flight phase = {}\n', phase)
            if phase == 'READY_FOR_GROUND_TAKEOFF':
                fmt_out('Publishing ground takeoff\n')
                self.request_json('async_command', {'command': 'ground_takeoff'})
            elif phase == 'FLYING':
                fmt_out('Flying.\n')
                return
            else:
                # print the active faults
                fmt_out('Faults = {}\n', ','.join(self.get_blocking_faults()))

    def land(self):
        """ Land the vehicle. Blocks until on the ground. """
        if self.access_level != 'PILOT':
            fmt_err('Cannot land: not pilot\n')
            return

        phase = 'FLYING'
        while phase == 'FLYING':
            fmt_out('Sending LAND\n')
            self.request_json('async_command', {'command': 'land'})
            time.sleep(1)
            new_phase = self.update_pilot_status().get('flightPhase')
            if not new_phase:
                continue
            phase = new_phase

    def set_skill(self, skill_key):
        """ Request a specific skill to be active. """
        if self.access_level != 'PILOT':
            fmt_err('Cannot switch skills: not pilot\n')
            return
        fmt_out("Requesting {} skill\n", skill_key)
        endpoint = 'set_skill/{}'.format(skill_key)
        self.request_json(endpoint, {'args': {}})

    def get_blocking_faults(self):
        faults = self.request_json('active_faults').get('faults', {})
        return [f['name'] for f in faults.values() if f['relevant']]

    def disable_faults(self):
        """ Tell the vehicle to ignore missing phone info. """
        faults = {
            # These faults occur if phone isn't connected via UDP
            'LOST_PHONE_COMMS_SHORT': 2,
            'LOST_PHONE_COMMS_LONG': 3,
        }
        for _, fault_id in faults.items():
            self.request_json('set_fault_override/{}'.format(fault_id),
                              {'override_on': True, 'fault_active': False})

    def check_min_api_version(self, major=18.0, minor=5.0):
        info = self.request_json('status')['config']['deployInfo']
        return info.get('api_version_major') >= major and info.get('api_version_minor') >= minor

    def get_udp_link_address(self):
        """ Get the dynamic port and hostname for the udp link. """
        resp = self.request_json('status')['config']
        udp_hostname = resp.get('lcmProxyUdpHostname')
        if not udp_hostname:
            udp_hostname = urlparse(self.baseurl).netloc.split(':')[0]
        udp_port = resp.get('lcmProxyUdpPort')
        return (udp_hostname, udp_port)

    def save_image(self, filename):
        """
        Fetch raw image data from the vehicle and and save it as png, using opencv.

        If you need to continuously fetch images from the vehicle, consider using RTP instead.
        """
        import cv2
        import numpy

        t1 = time.time()
        # Fetch the image metadata for the latest color image.
        data = self.request_json('channel/SUBJECT_CAMERA_RIG_NATIVE')
        t2 = time.time()
        fmt_out('Got metadata in {}ms\n', int(1000 * (t2 - t1)))
        images = data['json']['images']
        if not images:
            return

        # Download the raw pixel data from the vehicle's shared memory.
        # Note that this is not a high-speed image api, as it uses uncompressed
        # image data over HTTP.
        image = images[0]
        image_path = image['data']
        url = '{}/shm{}'.format(self.baseurl, image_path)
        try:
            res = requests.get(url)
            image_data = res.content
        except requests.HTTPError as err:
            fmt_err('Got error for url {} {}\n', image_path, err)
            return
        t3 = time.time()
        fmt_out('Got image data in {}ms\n', int(1000 * (t3 - t2)))

        # Convert and save as a PNG
        pixfmt = image['pixelformat']
        PIXELFORMAT_YUV = 1009
        PIXELFORMAT_RGB = 1002
        if pixfmt == PIXELFORMAT_YUV:
            bytes_per_pixel = 2
            conversion_format = cv2.COLOR_YUV2BGR_UYVY
        elif pixfmt == PIXELFORMAT_RGB:
            bytes_per_pixel = 3
            conversion_format = cv2.COLOR_RGB2BGR
        else:
            fmt_err('Unsupported pixelformat {}\n', pixfmt)
            return
        width = image['width']
        height = image['height']
        num_bytes = width * height * bytes_per_pixel
        input_array = numpy.array([numpy.uint8(ord(c)) for c in image_data[:num_bytes]])
        input_array.shape = (height, width, bytes_per_pixel)
        bgr_array = cv2.cvtColor(input_array, conversion_format)
        cv2.imwrite(filename, bgr_array)
        t4 = time.time()
        fmt_out('Saved image in {}ms\n', int(1000 * (t4 - t3)))

        return filename

    def set_run_mode(self, mode_name, set_default=False):
        if set_default:
            action = 'SET_DEFAULT'
        else:
            action = 'TERMINATE_AND_START'
        resp = self.request_json('runmode', {
            'run_mode_name': mode_name,
            'action': action,
        })
        print(resp)
