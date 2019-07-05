# H.E.D.O. Hyper Enabled Drone Operator
A proof of concept (POC) demonstrating the control of a skydio drone with a commander glove from BeBop sensors.

## Run
1. ```pip3 install -r requirements.txt```
2. Conect the Skydio Drone via WiFi (192.168.10.1)
3. Connect the Commander Glove via bluetooth and be sure to open a serial port connection (RFCOMM0)
4. ```python3 http_client.py```
## Controls
+ **Fist:** Land
+ **Thumbs Up:** Takeoff
+ **Peace:** Sentry Mode, follow anyone near a home point
+ **Hookem Horns:** Survey, spin 360 degrees in a circle to view surroundings
## ToDo
+ Add waypoint mode using the polygon skill
## Resources
+ https://github.com/Skydio/skydio-skills
