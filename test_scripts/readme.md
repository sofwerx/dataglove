## Glove Documentation
The dataglove.py script is a demonstration of parsing the serial port data from the right-handed dataglove.<br>
1. First, the glove must be connected to the device via serial port.
2. After the glove is connected, the following bytes must be sent to tell the glove to begin streaming and to use either USB or BLUETOOTH:
```            # data on
            self.glove.write(bytearray([176, 115, 1]))
AND
            # usb mode
            #self.glove.write(bytearray([176, 118, 1]))
OR
            # bluetooth mode
            self.glove.write(bytearray([176, 118, 2]))
```
3. The Glove will now begin streaming bytes.<br>
4. Collect the bytes and parse them as follows, appending them to the data array:
```     b = int.from_bytes(byte_to_parse, byteorder='big')
        if b == 240:
            self.data = []
        elif b == 247:
            self.data.append(b)

            if (self.data[0] == 1):
                data = self.data
        else:
            self.data.append(b)
```
The byte array begins with 0xF0, followed by 13 data bytes where the 14th byte is 0xf7.<br>
Byte # HEX DEC Description
0. 0xF0 240 - Start
1. 0x01 1 - ID (FRAME_ID_SENSOR)
2. 0x0B 11 - Data length (10 sensor + 1 battery bytes)
3. 0x## ## - Sensor 1 (Thumb Sensor 1)
4.-11 0x## ## - … Sensor 2 - Sensor 9
12. 0x## ## - Sensor 10 (Pinky Sensor 2)
13. 0x## ## - Battery
14. 0xF7 247 - Stop
<br>
Each finger sensor can be added together to achieve an overall flex number from 0 being fully extended and 254 being fully closed. These numbers can then be stored in finger values as follows:<br>
            thumb = (data[2] + data[3])<br>
            index = (data[4] + data[5])<br>
            middle = (data[6] + data[7])<br>
            ring = (data[8] + data[9])<br>
            pinky = (data[10] + data[11])<br>
            hand = sum([data[2], data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11]])<br>

A few poses can then be defined below:<br>
+ FIST: hand >= 600 and thumb >= 30
+ THUMBSUP: thumb <= 20 and index >= 140 and middle >= 140 and ring >= 100 and pinky >= 120
+ PEACE: thumb >= 20 and index <= 20 and middle <= 20 and ring >= 120 and pinky >= 120
+ HOOKEM: index <= 20 and middle >= 140 and ring >= 140 and pinky <= 20
+ FOUR: hand <= 500 and thumb >= 180
