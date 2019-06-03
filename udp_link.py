"""
Skydio UDP link
v0.1

Send and receive messages with the R1 via udp socket.
"""
# Prep for python3
from __future__ import absolute_import
from __future__ import print_function

from collections import defaultdict
import json
import socket
import time

from skydio.types import custom_comms_pb2
from skydio.types import skybus_pb2
from skydio.types.multipart_msg_t import multipart_msg_t


# TODO: support packet chunking
MAX_PACKET_SIZE = 64000


class UDPLink(object):
    """
    UDPLink

    Low-latency packet-based comms with the vehicle over UDP.
    """

    def __init__(self, client_id, local_port, remote_address):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.settimeout(0.05)
        self.server_socket.bind(('', local_port))
        self.remote_address = remote_address

        # Prep a reuseable rpc
        self.request = custom_comms_pb2.CustomRpcRequest()
        self.request.request_id = 0
        self.request.version = 1

        # Setup the subcription list so we can receive data from the remote.
        self.subscription_list = skybus_pb2.SubscribedChannelList()
        self.subscription_list.client_id = client_id
        self.subscription_list.nonce = 1
        channels = [
            'PHONE_UDP_SUBSCRIPTION_ACK_PB',
            'CUSTOM_SKILL_RPC_RESPONSE_PB',
            'CUSTOM_SKILL_STATUS_PB',
        ]
        for channel in channels:
            self.subscription_list.channels.add().channel = channel

        self.channel_ids = defaultdict(int)

        # Track whether we've received the subscription ack.
        self.sub_ack = None

    def connect(self):
        """
        Make contact with the remote server and subscribe to our list of channels.
        """
        # Keep sending the list until we get an ack.
        while not self.sub_ack:
            self.subscription_list.nonce += 1
            self.send_proto(self.subscription_list, channel='PHONE_UDP_SUBSCRIPTION_LIST_PB')
            self.read()
            time.sleep(0.5)

    def send_json(self, skill_key, json_obj):
        """ Send json data to the skill. """
        self.send_rpc_data(skill_key, json.dumps(json_obj).encode('utf-8'))

    def send_rpc_data(self, skill_key, data):
        self.request.data = data
        self.request.request_id += 1
        self.request.skill_key = skill_key
        self.request.utime = int(time.time() * 1e6)
        self.send_proto(self.request, 'CUSTOM_SKILL_RPC_REQUEST_PB')

    def send_proto(self, proto, channel):
        data = proto.SerializeToString()
        self.send_chunk(data, channel)

    def send_chunk(self, chunk, channel):
        msg = multipart_msg_t()
        msg.id = self.channel_ids[channel]
        self.channel_ids[channel] += 1
        msg.chunk_data = chunk
        msg.channel = channel
        msg.chunk_size = len(msg.chunk_data)
        if msg.chunk_size > MAX_PACKET_SIZE:
            raise ValueError('Packet too large to send: {} bytes'.format(msg.chunk_size))
        msg.chunk_count = 1
        msg.chunk_index = 0
        msg.total_size = msg.chunk_size
        self.server_socket.sendto(msg.encode(), self.remote_address)

    def read(self):
        """
        Read packets from the remote, return a parsed message or None
        """
        try:
            data, address = self.server_socket.recvfrom(1024)
        except socket.timeout:
            return
        if address != self.remote_address:
            # Ignore packets from unexpected sources
            print('dropping packet from unknown address {}. {} expected'
                  .format(address, self.remote_address))
            return
        msg = multipart_msg_t.decode(data)
        if msg.chunk_count > 1:
            # TODO: support multi-chunk messages
            print('skipping {} with {} chunks'.format(msg.channel, msg.chunk_count))
        else:
            # Decode the chunk
            if msg.channel == 'PHONE_UDP_SUBSCRIPTION_ACK_PB':
                ack = skybus_pb2.SubscriptionAck.FromString(msg.chunk_data)
                self.sub_ack = ack
                return
            elif msg.channel == 'CUSTOM_SKILL_RPC_RESPONSE_PB':
                resp = custom_comms_pb2.CustomRpcResponse.FromString(msg.chunk_data)
                return resp
            elif msg.channel == 'CUSTOM_SKILL_STATUS_PB':
                status = custom_comms_pb2.CustomSkillStatus.FromString(msg.chunk_data)
                return status
            else:
                return
