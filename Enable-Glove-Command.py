#!/usr/bin/env python
'''
        Data Glove Commander BT Handler
        James Andrews <jandrews7348@floridapoly.edu>
'''
import time
import sys
import bluetooth
from uuid import uuid4
from bluetooth.ble import DiscoveryService
from bluetooth import *

BaudRate = 19200
MaxBytes = 100000
interval = 100
uuid = "00001101-0000-1000-8000-00805f9b34fb"
addr = "00:80:E1:BC:4A:22"
server_sock=BluetoothSocket( RFCOMM )

currentPose = "__"
nearby_devices = bluetooth.discover_devices(lookup_names=True)
input = raw_input
isinterupted = False

def working():
        if (isinterupted == True):
                print(">> System interrupt")
                exit()

def SearchForDev():
        for addr, name in nearby_devices:
                print("%s:%s" % (addr, name))
                device = name
        if (len(nearby_devices)==0):
                print("[Err] Glove out of range!")
        elif (len(nearby_devices)==1):
                print("[OK] Found %d device" % len(nearby_devices))
        else:
                print("Found %d devices" % len(nearby_devices))
SearchForDev()

def connect():
        # Establish RFCOMM Link
        service_matches = find_service( uuid = uuid, address = addr )
        if (len(service_matches)) == 0:
                print("[Err] Unable to connect to glove! Exiting...")
                exit()
        elif (len(service_matches) == 1):
                first_match = service_matches[0]
                port = first_match["port"]
                name = first_match["name"]
                host = first_match["host"]
                print("[OK] Locked on to %s!" % (name))
connect()

client_sock, client_info = server_sock.accept()
print("[OK] Authenticated with", client_info)

def reciever():
        try:
                while True:
                        data = client_sock.recv(1024)
                        if len(data) == 0: break
                        if len(data) < MaxBytes: continue
                        print("received [%s]" % data)
        except IOError:
                print("[Err] An error has occoured in connecting to the device.")
                pass
reciever()

#Cleanup connections
client_sock.close()
server_sock.close()
print("disconnected")

exit()