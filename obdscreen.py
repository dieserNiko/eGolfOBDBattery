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

screenmode = "percscreen"
screen = "perc"

# Activate Debugmode to show custom percentage on display while not connected to car
DEBUG = False
DEBUGPERC = 100
DEBUGTEMP = 45

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
padding = -6 #-2
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# Load font.
font = ImageFont.truetype('/root/VWTextOfficeRegular.ttf', 38)
smallfont = ImageFont.truetype('/root/VWTextOfficeRegular.ttf', 15)

draw.rectangle((0,0,width,height), outline=0, fill=0)

draw.text((x, top), str("booting..."), font=ImageFont.truetype('/root/VWTextOfficeRegular.ttf', 35), fill=255)

disp.image(image)
disp.display()

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
	
# Define temperature method to calculate real temperature out of raw data value and abstract battery temperature
def temperature(messages):
	h = messages[0].hex()
	print("Temp hex data:")
	print(h)
	ha = h[6:8]
	print("first hextett")
	print(ha)
	ha = int(ha, 16)
	print("first hextett decimated")
	print(ha)
	hb = h[8:10]
	print("second hextett")
	print(hb)
	hb = int(hb, 16)
	print("second hextett decimated")
	print(hb)
	h = ((ha * 256 + hb) / 64)
	print("calculated result")
	print(h)
	h = (h - 320) / 8
	return h
	
# Communicate which car control device you want to talk to
try:
	c.interface._ELM327__send(b"ATZ",delay=0)
	c.interface._ELM327__send(b"ATE0",delay=0)
	c.interface._ELM327__send(b"AT TP 6",delay=0)
	c.interface._ELM327__send(b"ATH1",delay=0)
	c.interface._ELM327__send(b"AT CRA 7ED",delay=0)
	c.interface._ELM327__send(b"AT SH 7E5",delay=0)
except:
	print("Can't connect to car...")

while True:
	# Define custom command to request battery percentage from car
	try:
		cmdPerc = OBDCommand("BatteryPercent", "Percentage of HV Battery", b"22028C55555555", 4, percent)	
		
		# Query car for battery value
		response = c.query(cmdPerc, force=True)
		PERC = response.value
		# Parse answer from car and write it into the file to show it on screen
		
		PERC = round(PERC,0)
		PERC = int(PERC)
		if PERC < 100:
			PERC = "  " + str(PERC) + "%"
		else:
			PERC = " " + str(PERC) + "%"
		
		# Debug output
		print(response.value)
		
		if DEBUG == True:
			PERC = "" + str(DEBUGPERC) + "%"
		
	except:
		print("Can't connect to car")
		if DEBUG == False:
			PERC = "No car!"
		elif DEBUG == True:
			PERC = DEBUGPERC
			PERC = round(PERC,0)
			PERC = int(PERC)
			if PERC < 100:
				PERC = " " + str(PERC) + "%"
			else:
				PERC = str(PERC) + "%"
				
	try:
		# Define custom command to request battery temperature from car
		cmdTemp = OBDCommand("BatteryTemperature", "Temperature of HV Battery", b"222a0b55555555", 5, temperature)
		
		# Query car for temperature value
		response = c.query(cmdTemp, force=True)
		TEMP = response.value
		
		# Parse answer from car and write it into variable to show it on screen
		TEMP = round(TEMP,0)
		TEMP = int(TEMP)
		TEMP = str(TEMP) + "˚C"
		
		# Debug output
		print(response.value)
		
		if DEBUG == True:
			TEMP = str(DEBUGTEMP) + "˚C"
		
	except:
		print("Can't connect to car")
		#if DEBUG == False:
		TEMP = "Fail!"
	
	try: 
		def mode(messages):
			e = messages[0].hex()
			e = e[6:]
			e = bytes_to_int(e)
			return e
		        
		cmdMode = OBDCommand("BatteryMode", "Mode of HV Battery", b"22744855555555", 4, mode)
		
		response = c.query(cmdMode, force=True)
		mode = response.value
		print("Mode: " + str(response.value))
		
		if mode != 12337:
		
			screenmode = "switchscreen"
				
			def voltage(messages):
				f = messages[0].hex()
				fa = f[6:8]
				fa = int(fa, 16)
				fb = f[8:10]
				fb = int(fb, 16)
				f = (fa * 2 ** 8 + fb) / 4
				return f
				
			def current(messages):
			    g = messages[0].hex()
			    ga = g[6:8]
			    ga = int(ga, 16)
			    gb = g[8:10]
			    gb = int(gb, 16)
			    g = (ga * 2 ** 8 + gb - 2044) / 4
			    return g
			    
			cmdVolt = OBDCommand("BatteryVoltage", "Voltage of HV Battery", b"221E3B55555555", 0, voltage)
			cmdCurr = OBDCommand("BatteryCurrent", "Current of HV Battery", b"221E3D55555555", 0, current)
			
			response = c.query(cmdVolt, force=True)
			voltage = response.value
			print("Voltage: " + str(response.value) + "V")
			
			response = c.query(cmdCurr, force=True)
			current = response.value
			print("Current: " + str(response.value) + "A")
			
			power = round((abs(voltage * current) / 1000), 1)
			
			if power >= 10:
				power = " " + str(int(round((abs(voltage * current) / 1000), 0)))
				
			POWER = str(power) + "kW"
			
			print("Power: " + str(power))
			
		else:
			screenmode = "percscreen"
					
	except:
		print("Can't connect to car: Mode, Voltage or Current not available")
		
	if screenmode == "percscreen":
		DISP = PERC
	elif screenmode == "switchscreen" and screen == "perc":
		DISP = PERC
		screen = "power"
	elif screenmode == "switchscreen" and screen == "power":
		DISP = POWER
		screen = "perc"
		
	print("DISP: " + DISP)

	# Draw a black filled box to clear the image.
	draw.rectangle((0,0,width,height), outline=0, fill=0)
	
	draw.text((x, top),        str(DISP), font=font, fill=255)
	if DISP == PERC:
		draw.text((93, -1), str(TEMP), font=smallfont, fill=255)
	
	disp.image(image)
	disp.display()
	print(screenmode)
	print(screen)
	time.sleep(7)
