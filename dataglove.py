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

    while True:

        time.sleep(1)
        if (data[0] == 1):
            time.sleep(1)
            thumb = (data[2] + data[3])
            index = (data[4] + data[5])
            middle = (data[6] + data[7])
            ring = (data[8] + data[9])
            pinky = (data[10] + data[11])
            fingers = [thumb,index,middle,ring,pinky]
            hand = sum([data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11]])
            print(fingers,hand)
            
            if (hand >= 600):
                print("Taking off...")
                #Call Takeoff Function
            if (hand <= 500 and thumb >= 200):
                print("Landing...")
    data_glove_thread.close()

main()