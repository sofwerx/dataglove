#!/usr/bin/env python

# Data Glove Commander BT Handler
# James Andrews <jandrews7348@floridapoly.edu>
import time
import sys
#from bluetooth import *
import bluetooth
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

def SearchForDev():
        for addr, name in nearby_devices:
                print("  %s - %s" % (addr, name))
        print("found %d devices" % len(nearby_devices))

        # bluetooth low energy scan
        service = DiscoveryService()
        devices = service.discover(2)

        for address, name in devices.items():
                print("{}:{}".format(name, address))

while (isinterupted == False):
        time.sleep(1)# Avoid Spamming stdout
        SearchForDev()