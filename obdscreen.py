#!/usr/bin/python3

import time

import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

#import subprocess

import obd
from obd import OBDCommand
from obd.utils import bytes_to_int

# Set screenmode and which value to show by default after starting the car
screenmode = "percscreen"
screen = "perc"

# Activate Debugmode to show custom percentage on display while not connected to car
DEBUG = False
DEBUGPERC = 69

# AdaFruit Display Raspberry Pi pin configuration:
RST = None     # on the PiOLED this pin isnt used

# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0

# 128x32 display with hardware I2C:
disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST)

# Initialize library.
disp.begin()

# Clear display.
disp.clear()
disp.display()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)

# First define some constants to allow easy resizing of shapes.
padding = 0 #-2
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# Load font.
font = ImageFont.truetype('/root/Helvetica.ttf', 38)

# Create OBD connection to defined serial port (with baudrate etc)
c = obd.OBD("/dev/ttyUSB0")
#,timeout=1,fast=False,protocol="6",baudrate=38400)

# Define percent method to calculate real battery percentage out of raw data value from car
def percent(messages):
	d = messages[0].data
	d = d[3:]
	v = bytes_to_int(d)
	v = v / 2.5
	v = v * 51 / 46 - 6.4
	return v
	
# Communicate which car control device you want to talk to
try:
	c.interface._ELM327__send(b"ATZ",delay=0)
	c.interface._ELM327__send(b"ATE0",delay=0)
	c.interface._ELM327__send(b"AT TP 6",delay=0)
	c.interface._ELM327__send(b"ATH1",delay=0)
	c.interface._ELM327__send(b"AT CRA 7ED",delay=0)
	c.interface._ELM327__send(b"AT SH 7E5",delay=0)
# What happens if connection to car fails
except:
	print("Can't connect to car...")

# Loop that continuously checks percentage and power
while True:
	try:
    # Define custom command to request battery percentage from car
		cmdPerc = OBDCommand("BatteryPercent", "Percentage of HV Battery", b"22028C55555555", 4, percent)	
		
		# Query car for battery value
		response = c.query(cmdPerc, force=True)
		PERC = response.value
    
		# Parse answer from car and write it into variable to show it on screen
		PERC = round(PERC,0)
		PERC = int(PERC)
		if PERC < 100:
			PERC = "  " + str(PERC) + "%"
		else:
			PERC = " " + str(PERC) + "%"
		
		# Debug output
		print(response.value)
		
  # What happens if connection to car fails
	except:
		print("Can't connect to car")
		if DEBUG == False:
			PERC = "No car!"
    # Show dummy values on screen if Debugmode is active
		elif DEBUG == True:
			PERC = DEBUGPERC
			PERC = round(PERC,0)
			PERC = int(PERC)
			if PERC < 100:
				PERC = "  " + str(PERC) + "%"
			else:
				PERC = " " + str(PERC) + "%"
  
	try: 
    # Define mode method to to check if car is charging or not out of raw data value from car
		def mode(messages):
			e = messages[0].hex()
			e = e[6:]
			e = bytes_to_int(e)
			return e
		
    # Define custom command to check if car is charging or not
		cmdMode = OBDCommand("BatteryMode", "Mode of HV Battery", b"22744855555555", 4, mode)
		
    # Query car for charging, save it to variable and create debugging output
		response = c.query(cmdMode, force=True)
		mode = response.value
		print("Mode: " + str(response.value))
		
    # Mode 12337 is not plugged in, mode 12340 is plugged in, possible other modes not (yet) discovered
		if mode != 12337:
		  
      # Set screenmode to switchscreen to show battery percentage and charging power alternating with each update
			screenmode = "switchscreen"
			
      # Define voltage method to calculate battery voltage from raw values from car
			def voltage(messages):
				f = messages[0].hex()
				fa = f[6:8]
				fa = int(fa, 16)
				fb = f[8:10]
				fb = int(fb, 16)
				f = (fa * 2 ** 8 + fb) / 4
				return f
			
      # Define current method to calculate battery current from raw values from car
			def current(messages):
			    g = messages[0].hex()
			    ga = g[6:8]
			    ga = int(ga, 16)
			    gb = g[8:10]
			    gb = int(gb, 16)
			    g = (ga * 2 ** 8 + gb - 2044) / 4
			    return g
			
      # Define custom command to check battery voltage
			cmdVolt = OBDCommand("BatteryVoltage", "Voltage of HV Battery", b"221E3B55555555", 0, voltage)
      # Define custom command to check battery current
			cmdCurr = OBDCommand("BatteryCurrent", "Current of HV Battery", b"221E3D55555555", 0, current)
			
      # Query car for battery voltage, save it into variable and create debugging output
			response = c.query(cmdVolt, force=True)
			voltage = response.value
			print("Voltage: " + str(response.value) + "V")
			
      # Query car for battery current, save it into variable and create debugging output
			response = c.query(cmdCurr, force=True)
			current = response.value
			print("Current: " + str(response.value) + "A")
			
      # Round charging power to one decimal and always show positive values
			power = round((abs(voltage * current) / 1000), 1)
			
      # Don't show decimal values for charging power over 10kW as it would be too wide for the display
			if power >= 10:
				power = " " + str(round((abs(voltage * current) / 1000), 0))
			
      # Set variable with kW extension for displaying
			POWER = str(power) + "kW"
			
      # Create debugging output
			print("Power: " + str(power))
		
    # Set screenmode to percscreen if batterymode is "not charging"
		else:
			screenmode = "percscreen"
	
  # What to do if commands for querying mode, voltage or current fail
	except:
		print("Can't connect to car: Mode, Voltage or Current not available")
	
  # Check screenmode and display corresponding value on screen
	if screenmode == "percscreen":
		DISP = PERC
  # Check screenmode, display corresponding value on screen and switch to next value
	elif screenmode == "switchscreen" and screen == "perc":
		DISP = PERC
		screen = "power"
  # Check screenmode, display corresponding value on screen and switch to next value
	elif screenmode == "switchscreen" and screen == "power":
		DISP = POWER
		screen = "perc"
	
  # Create debugging output for what is shown on screen
	print("DISP: " + DISP)

	# Draw a black filled box to clear the image.
	draw.rectangle((0,0,width,height), outline=0, fill=0)
	
  # Draw value from variable on screen
	draw.text((x, top),        str(DISP), font=font, fill=255)
	
	disp.image(image)
	disp.display()
  
  # Create debugging output which screenmode and screen are shown next
	print(screenmode)
	print(screen)
  
  # Wait 10 seconds before updating the screen
	time.sleep(10)
