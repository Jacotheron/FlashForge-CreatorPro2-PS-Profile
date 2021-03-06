# FlashForge Creator Pro 2 PrusaSlicer Profile

This project aims to provide users of the FlashForge Creator Pro 2 (and similar 3D printers) an option to print using PrusaSlicer (Slic3er and SuperSlicer should also be supported directly). It can also be a starting point for other slicers as well.

I use PrusaSlicer for a couple of years now, and it fits with my many other printers, so I wanted to ensure I could use my FF Creator Pro 2 with it as well.

This project would not have been possible without help from the community. I would like to those that helped the most:
 * Frank Paynter - [Paynter's Palace](https://www.fpaynter.com/2021/09/flashforge-creator-pro-2-idex-profile-for-prusa-slicer-2-3/) - he provided me with the starting profile, which was a great start.
 * CME-Linux (here on Github) - [Github Issue](https://github.com/slic3r/Slic3r/issues/4869) - he performed a very useful analysis of the binary blob at the start of a .gx file.
 * mbarlett21 (also here on Github, in same issue thread) - also a few right pointers regarding multi-head systems and the binary blob.
 
## Features

* Use PrusaSlicer to slice 3d prints to be printed on your FlashForge.
* Adds a bunch of materials for use in the printer.
* Provides many quality options to choose from (thanks Frank for the many options).
* Creates 5 different Printer configurations:
	- CreatorPro2 E1 right only extrusion - single extruder, using the right extruder (aka T0).
	- CreatorPro2 E2 left only extrusion - single extruder, using the left extruder (aka T1).
	- CreatorPro2 Dual extrusion - 2 available extruders, used for multi-material prints (supports print settings with dissolvable support material).
	- CreatorPro2 E1 right E2 Ditto - Ditto printing using the right extruder (as the primary extruder, left extruder will follow its example).
	- CreatorPro2 E1 right E2 Mirror - Mirror printing using the right extruder (as the primary extruder, left extruder will mirror its example).
* Show the print thumbnail on the printer when you select the file (also show the estimated printing time). Note that if no thumbnail is found, it will generate a black image. Due to sizing constraints, image have to be 80x60.
 
## Installation

Before installation, please note that:

* In order to generate the binary blob, and enable ditto/mirror printing, we need to post-process the gcode.
* The post-process script is written in Python 3 (I used 3.8 for development, thus any newer should work) and thus requires Python 3. In addition Image support comes from Pillow, which is also required to be installed.
* Everything was tested with PrusaSlicer 2.4.0 - it may work with older versions, but that is not guaranteed. PS 2.4.1 have since been released and is known to work.

### Python & Pillow Installation

If you need to install Python head over to [Python Downloads](https://www.python.org/downloads/) and download the relevant installer for your Operating System. 
1. Simply run the installer,
2. Select the Customize option, 
3. Choose a path where it should be installed (ideally you want this to be short, for example C:/Python3.x/) 
4. Ensure you check the box for "Add Python3.x to PATH"
5. Let the installation complete.

We want to use a short path, so that we can easily use it [full instructions on how it is to be setup](https://manual.slic3r.org/advanced/post-processing).

We now want to install Pillow for Python [Pillow Installation](https://pillow.readthedocs.io/en/stable/installation.html).
Using Command Prompt run the following 2 commands:

```
python -m pip install --upgrade pip
python -m pip install --upgrade Pillow
```

PIP is a package manager for Python, allowing us to simply install Pillow in the right place, ready to be used.

### Vendor File and Post Processor Installation

Now on to the installation

1. This project contains, at time of writing, 2 folders, each with 1 file. Download the whole project
2. The file "vendor/FlashForge.ini" (mentioned below as Vendor file) should be placed inside of the PrusaSlicer's AppData folder (typically on Windows at "C:/Users/<username\>/AppData/Roaming/PrusaSlicer/vendor/")
3. The file "post-processor/ff-creator-post-processor.py" (Post Process Script) can be placed anywhere on your computer; I like to keep it in a folder "post-processor" also in the PrusaSlicer AppData. Make a note of the file's location, as we need to edit the Vendor file to use this for post-processing.
4. Open the Vendor file ("vendor/FlashForge.ini") in your favorite plain text editor (Notepad works, I use Notepad++); go to the line that starts with "post_process" and edit it to point to your Post Process Script (note the use of double back-slashes "\\\\\\" for Windows as folder separators). If the file path contains any space, it should be preceeded by an exclamation mark "!" (also ensure that it load your correct python version, directly from where it is installed). Save the file.
5. You can now open PrusaSlicer, and using its "Configuration > Configuration Wizard" add the FlashForge:
	1. Go to Other Vendors, and select "FlashForge"
	2. Go to "FlashForge FFF" and select the 0.4mm CreatorPro2 (sorry we don't currently have an image for it)
	3. You may go further through the options or just Finish.
	4. The printers should now be available from the "Printer" select under System Presets. You are welcome to make customizations and save them as separate profiles
5. The Print settings are available from the list inside System presets, and the filament is there as well.

If you did everything well, you should be able to slice a new object for printing, and have the post-processor run (open the sliced file in a text editor to confirm that it did indeed run and included the binary blob).

**This is beta software at this stage. Do not leave the printer unattended. Also ensure that the type of printing works as expected on something small, before spending many hours printing something only to have it fail due to some unexpected issue.**

## Using this profile
In PrusaSlicer we have 3 sets of dropdowns (Print Settings, Filament and Printer).

1. Start with the printer, and select the option you would like (this profile defines the options mentioned at the features):
	1. Dual Extrusion:
		1. Typically used when you either have 2 colors that should be used in the same job, of 2 different materials that should be used in the same job.
		2. This printer allows the Print Settings selections for Soluble supports.
	3. Ditto:
		1. Typically used to print 2x identical parts as defined. Both heads are used simultaneously and moves are identical. We only define the Right hand side of the build plate, left side will be identical.
	2. Mirror:
		1. Typically used to print 2x almost identical parts. Like Ditto, Mirror uses both heads, but the left head does the oposite in X than what the right head does.
		2. This allows you to print a left and right side of something, by only importing the right side (saving a lot of time).
	3. Right Only / Left Only
		1. This is used in print jobs where you only need one head for the whole print. 
		2. By alternating the use of left and right extruders for print job, you can save time with loading of the next print's color.
3. Then select the print settings you want to use:
	1. The included presets range between 0.05mm and 0.3mm layer heights; choose the option you would like.
	2. If using Dual, you can also select one of the Soluble options.
	3. If Using Dual, you can select the Draft Shield options, which helps to reduce ooze blobs on the print.
4. Now select the filament options to use.
5. Import your model into the slicer and let it slice.
6. Always confirm the slice to be successful and Export the Gcode. A small black window may appear for a moment - that is normal and is the post processor doing its job.

## Notes

* In PrusaSlicer the first extruder (and Filament selector) is always the Right Extruder (in firmware T0), unless you are using the Left Only printing mode.
* While I have attempted to test everything, there may be issues. Test out the most common setups to ensure they will work for you.
* Regarding the maximum printable dimensions, I usually work with a 5mm "keep-out" zone on all sides - this ensures that the print will succeed regardless of tiny differences and other inaccuracies. You are welcome to see exactly what your machine is capable of (my estimates are you might get a few extra mm on some sides).

## Troubleshooting

### "File open failed" on printer
This issue may commonly happens when the filename is too long. If you get this error, first try shortening the file, and then try printing it again.

I did not test where the limit is, but typically if I shorten it, it works.

If the issue persists, it may be an incorrect header, please report this.

### Print stopping just after completing the Start Gcode
This issue should be rare, but in the instances where it happened to me, it was with either Ditto or Mirror modes, and the CalPad was not in the file. If this happens to you, please check to confirm that the CalPad is in the file.

### Other issues
Please report other issues using the issue tracker here on GitHub, provide as much detail as possible. We will try it out and see how it can be resolved.


## The .gx file format
Here is a technical breakdown of the file format, specifically regarding the binary blob. Locations are mentioned as their Hex location in the file.

* General:
	- File is officially text, with a big binary blob for the header.
	- Numbers inside the binary blob are "little endian" style.
* Header:
	- the file starts with plain text string: "xgcode 1.0" followed by a new line, and NULL terminated. This brings us to location 0x0B
* Binary Block:
	- 0x0C -> a 4-byte (32-bit) value, which seems to always be 0.
	- 0x10 -> a 4 byte value, which points to the start location of the image inside the block, also constant at 0x3A (58).
	- 0x14 -> a 4 byte value, which points to the end of the image block/start of gcode at location 0x38B0 (this is where endianness affects us, actual value is read as 0xB038 -> number is 14512).
	- 0x18 -> an identical 4-byte value as at 0x14.
	- 0x1C -> a 4 byte value defining the estimated printing time in seconds (shown when selecting the file for print).
	- 0x20 -> 4-byte value for filament usage in mm on right extruder (used for progress bar during print).
	- 0x24 -> 4-byte value for filament usage in mm on left extruder (if present/used).
	- 0x28 -> 2 byte extruder mode; defaults to value 3, unless ditto (19) or mirror (35) - based on my demo slices from FlashPrint 5.
	- 0x2A -> 2 bytes value for layer height in microns (for 0.15mm it is 150).
	- 0x2C -> 2 null bytes -> in no demo, was I able to find any value for this.
	- 0x2E -> 2 bytes for the number of shells.
	- 0x30 -> 2 bytes for the print speed (mine uses the perimieter speed).
	- 0x32 -> 2 bytes for the platform temperature.
	- 0x34 -> 2 bytes for the right extruder temperature.
	- 0x36 -> 2 bytes for the left extruder temperature (if available).
	- 0x38 -> 2 bytes with constant value "0xFEFE", no idea what it is for.
	- 0x3A -> start of BMP image code, using RGB (3x 1 byte channels), thus 24bits per pixel
* Image:
	- Due to the color touch screen, the image can use any RGB bitmap image. In one of the notes it was said that it should be grey, but the original slicer uses a dark green for 2nd extruder sections, and PS thumbnails work very well.
	- The image size should be no more and no less than a 80x60. The post processor also does not support multiple images.
	- If no image is found, the post-processor will use a simple black image in its place as fallback (binary size is constant)
* CalPad:
	- When using Mirror or Ditto modes, a CalPad block is required, right before the Tool select "M109" is called. Without it the print is instantly "completed".
	- From what I was able to find out, it loads the nozzle height difference and if there is too much height difference between the 2, the higher one will print a thin "raft" so that it can print on top of it.
	- Typically in FlashPrint this CalPad is auto generated to be right below the part being printed. PS can't generate this and as such a very basic one is included (otherwise the printer will not print in Mirror or Ditto modes).
	- Since the basic one will not be fine for most prints, it is your responsibility to ensure that the nozzles are as perfectly aligned as possible, since only then will the CalPad not even get printed, but you still get perfect results. Mine is almost as perfect as it can be out of the box.
	
## G-codes

This printer uses a lot of non-standard gcode as part of the "xgcode".

* "xgcode 1.0" - Adding this at the top of the file does a couple of things (mostly changes to the way other gcode works):
	- M108 (tool change) actually returns the old tool before bringing out the new tool.
	- M118 (allow configuration of printer and progressbar)
	- M109 (printer mode) is enabled to be used.
* "M107" -> turn print cooling fan off.
* "M118" -> Print configuration (enables the progressbar):
	- X - print size in X (can be left at 0)
	- Y - print size in Y (can be left at 0)
	- Z - print size in Z (can be left at maximum 150)
	- T0 & T1 - which extruders are enabled
	- D1 | D2 - print mode is Mirror (D1) or Ditto / Duplicate (D2)
* "M140" -> set bed temperature, but does not wait.
* "M104" -> set nozzle temp (requires a Tn parameter to affect the right tool).
- "G28" -> home all axis
- "M132" -> load axis offsets from EEPROM, typically called after Homing, with the axis that should be loaded.
- "G161" -> Home selected axis
- "M7" -> wait for heatbed to finish heating, typically with T0 as the primary heatbed.
- "M6" -> wait for hot-end to finish heating, typically with a Tn for the tool that we are waiting for.
- M651 -> set the chamber fan on, typically with S255
- M108 -> perform tool change. Contains a Tn for the new tool.
	+ Note that without "xgcode 1.0" this command does not park the old tool.
- M109 -> used as the multi-tool (when commanding more than 1 tool at the same time):
	+ T1 is a Mirror Tool
	+ T2 is a Duplicate Tool
- G92 -> Reset Extruder distance. The firmware makes use of absolute extruder distances.
- M82 -> forces abslute extruder distances
- G162 -> moves the buildplate to the bottom (typically in end gcode), with the Z parameter.
- M652 -> chamber fan off.
- M18 -> disable stepper motors.

## Post Processor Script

A brief description of what the script does:
* First we have a bunch of regular expressions (Regex) that are defined, mainly to find the information we need; we also define a few script global variables/flags.
* We start building the header and binary block with constants we have.
* We start looping over each line of the G-code that PS gives us:
	- We save the line to memory variable (gcode data) - makes it easy to prepend the header later. Yes, it is not best practise, but the best I can do right now.
	- Attempt to match the line to one of our presets for information we need, if it match, process the information accordingly:
		+ When we start with the thumbnail, all lines are concatenated until we reach the end token, at which point we decode base64 and convert the PNG to BMP
		+ See which extruders are active (do we do left only, right only, dual, mirror or ditto)
		+ Get the printing time, and convert to number of seconds
		+ Based on active nozzles, get filament usage for each.
		+ Based on active nozzles, get nozzle temps
		+ Get layer height and convert to microns
		+ Get shells
		+ Get printing speed
		+ Get heatbed temperature
* We then close the file (as it was read in text mode), and due to not writing anything back, it is now empty.
* We compile the binary header block, using the new details we got.
* If no image was found, generate a black image.
* Append the image to the header block.
* Open the file in Binary mode (needed to actually write binary)
	- write the header, with the image to the file
	- determine if we need to add the "CalPad", if we have to , insert it before "M109" in the gcode data.
	- write the gcode data to the file, encoded as UTF8
* Exit

## Licensing 

Copyright 2022 Jacotheron

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.