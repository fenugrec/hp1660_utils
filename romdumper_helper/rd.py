# ROM dump helper
#
# (c) fenugrec 2025
#
# script to aid in dumping ROMs in-situ, while host device is running.
#
# this particular one is for this setup :
#
# fluke 2640 netdaq A1 main pcb
# 	- mc68302
# 	- 28F400B5 (4Mbit, 512kB; 256k*16bit) (0-0x7f ffff)
# its flash is wired as a 16-bit wide bus; address 0 is not relevant for access into flash area.
# 
# The strategy is to load the correct config on the hp1660 manually, then use this script to automate
# 	- setting up trigger
# 	- retrieving data for a 'section'
# 	- preparing next trigger
# 	- reset 2640
# 	- repeat
# 
# In half-channel mode, I can do 8k records at a time.
# 
The 2640 is controlled via the 'netdaq' python library.
Triggering the SelfTest routine should cause the checksum code to run again over the entire ROM

The LA is controlled over telnet with SCPI commands (could also work over rs232)

LA setup requirements:
	- trigger definition must be complete and functional, saving only the ROM fetch data, no opcodes
	- trigger term D will be used to last cycle before the ROM fetch, e.g.


*** misc useful commands
:system:dsp 'generic GUI message'

set sequence level 1 to count 65535 times before proceeding ? untested
	:mach1:str:find0 'anystate|nostate',65535

set recognizer term B
	:mach1:str:term b,'BLK_START',0xF000

retrieve raw data, hope I can find a parser for this shit.
	:syst
	header on
	longform 1
	# select LA module
	:sel 1
	:syst:data?
