#!/usr/bin/env python3

import sys
import time
import json
import math
import os
import colorsys
import numpy
from PIL import Image, ImageDraw, ImageFont
from collections import namedtuple

import busio
import digitalio
from board import SCK, MOSI, MISO, CE1, D25
import adafruit_rgb_display.st7789 as st7789

FPS = 30

class Size:
    def __init__(self, width, height):
        self.width = width
        self.height = height


class Frame:
    def __init__(self, x, y, size):
        self.x = x
        self.y = y
        self.size = size

# Configuration for CS and DC pins:
CS_PIN = CE1
DC_PIN = D25
BAUDRATE = 24000000

# Setup SPI bus using hardware SPI:
SPI = busio.SPI(clock=SCK, MOSI=MOSI, MISO=MISO)

class Screen:
    # Create the ST7789 display:
    Disp = st7789.ST7789(
        SPI,
        rotation=0,
        width=240,
        height=240,
        y_offset=80,
        baudrate=BAUDRATE,
        cs=digitalio.DigitalInOut(CS_PIN),
        dc=digitalio.DigitalInOut(DC_PIN))
    currentVC = None

    @staticmethod
    def size():
        return Size(Screen.Disp.width, Screen.Disp.height)

    @staticmethod
    def setup():
        print("Setup Screen")
        Screen.runloop()

    @staticmethod
    def runloop():
        print("Start Runloop")
        while True:
            if Screen.currentVC is not None:
                framebuffer = Screen.currentVC.redraw()
                framebuffer = framebuffer.resize((Screen.size().width, Screen.size().height))
                Screen.Disp.image(framebuffer.convert("RGBA"))
            time.sleep(1.0 / FPS)

    @staticmethod
    def addViewController(VC):
        Screen.currentVC = VC


class ViewController(object):
    def __init__(self):
        self.views = []

    def addView(self, View):
        self.views.append(View)

    def removeView(self, View):
        if View in self.views:
            self.views.remove(View)

    def redraw(self):
        print("Redraw ViewController")
        screen_size = Screen.size()
        frame_buffer = Image.new ("RGBA", (screen_size.width, screen_size.height), (0, 0, 0, 0))
        for v in self.views:
            view_buffer = v.render().convert(frame_buffer.mode)
            frame_buffer.paste(view_buffer, (v.frame.x, v.frame.y), view_buffer)
        return frame_buffer


class View(object):
    def __init__(self, frame):
        self.frame = frame

    def render(self):
        pass

# -------------------------------------------------------------------
# FLIGHT TRACKER CODE
# -------------------------------------------------------------------

class MapView(View):
    def __init__(self):
        super().__init__(Frame(0, 0, Screen.size()))
        self.image = Image.open("resources/map.png")
        self.image = self.image.resize((self.frame.size.width, self.frame.size.height))

    def render(self):
        return self.image


class ErrorView(View):
    def __init__(self):
        super().__init__(Frame(0, 240-40, Size(240, 40)))
        self.font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        # Create a new image with transparent background to store the text.
        self.textimage = Image.new('RGBA', (240, 40), (0, 0, 0, 0))
        self.textdraw = ImageDraw.Draw(self.textimage)
        self.textdraw.text((0, 0), "CAN'T READ DATA!", font=self.font, fill=(0, 0, 0))

    def render(self):
        return self.textimage


class AltitudeView(View):
    def __init__(self):
        super().__init__(Frame(0, 240-10, Size(240, 10)))
        # Create a new image with transparent background to store the text.
        self.bgImage = Image.new('RGB', (240, 20), (255, 0, 0, 255))
        pix = numpy.array(self.bgImage)
        bucket = 330 / 240
        for line_idx in range(len(pix)):
            for pix_idx in range(len(pix[line_idx])):
                hue = pix_idx * bucket
                rgb = colorsys.hsv_to_rgb(hue / 360, 1, 1)
                pixel = (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
                self.bgImage.putpixel((pix_idx, line_idx), pixel)

    def render(self):
        return self.bgImage


class AirplaneView(View):
    def __init__(self, x, y, plane):
        self.size = Size(30, 30)
        fx, fy = self.fixOrigin(x, y)
        super().__init__(Frame(fx, fy, self.size))
        planeImg = Image.open("resources/plane.png").rotate(45)
        planeImg = planeImg.rotate(-1 * plane.getHeading())
        planeImg = planeImg.resize((self.frame.size.width, self.frame.size.height))

        planeAlpha = planeImg.getchannel('A')
        iconColor = Alt2Color.interpolate2color(plane.alt_baro)
        self.image = Image.new('RGBA', planeImg.size, iconColor)
        self.image.putalpha(planeAlpha)


    def fixOrigin(self, x, y):
        return (int(x-self.size.width/2), int(y-self.size.height/2))

    def render(self):
        return self.image


class Airplane:
    def __init__(self, JSON):
        self.hex = JSON.get("hex", None)
        self.lat = JSON.get("lat", None)
        self.lon = JSON.get("lon", None)
        self.flight = JSON.get("flight", None)
        self.track = JSON.get("track", None)
        self.mag_heading = JSON.get("mag_heading", None)
        self.nav_heading = JSON.get("nav_heading", None)
        self.alt_baro = JSON.get("alt_baro", None)
        self.flight = JSON.get("flight", None)        
        
    def getHeading(self):
        if self.track is not None:
            return self.track
        if self.mag_heading is not None:
            return self.mag_heading
        if self.nav_heading is not None:
            return self.nav_heading
        return 0

    def isValid(self):
        if self.lat is None or self.lat is None:
            return False
        else:
            return True

Alt2Color = namedtuple('Alt2Color', 'alt val')


class Alt2Color:
    Saturation = 100
    Lightness = 50
    HUE = [
        Alt2Color(2000, 20),
        Alt2Color(10000, 140),
        Alt2Color(40000, 300),
        ]

    def interpolate2color(alt):
        hue = Alt2Color.HUE[0].val
        for i in range(len(Alt2Color.HUE)-1, -1, -1):
            if alt > Alt2Color.HUE[i].alt:
                if i == len(Alt2Color.HUE)-1:
                    hue = Alt2Color.HUE[i].val
                else:
                    hue = Alt2Color.HUE[i].val + (Alt2Color.HUE[i+1].val - Alt2Color.HUE[i].val) * (alt - Alt2Color.HUE[i].alt) / (Alt2Color.HUE[i+1].alt - Alt2Color.HUE[i].alt)
                break
        if hue < 0:
            hue = (hue % 360) + 360
        elif hue >= 360:
            hue = hue % 360
        rgb = colorsys.hsv_to_rgb(hue / 360, Alt2Color.Saturation/100, Alt2Color.Lightness/100)
        return (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))


class CoordinatesConverter:
    EARTH_RADIUS_KM = 6371

    def __init__(self, screen_width, screen_height, p0_lat, p0_lon, p1_lat, p1_lon):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.p0_lat = p0_lat
        self.p0_lon = p0_lon
        self.p1_lat = p1_lat
        self.p1_lon = p1_lon

        self.p0_glob_pos = self.coordinatesToGlobPosition(self.p0_lat, self.p0_lon)
        self.p1_glob_pos = self.coordinatesToGlobPosition(self.p1_lat, self.p1_lon)

    def coordToScreen(self, lat, lon):
        # Calculate global X and Y for projection point
        x, y = self.coordinatesToGlobPosition(lat, lon)
        # Calculate the percentage of Global X position in relation to total global width
        pos_perX = ((x-self.p0_glob_pos[0])/(self.p1_glob_pos[0] - self.p0_glob_pos[0]))
        # Calculate the percentage of Global Y position in relation to total global height
        pos_perY = ((y-self.p0_glob_pos[1])/(self.p1_glob_pos[1] - self.p0_glob_pos[1]))
        # Returns the screen position based on reference points
        return (int(self.screen_width * pos_perX), int(self.screen_height * pos_perY))

    # This function converts lat and lng coordinates to GLOBAL X and Y positions
    def coordinatesToGlobPosition(self, lat, lon):
        # Calculates x based on cos of average of the latitudes
        x_pos = CoordinatesConverter.EARTH_RADIUS_KM * lon * math.cos((self.p0_lat + self.p1_lat)/2)
        # Calculates y based on latitude
        y_pos = CoordinatesConverter.EARTH_RADIUS_KM * lat
        return (x_pos, y_pos)


class MainViewController(ViewController):
    def __init__(self):
        super().__init__()
        self.converter = CoordinatesConverter(
            Screen.size().width,
            Screen.size().height, 
            p0_lat=51.748699, 
            p0_lon=-0.531184, 
            p1_lat=51.229317, 
            p1_lon=0.300493
        )

        self.errorView = ErrorView()
        self.mapView = MapView()
        self.addView(self.mapView)

        self.altView = AltitudeView()
        self.addView(self.altView)

        self.airplanes = []
        self.airplaneViews = []

    def redraw(self):
        print("Redraw MainViewController")
        self.getData()
        self.redrawPlanes()
        return super().redraw()

    def redrawPlanes(self):
        print("Redrawing planes")
        currentPlaneViews = []
        for plane in self.airplanes:
            if plane.isValid() == False:
                continue
            xp, yp = self.converter.coordToScreen(plane.lat, plane.lon)
            planeView = AirplaneView(xp, yp, plane)
            currentPlaneViews.append(planeView)
            self.addView(planeView)

        for oldPlane in self.airplaneViews:
            self.removeView(oldPlane)
        self.airplaneViews = currentPlaneViews

    def getData(self):
        print("Getting data...")
        data_path = "/run/dump1090-fa/aircraft.json"

        # Show error view if the source doesn't exist
        if os.path.exists(data_path) == False:
            print("Error. Source doesn't exist.")
            self.addView(self.errorView)
            self.airplanes = []
            return
        # Hide error view if the source exist
        self.removeView(self.errorView)

        with open(data_path, "r") as read_file:
            data = json.load(read_file)

        current_planes = []
        for planeJSON in data["aircraft"]:
            plane = Airplane(planeJSON)
            current_planes.append(plane)
        self.airplanes = current_planes


def main():
    mainVC = MainViewController()
    Screen.addViewController(mainVC)
    Screen.setup()

if __name__ == "__main__":
    main()
