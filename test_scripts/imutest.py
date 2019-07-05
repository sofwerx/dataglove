import serial
import time
import sys
import threading
import numpy as np

# © 2019 BeBop Sensors, Inc.
data = []

class GloveSerialListener(threading.Thread):
    def __init__(self, port):
        threading.Thread.__init__(self)

        self.glove = serial.Serial()
        self.glove.baudrate = 460800
        self.glove.port = '/dev/rfcomm0'
        self.glove.timeout = 1
        self.glove.open()

        self.data = []
        self.data_shared = []

    def parse(self, byte_to_parse):
        global data

        b = int.from_bytes(byte_to_parse, byteorder='big')
        #print(b)
        if b == 240:
            self.data = []
        elif b == 247:
            self.data.append(b)

            #might need some thread saftey here
            if (self.data[0] == 2):
                data = self.data

        else:
            self.data.append(b)

    def run(self):

        global data

        if self.glove.is_open:
            # data on
            self.glove.write(bytearray([176, 115, 1]))

            # usb mode
            #self.glove.write(bytearray([176, 118, 1]))

            # bluetooth mode
            self.glove.write(bytearray([176, 118, 2]))

            while True:
                self.parse(self.glove.read())

        else:
            self.close()

def main():
    data_glove_thread = GloveSerialListener('/dev/rfcomm0')
    data_glove_thread.start()

    #Wait for data
    if not data:
        while True:
            print("Waiting for data...")
            time.sleep(2)
            if data:
                break


    while True:

        time.sleep(1)
        if (data[0] == 2 and data[1] == 12):
            #Accelerometer Data
            print(data)
    data_glove_thread.close()

#MainLoop
while True:
    try:
        main()
    except(OSError):
        print("Failed to connect to glove. Retrying...")
        time.sleep(1)
    except(KeyboardInterrupt):
        exit()