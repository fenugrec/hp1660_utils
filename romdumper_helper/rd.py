# ROM dump helper
#
# (c) fenugrec 2025
#
# script to aid in dumping ROMs in-situ, while host device is running.
#
# this particular script is for the following setup :
#
# - HP 1660C
# - fluke 2640 netdaq A1 main pcb
# 	- mc68302
# 	- 28F400B5 (4Mbit, 512kB; 256k*16bit) (0-0x7f ffff)
# its flash is wired as a 16-bit wide bus; address 0 is not relevant for access into flash area.
# 
'''
The strategy is to load the correct config on the hp1660 manually, then use this script to automate
	- setting up trigger
	- retrieving data for a 'section'
	- preparing next trigger
	- reset 2640
	- repeat

In half-channel mode, the 1660C can do 8k records per trace, i.e. 16kB of ROM data.

The 2640 is controlled via the 'netdaq' python library.
Triggering the SelfTest routine should cause the checksum code to run again over the entire ROM

The LA is controlled over telnet with SCPI commands (could also work over rs232)

LA setup requirements:
	- trigger definition must be complete and functional, saving only the ROM fetch data, no opcodes
	- trigger term B is the first address we want to dump
	- trigger term C is the last opcode fetch before the ROM fetch; 82EBA in the example below
	e.g.
		082EBA  <some opcode fetch here, part of some kind of MOV op>
		000000  <this is the data fetch @ address 0 that we need>
		082EBC  <some later code part of a short loop>
		082EBE
		...
		082EBA
		000002  <reading next location for checksum>
	
	term B will be set by the script and incremented on every capture
	term C will not be modified
	The trigger setup must produce a listing that is exclusively the data fetches, e.g.
	line	ADDR	DATA
	0	0000	FFFF
	1	0002	0000
	2	0004	......


*** misc useful commands
:system:dsp 'generic GUI message'

set sequence level 1 to count 65535 times before proceeding ? -> doesnt work as wanted
	:mach1:str:find0 'anystate|nostate',65535

set recognizer term B
	:mach1:str:term b,'BLK_START','#H08f00'

retrieve raw data, hope I can find a parser for this shit.
	:syst
	header off
#	longform 1
	# select LA module
	:sel 1
	:syst:data?
response:
#800204976DATA <binary garbage>

'''

# this requries symlink or git submodule i.e. "netdaq/lib/netdaq.py"
import netdaq.lib.netdaq as ndq
import time

# doesn't really work, ROM check doesn't seem to be triggered at all
async def reset_target_soft():
	ndq_ip="192.168.3.40"
	targ=ndq.NetDAQ(ip=ndq_ip, port=4369)

	await targ.connect()

	try:
		await targ.ping()
		print("connected to:", await targ.get_version_info())
		print("sending SelfTest request")
		await targ.selftest()

	finally:
		print("Disconnecting from netdaq")
		await targ.close()

def get_rawdata():

run(main())
