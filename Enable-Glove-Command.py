#!/usr/bin/env python

# Data Glove Commander BT Handler
# James Andrews <jandrews7348@floridapoly.edu>
import time
import sys
#from bluetooth import *
import bluetooth
from uuid import uuid4
from bluetooth.ble import DiscoveryService
from bluetooth import *

addr = None
BaudRate = 19200
MaxBytes = 100000
interval = 100
#uuid = "00001101-0000-10000-8000-008055f9b34fb"
uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"
addr = "00:80:E1:BC:4A:22"
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
                print("Glove out of range!")
        elif (len(nearby_devices)==1):
                print("found %d device" % len(nearby_devices))
        else:
                print("found %d devices" % len(nearby_devices))
SearchForDev()

def connect():
        # Establish RFCOMM Link
        service_matches = find_service( uuid = uuid, address = addr )
        if (len(service_matches)) == 0:
                print("Unable to connect to glove! Exiting...")
                exit()
        elif (len(service_matches) == 1):
                print("Locked on to commander glove!")

connect()