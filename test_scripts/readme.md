## Glove Documentation
The dataglove.py script is a demonstration of parsing the serial port data from the right-handed dataglove. The script parses a byte array of 14 elements.<br>

0. Data type - If 1, the following data is from flex sensors, if 2, the following data is from the IMU
1. Verification byte
2. Thumb 1 (0-127)
3. Thumb 2 (0-127)
4. Index 1 (0-127)
5. Index 2 (0-127)
6. Middle 1 (0-127)
7. Middle 2 (0-127)
8. Ring 1 (0-127)
9. Ring 2 (0-127)
10. Pinky 1 (0-127)
11. Pinky 2 (0-127)
12.
13. Constant - 127
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
