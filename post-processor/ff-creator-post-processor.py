#! /usr/bin/python3-64
# ff-creator-post-processor.py

# LICENSE & COPYRIGHT
# Copyright 2022 Jacotheron
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import fileinput
import re
import sys
import base64
from io import BytesIO
from PIL import Image ## remember to install Pillow
from struct import *

thumbnail_start = re.compile('^; thumbnail begin [a-x0-9]+ [0-9]+')
thumbnail_end = re.compile('^; thumbnail end')
thumbnail_content_re = re.compile('^; (.*)$')
thumbnail_b64_content = ""
thumbnail_image = ""

extr_right_active = False
extr_left_active = False
extr_both_active = False
use_calpads = False

extruder_match = re.compile('^M6 T([0-9]+)') #get which extruders are active
extruder_mode_match = re.compile('^M109 T([0-9])') #match for ditto or mirror
setting_print_time = re.compile('^; estimated printing time \(normal mode\) = ([0-9hms ]*)')
setting_filament_usage = re.compile('^; filament used \[mm\] = ([0-9., ]*)')
setting_layer_height = re.compile('^; layer_height = ([0-9. ]*)')
setting_shells = re.compile('^; perimeters = ([0-9]*)')
setting_speed = re.compile('^; perimeter_speed = ([0-9]*)')
setting_bed_temp = re.compile('^; bed_temperature = ([0-9]*)')
setting_temps = re.compile('^; temperature = ([0-9, ]*)')

matching_hours = re.compile('([0-9]+)h')
matching_minutes = re.compile('([0-9]+)m')
matching_seconds = re.compile('([0-9]+)s')

#the binary seems to be little-endian (start with smallest values), and appends null-bytes after to fill the space
header_hex = [
    bytes.fromhex("7867636F646520312E300A00"), # "xgcode 1.0\nNULL"
] # first constant for version number 0x00 -> 0x0B

header_hex.append(bytes.fromhex("00000000")) # 32bit constant #1 = 0 -> file start; 0x0C -> 0x0F
header_hex.append(bytes.fromhex("3A000000")) # 32bit constant #2 = 58 -> start of bitmap; 0x10 -> 0x13
header_hex.append(bytes.fromhex("B0380000")) # 32bit constant #3 = 14512 -> start of gcode; 0x14 -> 0x17
header_hex.append(bytes.fromhex("B0380000")) # 32bit constant #4 = 14512 -> start of gcode; 0x18 -> 0x1B


print_time_in_seconds = 0 #0x1C - 4 bytes
filament_usage_in_mm_right = 0 #0x20 - 4 bytes
filament_usage_in_mm_left = 0 #0x24 - 4 bytes
extruder_mode = 3 # 0x28 - 2 bytes # 3 is normal, 19 is duplicate, 35 is mirror
layer_height_microns = 0 #0x2a - 2 bytes
number_perimeter_shells = 0 #0x2e - 2 bytes
print_speed = 0 # 0x30 - 2 bytes
platform_temp = 0 # 0x32 - 2 bytes
right_extruder_temp = 0 # 0x34 - 2 bytes
left_extruder_temp = 0 # 0x36 - 2 bytes
thumbnail = 0

file_data = "\n"

image_extract_status = 0 #1 means we are extracting; 2 means we are done extracting

#this variable to is to ensure it still work for single extruder prints
print_have_started = 0
for line in fileinput.input(inplace=True):
    #print(line, end="") #for now we keep all lines
    file_data += line #store in memory, since we already have to get everything in memory
    if image_extract_status == 0:
        if thumbnail_start.match(line):
            image_extract_status = 1
            continue # got o next line
    if image_extract_status == 1:
        if thumbnail_end.match(line):
            image_extract_status = 2
            thumbnail_image = Image.open(BytesIO(base64.decodebytes(thumbnail_b64_content.encode('ascii')))).convert("RGB") #load as image and ensure it is RGB (1 byte per pixel)
            thumbnail_b64_content = "" # clear to save memory
            thumbnail_bytes = BytesIO()
            thumbnail_image.save(thumbnail_bytes, format="BMP")
            thumbnail = thumbnail_bytes.getvalue()
            
            continue #go to nect line
        else:
            m = thumbnail_content_re.match(line)
            thumbnail_b64_content += m.group(1)
    else:
        if extruder_match.match(line): # this should match early in the file
            if extruder_match.match(line).group(1) == "1":
                extr_left_active = True
                if extr_right_active:
                    extr_both_active = True
            else:
                extr_right_active = True
                if extr_left_active:
                    extr_both_active = True
            continue
        if extruder_mode_match.match(line): # this should match early in the file
            use_calpads = True
            if extruder_mode_match.match(line).group(1) == "1": # mirror
                extruder_mode = 35
            else: # 2 = ditto
                extruder_mode = 19
            continue
        if setting_print_time.match(line):
            time = setting_print_time.match(line).group(1).split() # this match in nnh nnm nns
            seconds = 0
            for part in time:
                if matching_hours.match(part):
                    hours = matching_hours.match(part).group(1)
                    seconds += int(hours) * 60 * 60
                if matching_minutes.match(part):
                    minutes = matching_minutes.match(part).group(1)
                    seconds += int(minutes) * 60
                if matching_seconds.match(part):
                    seconds += int(matching_seconds.match(part).group(1))
            print_time_in_seconds = seconds
            continue
        if setting_filament_usage.match(line):
            string = setting_filament_usage.match(line).group(1).split(", ") # this match in nnh nnm nns
            for part in string:
                if not extr_both_active and extr_left_active:
                    filament_usage_in_mm_left = int(float(part)) # should be the only part
                elif filament_usage_in_mm_right != 0:
                    filament_usage_in_mm_left = int(float(part)) # should be on second loop now
                else:
                    filament_usage_in_mm_right = int(float(part)) # might be only part or first loop
            continue
        if setting_temps.match(line):
            string = setting_temps.match(line).group(1).split(",") # this match in nnh nnm nns
            for part in string:
                if not extr_both_active and extr_left_active:
                    left_extruder_temp = int(part) # should be the only part
                elif right_extruder_temp != 0:
                    left_extruder_temp = int(part) # should be on second loop now
                else:
                    right_extruder_temp = int(part) # might be only part or first loop
            continue
        if setting_layer_height.match(line):
            layer_height_microns = int(float(setting_layer_height.match(line).group(1)) * 1000)
            continue
        if setting_shells.match(line):
            number_perimeter_shells = int(setting_shells.match(line).group(1))
            continue
        if setting_speed.match(line):
            print_speed = int(setting_speed.match(line).group(1))
            continue
        if setting_bed_temp.match(line):
            platform_temp = int(setting_bed_temp.match(line).group(1))
            continue
    
fileinput.close() # ensure it is closed, so that we can read to it in binary mode
# since we store the data in memory, and did not write back, file is empty, easy to prepend header

#lets now start to process our additional_data
# Our Variables and their sizes
# print_time_in_seconds = 0 #0x1C - 4 bytes
# filament_usage_in_mm_right = 0 #0x20 - 4 bytes
# filament_usage_in_mm_left = 0 #0x24 - 4 bytes
# extruder_mode = 3 # 0x28 - 2 bytes # 3 is normal, 19 is duplicate, 35 is mirror
# layer_height_microns = 0 #0x2a - 2 bytes
# number_perimeter_shells = 0 #0x2e - 2 bytes
# print_speed = 0 # 0x30 - 2 bytes
# platform_temp = 0 # 0x32 - 2 bytes
# right_extruder_temp = 0 # 0x34 - 2 bytes
# left_extruder_temp = 0 # 0x36 - 2 bytes
null_byte = 0

header_hex.extend([
    pack(
        '<lllhhhhhhhh', 
        print_time_in_seconds, #0x1C - l
        filament_usage_in_mm_right, #0x20 - l
        filament_usage_in_mm_left, #0x24 - l
        extruder_mode, #0x28 - h
        layer_height_microns, #2A - h
        null_byte, #2C - h
        number_perimeter_shells, #0x2E - h
        print_speed, #0x30 - h
        platform_temp, #x32 - h
        right_extruder_temp, #x34 - h
        left_extruder_temp, #x36 - h
    ),
    bytes.fromhex("FEFE") # Unknown, but seems to be a constant in all my demo files
]) #after this we should be at next space should be at 3A which is the starting point for our image


if thumbnail == 0: # we generate a new one
    thumbnail_image = Image.new('RGB', (80,60))
    thumbnail_bytes = BytesIO()
    thumbnail_image.save(thumbnail_bytes, format="BMP")
    thumbnail = thumbnail_bytes.getvalue()
header_hex.append(thumbnail)

calPad_content = """;calPad A start Z0.20
;support-start
;structure:cal-pad
;:G1 X-13.40 Y-13.64 F6000
;:G1 X-11.80 Y-14.66 E.0688 F4800
;:G1 X-10.00 Y-15.00 E.1352
;:G1 X10.00 Y-15.00 E.8603
;:G1 X11.95 Y-14.60 E.9324
;:G1 X13.59 Y-13.48 E1.0044
;:G1 X14.66 Y-11.80 E1.0766
;:G1 X15.00 Y-10.00 E1.1431
;:G1 X15.00 Y-6.60 E1.2663
;:G1 X16.60 Y-6.60 E1.3243
;:G1 X16.60 Y16.60 E2.1654
;:G1 X-16.60 Y16.60 E3.3690
;:G1 X-16.60 Y-16.60 E4.5726
;:G1 X-13.40 Y-16.60 E4.6887
;:G1 X-13.40 Y-13.64 E4.7960
;:G1 X-13.60 Y-14.52 F6000
;:G1 X-15.47 Y-16.40 E4.8921 F4800
;:G1 X14.48 Y-11.71 F6000
;:G1 X11.74 Y-14.44 E5.0323 F4800
;:G1 X9.98 Y-14.80 E5.0974
;:G1 X9.44 Y-14.80 E5.1170
;:G1 X14.80 Y-9.44 E5.3918
;:G1 X14.80 Y-7.50 E5.4622
;:G1 X7.50 Y-14.80 E5.8364
;:G1 X5.56 Y-14.80 E5.9068
;:G1 X16.40 Y-3.96 E6.4625
;:G1 X16.40 Y-2.01 E6.5332
;:G1 X3.61 Y-14.80 E7.1890
;:G1 X1.67 Y-14.80 E7.2593
;:G1 X16.40 Y-.07 E8.0145
;:G1 X16.40 Y1.87 E8.0849
;:G1 X-.27 Y-14.80 E8.9395
;:G1 X-2.21 Y-14.80 E9.0099
;:G1 X16.40 Y3.82 E9.9643
;:G1 X16.40 Y5.76 E10.0346
;:G1 X-4.16 Y-14.80 E11.0887
;:G1 X-6.10 Y-14.80 E11.1590
;:G1 X16.40 Y7.70 E12.3126
;:G1 X16.40 Y9.65 E12.3833
;:G1 X-8.04 Y-14.80 E13.6366
;:G1 X-9.98 Y-14.80 E13.7069
;:G1 X16.40 Y11.59 E15.0597
;:G1 X16.40 Y13.53 E15.1300
;:G1 X-11.62 Y-14.49 E16.5666
;:G1 X-11.73 Y-14.47 E16.5707
;:G1 X-12.84 Y-13.76 E16.6185
;:G1 X16.40 Y15.48 E18.1176
;:G1 X16.40 Y16.40 E18.1510
;:G1 X15.38 Y16.40 E18.1879
;:G1 X-16.40 Y-15.38 E19.8173
;:G1 X-16.40 Y-13.44 E19.8876
;:G1 X13.44 Y16.40 E21.4175
;:G1 X11.49 Y16.40 E21.4882
;:G1 X-16.40 Y-11.49 E22.9182
;:G1 X-16.40 Y-9.55 E22.9885
;:G1 X9.55 Y16.40 E24.3190
;:G1 X7.61 Y16.40 E24.3893
;:G1 X-16.40 Y-7.61 E25.6203
;:G1 X-16.40 Y-5.66 E25.6910
;:G1 X5.66 Y16.40 E26.8220
;:G1 X3.72 Y16.40 E26.8923
;:G1 X-16.40 Y-3.72 E27.9239
;:G1 X-16.40 Y-1.78 E27.9942
;:G1 X1.78 Y16.40 E28.9263
;:G1 X-.17 Y16.40 E28.9970
;:G1 X-16.40 Y.17 E29.8291
;:G1 X-16.40 Y2.11 E29.8995
;:G1 X-2.11 Y16.40 E30.6321
;:G1 X-4.05 Y16.40 E30.7025
;:G1 X-16.40 Y4.05 E31.3356
;:G1 X-16.40 Y6.00 E31.4063
;:G1 X-5.99 Y16.40 E31.9398
;:G1 X-7.94 Y16.40 E32.0105
;:G1 X-16.40 Y7.94 E32.4442
;:G1 X-16.40 Y9.88 E32.5146
;:G1 X-9.88 Y16.40 E32.8489
;:G1 X-11.82 Y16.40 E32.9192
;:G1 X-16.40 Y11.82 E33.1540
;:G1 X-16.40 Y13.77 E33.2247
;:G1 X-13.77 Y16.40 E33.3595
;:G1 X-15.71 Y16.40 E33.4299
;:G1 X-16.40 Y15.71 E33.4652
;:G1 X15.90 Y-6.40 F6000
;:G1 X16.40 Y-5.90 E33.4909 F4800
;support-end
;calPad A end
;calPad B start Z0.20
;support-start
;:G1 X-13.40 Y-13.64 F6000
;:G1 X-11.80 Y-14.66 E.0688 F4800
;:G1 X-10.00 Y-15.00 E.1352
;:G1 X10.00 Y-15.00 E.8603
;:G1 X11.95 Y-14.60 E.9324
;:G1 X13.59 Y-13.48 E1.0044
;:G1 X14.66 Y-11.80 E1.0766
;:G1 X15.00 Y-10.00 E1.1431
;:G1 X15.00 Y-6.60 E1.2663
;:G1 X16.60 Y-6.60 E1.3243
;:G1 X16.60 Y16.60 E2.1654
;:G1 X-16.60 Y16.60 E3.3690
;:G1 X-16.60 Y-16.60 E4.5726
;:G1 X-13.40 Y-16.60 E4.6887
;:G1 X-13.40 Y-13.64 E4.7960
;:G1 X-15.95 Y-16.40 F6000
;:G1 X-16.40 Y-15.95 E4.8190 F4800
;:G1 X-16.40 Y-14.05 E4.8879
;:G1 X-14.05 Y-16.40 E5.0084
;:G1 X-13.60 Y-16.40 E5.0247
;:G1 X-13.60 Y-14.95 E5.0773
;:G1 X-16.40 Y-12.15 E5.2208
;:G1 X-16.40 Y-10.26 E5.2894
;:G1 X-12.99 Y-13.66 E5.4639
;:G1 X-11.73 Y-14.47 E5.5182
;:G1 X-9.96 Y-14.80 E5.5835
;:G1 X-16.40 Y-8.36 E5.9137
;:G1 X-16.40 Y-6.46 E5.9826
;:G1 X-8.06 Y-14.80 E6.4102
;:G1 X-6.17 Y-14.80 E6.4787
;:G1 X-16.40 Y-4.57 E7.0032
;:G1 X-16.40 Y-2.67 E7.0721
;:G1 X-4.27 Y-14.80 E7.6940
;:G1 X-2.38 Y-14.80 E7.7625
;:G1 X-16.40 Y-.77 E8.4816
;:G1 X-16.40 Y1.12 E8.5501
;:G1 X-.48 Y-14.80 E9.3663
;:G1 X1.42 Y-14.80 E9.4352
;:G1 X-16.40 Y3.02 E10.3488
;:G1 X-16.40 Y4.92 E10.4177
;:G1 X3.31 Y-14.80 E11.4285
;:G1 X5.21 Y-14.80 E11.4974
;:G1 X-16.40 Y6.81 E12.6053
;:G1 X-16.40 Y8.71 E12.6742
;:G1 X7.11 Y-14.80 E13.8796
;:G1 X9.00 Y-14.80 E13.9481
;:G1 X-16.40 Y10.60 E15.2504
;:G1 X-16.40 Y12.50 E15.3192
;:G1 X10.75 Y-14.64 E16.7110
;:G1 X11.87 Y-14.42 E16.7524
;:G1 X12.19 Y-14.19 E16.7666
;:G1 X-16.40 Y14.40 E18.2325
;:G1 X-16.40 Y16.29 E18.3010
;:G1 X13.32 Y-13.42 E19.8245
;:G1 X13.45 Y-13.34 E19.8300
;:G1 X14.10 Y-12.31 E19.8742
;:G1 X-14.61 Y16.40 E21.3461
;:G1 X-12.71 Y16.40 E21.4150
;:G1 X14.62 Y-10.93 E22.8162
;:G1 X14.80 Y-9.98 E22.8513
;:G1 X14.80 Y-9.21 E22.8792
;:G1 X-10.81 Y16.40 E24.1922
;:G1 X-8.92 Y16.40 E24.2607
;:G1 X14.80 Y-7.32 E25.4769
;:G1 X14.80 Y-6.40 E25.5102
;:G1 X15.78 Y-6.40 E25.5458
;:G1 X-7.02 Y16.40 E26.7147
;:G1 X-5.13 Y16.40 E26.7832
;:G1 X16.40 Y-5.13 E27.8871
;:G1 X16.40 Y-3.23 E27.9560
;:G1 X-3.23 Y16.40 E28.9624
;:G1 X-1.33 Y16.40 E29.0313
;:G1 X16.40 Y-1.33 E29.9403
;:G1 X16.40 Y.56 E30.0088
;:G1 X.56 Y16.40 E30.8209
;:G1 X2.46 Y16.40 E30.8898
;:G1 X16.40 Y2.46 E31.6045
;:G1 X16.40 Y4.36 E31.6734
;:G1 X4.36 Y16.40 E32.2907
;:G1 X6.25 Y16.40 E32.3592
;:G1 X16.40 Y6.25 E32.8796
;:G1 X16.40 Y8.15 E32.9485
;:G1 X8.15 Y16.40 E33.3715
;:G1 X10.05 Y16.40 E33.4404
;:G1 X16.40 Y10.05 E33.7659
;:G1 X16.40 Y11.94 E33.8345
;:G1 X11.94 Y16.40 E34.0631
;:G1 X13.84 Y16.40 E34.1320
;:G1 X16.40 Y13.84 E34.2633
;:G1 X16.40 Y15.74 E34.3321
;:G1 X15.74 Y16.40 E34.3660
;support-end
;calPad B end
;calPad SA start Z0.20
;support-start
;:G1 X-13.40 Y-13.64 F6000
;:G1 X-11.80 Y-14.66 E.0688 F4800
;:G1 X-10.00 Y-15.00 E.1352
;:G1 X10.00 Y-15.00 E.8603
;:G1 X11.95 Y-14.60 E.9324
;:G1 X13.59 Y-13.48 E1.0044
;:G1 X14.66 Y-11.80 E1.0766
;:G1 X15.00 Y-10.00 E1.1431
;:G1 X15.00 Y-6.60 E1.2663
;:G1 X16.60 Y-6.60 E1.3243
;:G1 X16.60 Y16.60 E2.1654
;:G1 X-16.60 Y16.60 E3.3690
;:G1 X-16.60 Y-16.60 E4.5726
;:G1 X-13.40 Y-16.60 E4.6887
;:G1 X-13.40 Y-13.64 E4.7960
;:G1 X-13.34 Y-13.44 F6000
;:G1 X16.40 Y16.30 E6.3207 F4800
;:G1 X16.40 Y15.73 E6.3414
;:G1 X-12.99 Y-13.66 E7.8482
;:G1 X-12.65 Y-13.88 E7.8629
;:G1 X16.40 Y15.16 E9.3521
;:G1 X16.40 Y14.60 E9.3724
;:G1 X-12.30 Y-14.10 E10.8438
;:G1 X-11.96 Y-14.33 E10.8587
;:G1 X16.40 Y14.03 E12.3127
;:G1 X16.40 Y13.46 E12.3334
;:G1 X-11.57 Y-14.50 E13.7672
;:G1 X-11.09 Y-14.59 E13.7849
;:G1 X16.40 Y12.90 E15.1943
;:G1 X16.40 Y12.33 E15.2150
;:G1 X-10.61 Y-14.68 E16.5998
;:G1 X-10.13 Y-14.77 E16.6175
;:G1 X16.40 Y11.76 E17.9777
;:G1 X16.40 Y11.19 E17.9983
;:G1 X-9.59 Y-14.80 E19.3308
;:G1 X-9.03 Y-14.80 E19.3512
;:G1 X16.40 Y10.63 E20.6550
;:G1 X16.40 Y10.06 E20.6756
;:G1 X-8.46 Y-14.80 E21.9502
;:G1 X-7.89 Y-14.80 E21.9709
;:G1 X16.40 Y9.49 E23.2162
;:G1 X16.40 Y8.93 E23.2365
;:G1 X-7.32 Y-14.80 E24.4529
;:G1 X-6.76 Y-14.80 E24.4732
;:G1 X16.40 Y8.36 E25.6606
;:G1 X16.40 Y7.79 E25.6813
;:G1 X-6.19 Y-14.80 E26.8395
;:G1 X-5.62 Y-14.80 E26.8602
;:G1 X16.40 Y7.23 E27.9894
;:G1 X16.40 Y6.66 E28.0100
;:G1 X-5.06 Y-14.80 E29.1103
;:G1 X-4.49 Y-14.80 E29.1310
;:G1 X16.40 Y6.09 E30.2020
;:G1 X16.40 Y5.52 E30.2227
;:G1 X-3.92 Y-14.80 E31.2645
;:G1 X-3.36 Y-14.80 E31.2848
;:G1 X16.40 Y4.96 E32.2979
;:G1 X16.40 Y4.39 E32.3185
;:G1 X-2.79 Y-14.80 E33.3024
;:G1 X-2.22 Y-14.80 E33.3231
;:G1 X16.40 Y3.82 E34.2777
;:G1 X16.40 Y3.26 E34.2980
;:G1 X-1.65 Y-14.80 E35.2237
;:G1 X-1.09 Y-14.80 E35.2440
;:G1 X16.40 Y2.69 E36.1407
;:G1 X16.40 Y2.12 E36.1614
;:G1 X-.52 Y-14.80 E37.0289
;:G1 X.05 Y-14.80 E37.0496
;:G1 X16.40 Y1.55 E37.8878
;:G1 X16.40 Y.99 E37.9081
;:G1 X.61 Y-14.80 E38.7177
;:G1 X1.18 Y-14.80 E38.7384
;:G1 X16.40 Y.42 E39.5187
;:G1 X16.40 Y-.15 E39.5394
;:G1 X1.75 Y-14.80 E40.2905
;:G1 X2.32 Y-14.80 E40.3111
;:G1 X16.40 Y-.71 E41.0333
;:G1 X16.40 Y-1.28 E41.0539
;:G1 X2.88 Y-14.80 E41.7471
;:G1 X3.45 Y-14.80 E41.7678
;:G1 X16.40 Y-1.85 E42.4317
;:G1 X16.40 Y-2.42 E42.4524
;:G1 X4.02 Y-14.80 E43.0871
;:G1 X4.58 Y-14.80 E43.1074
;:G1 X16.40 Y-2.98 E43.7134
;:G1 X16.40 Y-3.55 E43.7341
;:G1 X5.15 Y-14.80 E44.3109
;:G1 X5.72 Y-14.80 E44.3315
;:G1 X16.40 Y-4.12 E44.8791
;:G1 X16.40 Y-4.68 E44.8994
;:G1 X6.29 Y-14.80 E45.4180
;:G1 X6.85 Y-14.80 E45.4383
;:G1 X14.80 Y-6.85 E45.8459
;:G1 X14.80 Y-7.42 E45.8666
;:G1 X7.42 Y-14.80 E46.2449
;:G1 X7.99 Y-14.80 E46.2656
;:G1 X14.80 Y-7.99 E46.6148
;:G1 X14.80 Y-8.55 E46.6351
;:G1 X8.55 Y-14.80 E46.9555
;:G1 X9.12 Y-14.80 E46.9762
;:G1 X14.80 Y-9.12 E47.2674
;:G1 X14.80 Y-9.69 E47.2880
;:G1 X9.69 Y-14.80 E47.5500
;:G1 X10.32 Y-14.73 E47.5730
;:G1 X14.74 Y-10.32 E47.7994
;:G1 X14.61 Y-11.01 E47.8248
;:G1 X11.04 Y-14.58 E48.0079
;:G1 X11.75 Y-14.44 E48.0341
;:G1 X14.48 Y-11.71 E48.1741
;:G1 X13.49 Y-13.26 E48.2407
;:G1 X13.36 Y-13.39 E48.2474
;:G1 X15.25 Y-6.40 F6000
;:G1 X16.40 Y-5.25 E48.3064 F4800
;:G1 X16.40 Y-5.82 E48.3270
;:G1 X15.82 Y-6.40 E48.3568
;:G1 X16.40 Y-6.39 E48.3778
;:G1 X-13.60 Y-15.97 F6000
;:G1 X-14.03 Y-16.40 E48.3999 F4800
;:G1 X-14.60 Y-16.40 E48.4205
;:G1 X-13.60 Y-15.40 E48.4718
;:G1 X-13.60 Y-14.83 E48.4924
;:G1 X-15.16 Y-16.40 E48.5727
;:G1 X-15.73 Y-16.40 E48.5934
;:G1 X-13.60 Y-14.27 E48.7026
;:G1 X-13.60 Y-13.70 E48.7232
;:G1 X-16.30 Y-16.40 E48.8617
;:G1 X-16.40 Y-16.40 E48.8653
;:G1 X-16.40 Y-15.93 E48.8823
;:G1 X15.93 Y16.40 E50.5399
;:G1 X15.37 Y16.40 E50.5602
;:G1 X-16.40 Y-15.36 E52.1888
;:G1 X-16.40 Y-14.80 E52.2091
;:G1 X14.80 Y16.40 E53.8087
;:G1 X14.23 Y16.40 E53.8294
;:G1 X-16.40 Y-14.23 E55.3998
;:G1 X-16.40 Y-13.66 E55.4205
;:G1 X13.66 Y16.40 E56.9616
;:G1 X13.10 Y16.40 E56.9819
;:G1 X-16.40 Y-13.10 E58.4944
;:G1 X-16.40 Y-12.53 E58.5151
;:G1 X12.53 Y16.40 E59.9983
;:G1 X11.96 Y16.40 E60.0190
;:G1 X-16.40 Y-11.96 E61.4730
;:G1 X-16.40 Y-11.40 E61.4933
;:G1 X11.40 Y16.40 E62.9186
;:G1 X10.83 Y16.40 E62.9393
;:G1 X-16.40 Y-10.83 E64.3354
;:G1 X-16.40 Y-10.26 E64.3560
;:G1 X10.26 Y16.40 E65.7229
;:G1 X9.69 Y16.40 E65.7436
;:G1 X-16.40 Y-9.69 E67.0812
;:G1 X-16.40 Y-9.13 E67.1015
;:G1 X9.13 Y16.40 E68.4104
;:G1 X8.56 Y16.40 E68.4311
;:G1 X-16.40 Y-8.56 E69.7108
;:G1 X-16.40 Y-7.99 E69.7315
;:G1 X7.99 Y16.40 E70.9820
;:G1 X7.43 Y16.40 E71.0023
;:G1 X-16.40 Y-7.43 E72.2240
;:G1 X-16.40 Y-6.86 E72.2447
;:G1 X6.86 Y16.40 E73.4373
;:G1 X6.29 Y16.40 E73.4579
;:G1 X-16.40 Y-6.29 E74.6212
;:G1 X-16.40 Y-5.72 E74.6419
;:G1 X5.72 Y16.40 E75.7760
;:G1 X5.16 Y16.40 E75.7963
;:G1 X-16.40 Y-5.16 E76.9017
;:G1 X-16.40 Y-4.59 E76.9224
;:G1 X4.59 Y16.40 E77.9985
;:G1 X4.02 Y16.40 E78.0192
;:G1 X-16.40 Y-4.02 E79.0661
;:G1 X-16.40 Y-3.46 E79.0864
;:G1 X3.46 Y16.40 E80.1047
;:G1 X2.89 Y16.40 E80.1253
;:G1 X-16.40 Y-2.89 E81.1143
;:G1 X-16.40 Y-2.32 E81.1350
;:G1 X2.32 Y16.40 E82.0948
;:G1 X1.76 Y16.40 E82.1151
;:G1 X-16.40 Y-1.75 E83.0459
;:G1 X-16.40 Y-1.19 E83.0662
;:G1 X1.19 Y16.40 E83.9680
;:G1 X.62 Y16.40 E83.9887
;:G1 X-16.40 Y-.62 E84.8613
;:G1 X-16.40 Y-.05 E84.8820
;:G1 X.05 Y16.40 E85.7254
;:G1 X-.51 Y16.40 E85.7457
;:G1 X-16.40 Y.51 E86.5604
;:G1 X-16.40 Y1.08 E86.5810
;:G1 X-1.08 Y16.40 E87.3665
;:G1 X-1.65 Y16.40 E87.3872
;:G1 X-16.40 Y1.65 E88.1434
;:G1 X-16.40 Y2.21 E88.1637
;:G1 X-2.21 Y16.40 E88.8912
;:G1 X-2.78 Y16.40 E88.9119
;:G1 X-16.40 Y2.78 E89.6102
;:G1 X-16.40 Y3.35 E89.6309
;:G1 X-3.35 Y16.40 E90.2999
;:G1 X-3.92 Y16.40 E90.3206
;:G1 X-16.40 Y3.92 E90.9604
;:G1 X-16.40 Y4.48 E90.9808
;:G1 X-4.48 Y16.40 E91.5919
;:G1 X-5.05 Y16.40 E91.6126
;:G1 X-16.40 Y5.05 E92.1945
;:G1 X-16.40 Y5.62 E92.2151
;:G1 X-5.62 Y16.40 E92.7678
;:G1 X-6.18 Y16.40 E92.7881
;:G1 X-16.40 Y6.19 E93.3119
;:G1 X-16.40 Y6.75 E93.3322
;:G1 X-6.75 Y16.40 E93.8269
;:G1 X-7.32 Y16.40 E93.8476
;:G1 X-16.40 Y7.32 E94.3131
;:G1 X-16.40 Y7.89 E94.3338
;:G1 X-7.89 Y16.40 E94.7701
;:G1 X-8.45 Y16.40 E94.7904
;:G1 X-16.40 Y8.45 E95.1980
;:G1 X-16.40 Y9.02 E95.2187
;:G1 X-9.02 Y16.40 E95.5970
;:G1 X-9.59 Y16.40 E95.6177
;:G1 X-16.40 Y9.59 E95.9669
;:G1 X-16.40 Y10.15 E95.9872
;:G1 X-10.15 Y16.40 E96.3076
;:G1 X-10.72 Y16.40 E96.3283
;:G1 X-16.40 Y10.72 E96.6195
;:G1 X-16.40 Y11.29 E96.6401
;:G1 X-11.29 Y16.40 E96.9021
;:G1 X-11.86 Y16.40 E96.9228
;:G1 X-16.40 Y11.86 E97.1556
;:G1 X-16.40 Y12.42 E97.1759
;:G1 X-12.42 Y16.40 E97.3799
;:G1 X-12.99 Y16.40 E97.4006
;:G1 X-16.40 Y12.99 E97.5754
;:G1 X-16.40 Y13.56 E97.5961
;:G1 X-13.56 Y16.40 E97.7417
;:G1 X-14.12 Y16.40 E97.7620
;:G1 X-16.40 Y14.12 E97.8789
;:G1 X-16.40 Y14.69 E97.8996
;:G1 X-14.69 Y16.40 E97.9872
;:G1 X-15.26 Y16.40 E98.0079
;:G1 X-16.40 Y15.26 E98.0663
;:G1 X-16.40 Y15.83 E98.0870
;:G1 X-15.83 Y16.40 E98.1162
;:G1 X-16.40 Y16.39 E98.1369
;support-end
;calPad SA end
;calPad SB start Z0.20
;support-start
;:G1 X-13.40 Y-13.64 F6000
;:G1 X-11.80 Y-14.66 E.0688 F4800
;:G1 X-10.00 Y-15.00 E.1352
;:G1 X10.00 Y-15.00 E.8603
;:G1 X11.95 Y-14.60 E.9324
;:G1 X13.59 Y-13.48 E1.0044
;:G1 X14.66 Y-11.80 E1.0766
;:G1 X15.00 Y-10.00 E1.1431
;:G1 X15.00 Y-6.60 E1.2663
;:G1 X16.60 Y-6.60 E1.3243
;:G1 X16.60 Y16.60 E2.1654
;:G1 X-16.60 Y16.60 E3.3690
;:G1 X-16.60 Y-16.60 E4.5726
;:G1 X-13.40 Y-16.60 E4.6887
;:G1 X-13.40 Y-13.64 E4.7960
;:G1 X-16.40 Y-16.03 F6000
;:G1 X-16.03 Y-16.40 E4.8149 F4800
;:G1 X-15.46 Y-16.40 E4.8356
;:G1 X-16.40 Y-15.46 E4.8838
;:G1 X-16.40 Y-14.89 E4.9045
;:G1 X-14.89 Y-16.40 E4.9819
;:G1 X-14.32 Y-16.40 E5.0025
;:G1 X-16.40 Y-14.32 E5.1092
;:G1 X-16.40 Y-13.76 E5.1295
;:G1 X-13.76 Y-16.40 E5.2648
;:G1 X-13.60 Y-16.40 E5.2706
;:G1 X-13.60 Y-15.99 E5.2855
;:G1 X-16.40 Y-13.19 E5.4291
;:G1 X-16.40 Y-12.62 E5.4497
;:G1 X-13.60 Y-15.42 E5.5933
;:G1 X-13.60 Y-14.85 E5.6139
;:G1 X-16.40 Y-12.06 E5.7572
;:G1 X-16.40 Y-11.49 E5.7779
;:G1 X-13.60 Y-14.29 E5.9215
;:G1 X-13.60 Y-13.72 E5.9421
;:G1 X-16.40 Y-10.92 E6.0857
;:G1 X-16.40 Y-10.35 E6.1064
;:G1 X-13.26 Y-13.49 E6.2673
;:G1 X-11.71 Y-14.48 E6.3340
;:G1 X-16.40 Y-9.79 E6.5745
;:G1 X-16.40 Y-9.22 E6.5951
;:G1 X-11.01 Y-14.60 E6.8712
;:G1 X-10.32 Y-14.73 E6.8967
;:G1 X-16.40 Y-8.65 E7.2084
;:G1 X-16.40 Y-8.09 E7.2287
;:G1 X-9.69 Y-14.80 E7.5727
;:G1 X-9.12 Y-14.80 E7.5934
;:G1 X-16.40 Y-7.52 E7.9666
;:G1 X-16.40 Y-6.95 E7.9873
;:G1 X-8.55 Y-14.80 E8.3898
;:G1 X-7.99 Y-14.80 E8.4101
;:G1 X-16.40 Y-6.38 E8.8415
;:G1 X-16.40 Y-5.82 E8.8618
;:G1 X-7.42 Y-14.80 E9.3222
;:G1 X-6.85 Y-14.80 E9.3429
;:G1 X-16.40 Y-5.25 E9.8325
;:G1 X-16.40 Y-4.68 E9.8532
;:G1 X-6.28 Y-14.80 E10.3720
;:G1 X-5.72 Y-14.80 E10.3923
;:G1 X-16.40 Y-4.12 E10.9399
;:G1 X-16.40 Y-3.55 E10.9606
;:G1 X-5.15 Y-14.80 E11.5374
;:G1 X-4.58 Y-14.80 E11.5580
;:G1 X-16.40 Y-2.98 E12.1640
;:G1 X-16.40 Y-2.41 E12.1847
;:G1 X-4.02 Y-14.80 E12.8197
;:G1 X-3.45 Y-14.80 E12.8404
;:G1 X-16.40 Y-1.85 E13.5043
;:G1 X-16.40 Y-1.28 E13.5250
;:G1 X-2.88 Y-14.80 E14.2181
;:G1 X-2.31 Y-14.80 E14.2388
;:G1 X-16.40 Y-.71 E14.9612
;:G1 X-16.40 Y-.15 E14.9815
;:G1 X-1.75 Y-14.80 E15.7326
;:G1 X-1.18 Y-14.80 E15.7533
;:G1 X-16.40 Y.42 E16.5336
;:G1 X-16.40 Y.99 E16.5543
;:G1 X-.61 Y-14.80 E17.3638
;:G1 X-.05 Y-14.80 E17.3841
;:G1 X-16.40 Y1.55 E18.2224
;:G1 X-16.40 Y2.12 E18.2431
;:G1 X.52 Y-14.80 E19.1106
;:G1 X1.09 Y-14.80 E19.1312
;:G1 X-16.40 Y2.69 E20.0279
;:G1 X-16.40 Y3.26 E20.0486
;:G1 X1.66 Y-14.80 E20.9746
;:G1 X2.22 Y-14.80 E20.9949
;:G1 X-16.40 Y3.82 E21.9495
;:G1 X-16.40 Y4.39 E21.9702
;:G1 X2.79 Y-14.80 E22.9540
;:G1 X3.36 Y-14.80 E22.9747
;:G1 X-16.40 Y4.96 E23.9878
;:G1 X-16.40 Y5.52 E24.0081
;:G1 X3.92 Y-14.80 E25.0499
;:G1 X4.49 Y-14.80 E25.0706
;:G1 X-16.40 Y6.09 E26.1416
;:G1 X-16.40 Y6.66 E26.1623
;:G1 X5.06 Y-14.80 E27.2626
;:G1 X5.63 Y-14.80 E27.2832
;:G1 X-16.40 Y7.23 E28.4127
;:G1 X-16.40 Y7.79 E28.4330
;:G1 X6.19 Y-14.80 E29.5912
;:G1 X6.76 Y-14.80 E29.6119
;:G1 X-16.40 Y8.36 E30.7993
;:G1 X-16.40 Y8.93 E30.8199
;:G1 X7.33 Y-14.80 E32.0366
;:G1 X7.89 Y-14.80 E32.0569
;:G1 X-16.40 Y9.49 E33.3022
;:G1 X-16.40 Y10.06 E33.3229
;:G1 X8.46 Y-14.80 E34.5975
;:G1 X9.03 Y-14.80 E34.6182
;:G1 X-16.40 Y10.63 E35.9220
;:G1 X-16.40 Y11.20 E35.9426
;:G1 X9.59 Y-14.80 E37.2754
;:G1 X10.13 Y-14.77 E37.2950
;:G1 X-16.40 Y11.76 E38.6552
;:G1 X-16.40 Y12.33 E38.6759
;:G1 X10.60 Y-14.67 E40.0602
;:G1 X11.07 Y-14.58 E40.0775
;:G1 X-16.40 Y12.90 E41.4862
;:G1 X-16.40 Y13.46 E41.5065
;:G1 X11.55 Y-14.48 E42.9392
;:G1 X11.98 Y-14.34 E42.9556
;:G1 X-16.40 Y14.03 E44.4104
;:G1 X-16.40 Y14.60 E44.4311
;:G1 X12.31 Y-14.11 E45.9030
;:G1 X12.65 Y-13.88 E45.9179
;:G1 X-16.40 Y15.17 E47.4073
;:G1 X-16.40 Y15.73 E47.4276
;:G1 X12.98 Y-13.65 E48.9339
;:G1 X13.32 Y-13.42 E48.9488
;:G1 X-16.40 Y16.30 E50.4726
;:G1 X-16.40 Y16.40 E50.4762
;:G1 X-15.93 Y16.40 E50.4932
;:G1 X13.58 Y-13.12 E52.0065
;:G1 X13.81 Y-12.77 E52.0217
;:G1 X-15.36 Y16.40 E53.5172
;:G1 X-14.80 Y16.40 E53.5375
;:G1 X14.03 Y-12.42 E55.0154
;:G1 X14.25 Y-12.08 E55.0301
;:G1 X-14.23 Y16.40 E56.4902
;:G1 X-13.66 Y16.40 E56.5109
;:G1 X14.47 Y-11.73 E57.9531
;:G1 X14.56 Y-11.26 E57.9705
;:G1 X-13.10 Y16.40 E59.3886
;:G1 X-12.53 Y16.40 E59.4093
;:G1 X14.65 Y-10.78 E60.8028
;:G1 X14.74 Y-10.30 E60.8205
;:G1 X-11.96 Y16.40 E62.1894
;:G1 X-11.39 Y16.40 E62.2101
;:G1 X14.80 Y-9.79 E63.5529
;:G1 X14.80 Y-9.23 E63.5732
;:G1 X-10.83 Y16.40 E64.8872
;:G1 X-10.26 Y16.40 E64.9079
;:G1 X14.80 Y-8.66 E66.1927
;:G1 X14.80 Y-8.09 E66.2134
;:G1 X-9.69 Y16.40 E67.4690
;:G1 X-9.13 Y16.40 E67.4893
;:G1 X14.80 Y-7.53 E68.7162
;:G1 X14.80 Y-6.96 E68.7369
;:G1 X-8.56 Y16.40 E69.9345
;:G1 X-7.99 Y16.40 E69.9552
;:G1 X14.81 Y-6.40 E71.1242
;:G1 X15.38 Y-6.40 E71.1448
;:G1 X-7.42 Y16.40 E72.3138
;:G1 X-6.86 Y16.40 E72.3341
;:G1 X15.94 Y-6.40 E73.5030
;:G1 X16.40 Y-6.40 E73.5197
;:G1 X16.40 Y-6.29 E73.5237
;:G1 X-6.29 Y16.40 E74.6870
;:G1 X-5.72 Y16.40 E74.7077
;:G1 X16.40 Y-5.72 E75.8418
;:G1 X16.40 Y-5.16 E75.8621
;:G1 X-5.16 Y16.40 E76.9675
;:G1 X-4.59 Y16.40 E76.9882
;:G1 X16.40 Y-4.59 E78.0643
;:G1 X16.40 Y-4.02 E78.0850
;:G1 X-4.02 Y16.40 E79.1319
;:G1 X-3.45 Y16.40 E79.1526
;:G1 X16.40 Y-3.45 E80.1703
;:G1 X16.40 Y-2.89 E80.1906
;:G1 X-2.89 Y16.40 E81.1796
;:G1 X-2.32 Y16.40 E81.2003
;:G1 X16.40 Y-2.32 E82.1601
;:G1 X16.40 Y-1.75 E82.1807
;:G1 X-1.75 Y16.40 E83.1113
;:G1 X-1.19 Y16.40 E83.1316
;:G1 X16.40 Y-1.19 E84.0334
;:G1 X16.40 Y-.62 E84.0541
;:G1 X-.62 Y16.40 E84.9267
;:G1 X-.05 Y16.40 E84.9474
;:G1 X16.40 Y-.05 E85.7908
;:G1 X16.40 Y.51 E85.8111
;:G1 X.51 Y16.40 E86.6258
;:G1 X1.08 Y16.40 E86.6464
;:G1 X16.40 Y1.08 E87.4319
;:G1 X16.40 Y1.65 E87.4525
;:G1 X1.65 Y16.40 E88.2088
;:G1 X2.22 Y16.40 E88.2294
;:G1 X16.40 Y2.22 E88.9565
;:G1 X16.40 Y2.78 E88.9768
;:G1 X2.78 Y16.40 E89.6751
;:G1 X3.35 Y16.40 E89.6957
;:G1 X16.40 Y3.35 E90.3648
;:G1 X16.40 Y3.92 E90.3855
;:G1 X3.92 Y16.40 E91.0253
;:G1 X4.48 Y16.40 E91.0456
;:G1 X16.40 Y4.48 E91.6568
;:G1 X16.40 Y5.05 E91.6774
;:G1 X5.05 Y16.40 E92.2593
;:G1 X5.62 Y16.40 E92.2800
;:G1 X16.40 Y5.62 E92.8327
;:G1 X16.40 Y6.19 E92.8534
;:G1 X6.19 Y16.40 E93.3768
;:G1 X6.75 Y16.40 E93.3971
;:G1 X16.40 Y6.75 E93.8919
;:G1 X16.40 Y7.32 E93.9126
;:G1 X7.32 Y16.40 E94.3781
;:G1 X7.89 Y16.40 E94.3988
;:G1 X16.40 Y7.89 E94.8351
;:G1 X16.40 Y8.45 E94.8554
;:G1 X8.45 Y16.40 E95.2630
;:G1 X9.02 Y16.40 E95.2836
;:G1 X16.40 Y9.02 E95.6620
;:G1 X16.40 Y9.59 E95.6827
;:G1 X9.59 Y16.40 E96.0318
;:G1 X10.16 Y16.40 E96.0525
;:G1 X16.40 Y10.16 E96.3724
;:G1 X16.40 Y10.72 E96.3927
;:G1 X10.72 Y16.40 E96.6839
;:G1 X11.29 Y16.40 E96.7046
;:G1 X16.40 Y11.29 E96.9666
;:G1 X16.40 Y11.86 E96.9873
;:G1 X11.86 Y16.40 E97.2200
;:G1 X12.42 Y16.40 E97.2403
;:G1 X16.40 Y12.42 E97.4444
;:G1 X16.40 Y12.99 E97.4651
;:G1 X12.99 Y16.40 E97.6399
;:G1 X13.56 Y16.40 E97.6605
;:G1 X16.40 Y13.56 E97.8062
;:G1 X16.40 Y14.13 E97.8268
;:G1 X14.13 Y16.40 E97.9432
;:G1 X14.69 Y16.40 E97.9635
;:G1 X16.40 Y14.69 E98.0512
;:G1 X16.40 Y15.26 E98.0718
;:G1 X15.26 Y16.40 E98.1303
;:G1 X15.83 Y16.40 E98.1510
;:G1 X16.40 Y15.83 E98.1802
;:G1 X16.39 Y16.40 E98.2008
;support-end
;calPad SB end
M109"""


our_file = open(sys.argv[1], 'rb+')
for binary_data in header_hex:
    our_file.write(binary_data)
    
if use_calpads: #only required for ditto and mirror
    file_data = file_data.replace("M109", calPad_content, 1)

our_file.write(file_data.encode('utf-8')) # add the actual gcode for the printer