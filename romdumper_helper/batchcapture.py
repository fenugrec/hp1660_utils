#!/usr/bin/env python
#
# (c) fenugrec 2025
#
# script to aid in dumping ROMs in-situ, while target is running.
# Requires pyvisa and pyvisa-py (or other backend)
#
'''
This was developed for the HP 1660C but should work on many similar LAs.

The strategy is to load the correct config on the hp1660 manually, then use this script to automate
	- setting up trigger
	- retrieving data for a 'section'
	- preparing next trigger
	- reset target
	- repeat

In half-channel mode, the 1660C can do 8k records per trace, i.e. 16kB of ROM data.

Should work over GPIB and RS232 transports as well, hopefully


****************************************
LA setup requirements:
	- trigger definition must be functional, saving only the ROM fetch data, no opcodes
	- trigger term B is the first address we want to dump
	- trigger term C(or other) is the last opcode fetch before the ROM fetch; 82EBA in the example below
	e.g.
		082EBA  <some opcode fetch here, part of some kind of MOV op>
		000000  <this is the data fetch @ address 0 that we need>
		082EBC  <some later code part of a short loop>
		082EBE
		...
		082EBA
		000002  <reading next location for checksum>

	term B will be set by the script and incremented on every capture
	other terms will not be modified

	The trigger setup must produce a listing that is exclusively the data fetches, e.g.
	line	ADDR	DATA
	0	0000	FFFF
	1	0002	0000
	2	0004	......

****************************************
This script is meant to be tailored to each setup.

Most important functions would be dumploop() which may need modifications,
and target_reset() for triggering an external target reset

Then one would run 'python -i batchcapture.py -H 192.168.x.y' where the -i arg starts an
interpreter after running this script, which provides :
- an active pyvisa connection to the instrument, via handle 'la'
- generic pyvisa queries like la.query("....")
- misc functions like set_darkmode(la)
the console makes it easier to iterate over settings and examine data



****************************************
misc useful commands

:system:dsp 'generic GUI message'

set sequence level 1 to count 65535 times before proceeding ? -> doesnt work as wanted
	:mach1:str:find0 'anystate|nostate',65535
'''

import argparse
import pyvisa
import struct
import itertools


# modify this func if automated reset is possible
def target_reset(instr):
    print("reset target now.")
    return

# retrieve current color settings. color 'number' is from 1 to 7
def get_colors (instr):
    cols=[]
    for cn in range(1,8):
        cols.append(instr.query_ascii_values(f":setc? {cn}", converter='d'))
    return cols

# set colors, must be list of lists e.g. [[1,0,0,85],[2,0,0,55], ....
def set_colors (instr, newcolors):
    for cn in range(1,8):
        ri=cn - 1
        instr.write(f":setc {cn},"
            f"{newcolors[ri][1]},"
            f"{newcolors[ri][2]},"
            f"{newcolors[ri][3]}")

# set all colors to darkest. Save the phosphors
def set_darkmode (instr):
    for cn in range(1,8):
        instr.write(f":setc {cn},0,0,0")

# restore default colors
def reset_colors (instr):
    instr.write(":setc def")

# run capture loop, return list of chunks
# may return more data than desired (does not truncate a full capture)
def dumploop (instr, start_addr, cnt, datawidth=2, timeout=5000):
    ca = start_addr
    end_addr = start_addr + cnt - 1
    chunks = []
    am,dm = get_mask(instr)
    while cnt > 0:
        instr.write(f":mach1:str:term b,'ADDR','#H{ca:x}'")
        instr.write('*cls')
        instr.write(':start')
        target_reset(instr)
        print(f"CAPTURE ({start_addr:#X}-{end_addr:#X}): "
              f"waiting for trigger on addr={ca:#X}")
        req_abort = 0
        while 1:
            try:
                esr = int(instr.query('mesr1?'))
                # bit 0 should be set when done
                if esr & 1: break
                # instr.write(':stop')
                time.sleep(0.2)
            except KeyboardInterrupt:
                req_abort = 1
                break
        rd=get_rawdata(instr)
        chunk=parse_raw(rd,am,dm)
        chunks.append(chunk)
        if req_abort:
            print("cancelling operation, data may be incomplete")
            return chunks
        cl = len(chunk[1])
        ca += cl
        cnt -= cl
    return chunks

# pretty-print a chunklist
def chunk_info (chl):
    for c in chl:
        start=c[0]
        end=start + len(c[1]) - 1
        print(f"{start:x}-{end:x}")

def write_chunks (fname, chunks):
    with open(fname, "wb") as f:
        for chunk in chunks:
            f.write(chunk[1])


# get (address,data) bitmap masks
# hack : set mode to FULL before getting mask, then restore DEEP (half-chanel) mode if required
# In half-channel (full depth) mode, I don't think there's a way to
# identify which pod in a pair is being used. That is, the 'sfor:label?' query will 
# return a bit mask of whatever pods were enabled, but the GUI lets you change that
# (e.g. A8 instead of A7) hence this workaround.
def get_mask(instr):
    origmode=instr.query(':mach1:sfor:mode?')
    instr.write(':mach1:sfor:mode FULL')
    am_str=instr.query(':mach1:sfor:label? "ADDR"').split(',')[3:]
    dm_str=instr.query(':mach1:sfor:label? "DATA"').split(',')[3:]
    am = list(map(int,am_str))
    dm = list(map(int,dm_str))
    instr.write(':mach1:sfor:mode ' + origmode)
# returns something like '"ADDR  ",POSITIVE,0,0,3840,65535'
# where the numeric fields are <clock_bits>,<bitmask>,<bitmask>...
# and each bitmask applies to a pod ; matches left-to-right ordering of Format display
# label string 'ADDR' is case-sensitive !
    podlist=instr.query_ascii_values(':mach1:ass?', 'd')
    #e.g. [8,7,4,3,2,1]. Use these to shift the bitmasks to final 'A8A7A6....A1' pattern
    amask = sum(map(lambda msk, pl: msk << (16 * (pl - 1)), am, podlist))
    dmask = sum(map(lambda msk, pl: msk << (16 * (pl - 1)), dm, podlist))
    return (amask,dmask)


# take a 'row' of data, e.g. 18 bytes on the hp1660, apply mask
# and right-align the bits.
#
def unshift_rawdata(src, mask):
    out = 0
    ob = 0
    while mask:
        if mask & 1:
            if src & 1:
                out |= 1 << ob
            ob += 1
        mask >>= 1
        src >>= 1
    return out

# alternate version of unshift_rawdata, seems to perform better, but a lot less obvious.
# courtesy of 'TeXNickAL' on irc #python.
def unshift_rawdata2(src, mask):
# compute a tuple? of all the weights of the '1' bits of the mask
    wide_wt_it = ( 2**ss   for ss, c in enumerate( f'{mask:b}'[::-1] )  if c == '1' ) 
    # and add all weights where the corresponding bit is set in 'src'
    return  sum(  2**ss   for ss, wide_wt in enumerate(wide_wt_it)   if src&wide_wt )
  



# parse raw data according to dev config, return single contiguous chunk.
# maybe some work needed to make it less device-dependant
# rd: raw data received from :SYST:DATA? query, starting at its "DATA      " header
# _mask: (num_pods * 2)-bytes long mask of bits to extract data, e.g.
#           A8 A7 ..... A1
# data_mask=FF 00 00 00 00  : 16 bits of A8 will end up in DATA
def parse_raw(rd, addr_mask, data_mask, datawidth=2):
    sec_hdr = rd[0:10]
    if sec_hdr != b'DATA      ':
        print("bad section header")
        return
    sec_len = int.from_bytes(rd[12:16])
    #not going to parse the entire Preamble struc here
    podpairs = rd[19] # this should allow to do model-specific parsing
    bpr = 2 + podpairs*4    # 2 bytes for clock + 4 bytes per podpair
    podlist = rd[22:24] #bitmask of pods 'assigned to analyzer 1'
    validrows = rd[100:126]
    max_rows = max(struct.unpack('>10xHHHHHHHH', validrows))   #magic to extract 8x uint16
    acqdata = rd[176:176+(max_rows * bpr)]
    print(f"parsing {bpr}B/row, {max_rows} rows")

    #print(f"am: {addr_mask:X}, dm:{data_mask:X}")
    chunk_start = None
    chunkdata = b''
    last_addr = None
    for rawsample in itertools.batched(acqdata, bpr, strict=1):
        sample=int.from_bytes(rawsample)
        addr=unshift_rawdata(sample, addr_mask)
        data=unshift_rawdata(sample, data_mask)
        if chunk_start is None:
            #first loop only
            chunk_start = addr
            last_addr = addr - datawidth
        if not (addr & 0xfff):
            print(f"@ {addr:X}: {data:X}... ") #chunksize={len(chunkdata):X}")
            #print(f"@ {addr:X}: {data:X} ({sample:X})")
        if addr == (last_addr + datawidth):
            chunkdata = chunkdata + data.to_bytes(datawidth)
        else:
            print(f"discontinuity from {last_addr:#x} to {addr:#x}")
            # cannot ignore this without user intervention; save data and abort
            chunklist=[chunk_start, chunkdata]
            return chunklist
        last_addr = addr
    print(f"last addr: {last_addr:#x}, chunksize={len(chunkdata):X}")
    chunklist=[chunk_start, chunkdata]
    return chunklist


# fetch raw data after a capture
def get_rawdata(instr):
    rawdata = instr.query_binary_values(':syst:data?', datatype='s', container=bytes)
    return rawdata


parser = argparse.ArgumentParser(description="HP 1660 LA-powered ROM dumper helper")
parser.add_argument('-H', '--host', required=True, help='LA hostname')
parser.add_argument('-p', '--port', type=int, default=5025, help='telnet port')
args = parser.parse_args()

hostname=args.host
port=args.port


rm = pyvisa.ResourceManager('@py')
la=rm.open_resource('TCPIP0::' + hostname + '::' + str(port) + '::SOCKET')
# because the 1660 isn't "discoverable" we need to use ::SOCKET mode, which means we need to set terminator
la.read_termination='\n'
print("connected to: " + la.query('*idn?'))

