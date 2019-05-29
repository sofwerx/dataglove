#!/usr/bin/env python

# Data Glove Commander BT Handler
# James Andrews <jandrews7348@floridapoly.edu>
import time
import sys
from bluetooth import *
from uuid import uuid4
from bluetooth.ble import DiscoveryService

addr = None
BaudRate = 19200
MaxBytes = 100000
interval = 100
UUID = "00001101-0000-10000-8000-008055f9b34fb"
currentPose = "__"
nearby_devices = bluetooth.discover_devices(lookup_names=True)
input = raw_input
isinterupted = False

def working():
        if (isinterupted == True):
                print(">> System interrupt")
                exit()

server_sock = BluetoothSocket( RFCOMM )
server_sock.bind(("",PORT_ANY))#Not secure, but quick
server_sock.listen(1)
port = server_sock.getsockname()[1]

advertise_service( server_sock, "SkydioHub",
                   service_id = UUID,
                   service_classes = [ UUID, SERIAL_PORT_CLASS ],
                   profiles = [ SERIAL_PORT_PROFILE ], 
#                   protocols = [ OBEX_UUID ] 
                    )
                   
print("Waiting for connection on port %d" % port)

client_sock, client_info = server_sock.accept()
print("Connected to: ", client_info)

def reciever():
        try:
                while True:
                        data = client_sock.recv(1024)
                        if len(data) == 0: break
                        print("%s" % data)
        except IOError:
                pass
        print("Connection lost!")
reciever()

#cleanup
client_sock.close()
server_sock.close()
print("all done")
