# Flight tracker

A python script that runs on Raspberry Pi, uses ADS-B receiver to receive and dump1090 to demodulate and decode signal from
nearby aircrafts.

Then shows local map and aircrafts on connected ST7789 screen in real-time.

Install dependencies:
`sudo pip3 install adafruit-circuitpython-rgb-display`

To install as a linux service:
`sudo ./install.sh`

https://github.com/flightaware/dump1090

https://github.com/adafruit/Adafruit_CircuitPython_RGB_Display
