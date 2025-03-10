#! python
# (fenugrec 2025)
#need pyvisa and pyvisa-py (or other backend)
#
# could work over GPIB and RS232 transports as well, hopefully

import sys
import argparse
import pyvisa
import struct
import itertools

parser = argparse.ArgumentParser(description="HP 1660 LA-powered ROM dumper helper")
parser.add_argument('-H', '--host', required=True, help='LA hostname')
parser.add_argument('-p', '--port', type=int, default=5025, help='telnet port')
args = parser.parse_args(sys.argv[1:])

hostname=args.host
port=args.port


rm = pyvisa.ResourceManager('@py')
la=rm.open_resource('TCPIP0::' + hostname + '::' + str(port) + '::SOCKET')
# because the 1660 isn't "discoverable" we need to use ::SOCKET mode, which means we need to set terminator
la.read_termination='\n'
print(la.query('*idn?'))


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

# stupid loop reading a chunk of data one line at a time...
# slow !!!
#
# with proper triggering, HP line # would be 0...<2^n-1> e.g. 0-4095 or 0-8191 ;
# n is # of lines to expect = 2^n
# reply to query looks like '4095,"DATA  ","#H0008"'
#
# returns [[chunk0_start,b'...chunkdata..'],[chunk1_start...
def get_chunk (instr, cnt, datawidth=2):
    chunklist=[]
    chunk_start = None
    chunkdata = None
    last_addr = None
    numbytes = 0
    for ln in range(0,cnt):
        addr_text=instr.query(f":mach1:slist:data? {ln},'ADDR'")
        # this parsing can probably be improved; can't believe pyvisa has nothing to help us here?
        # query_ascii_values() almost works but uses the same formatter for all fields ?
        addr=int(addr_text.split(',')[2].strip('"#H'),16)

        data_text=instr.query(f":mach1:slist:data? {ln},'DATA'")
        data=int(data_text.split(',')[2].strip('"#H'),16)
#        print(f"a {addr:#x}, d={data:#x}")
        if chunk_start is None:
            #first loop only
            chunk_start = addr
            chunkdata = (data.to_bytes(datawidth))
            last_addr = addr - 2

        if addr == (last_addr + datawidth):
            chunkdata = chunkdata + (data.to_bytes(datawidth))
        else:
            print(f"discontinuity from {last_addr:#x} to {addr:#x}")
            chunklist.append([chunk_start, chunkdata])
            chunk_start = addr
            chunkdata = (data.to_bytes(datawidth))
        last_addr = addr
        numbytes += datawidth
    print(f"read {numbytes:#x} bytes")
    chunklist.append([chunk_start, chunkdata])
    return chunklist

# extract data
def dumploop (instr, start_addr, cnt, capture_depth, datawidth=2, timeout=5000):
    ca = start_addr
    chunks = []
    while cnt > 0:
        cap = min(cnt, capture_depth)
        instr.write(f":mach1:str:term b,'ADDR','#H{ca:x}'")
        instr.write('*cls')
        instr.write(':start')
        # TODO : implement timeout + polling status + aborting beyond timeout
        while 1:
            esr = int(instr.query('mesr1?'))
            # bit 0 should be set when done
            if esr & 1: break
            # instr.write(':stop')
            time.sleep(0.2)
        chunks.append(get_chunk(instr, cap, datawidth))
        cnt -= cap
    return chunks

def write_chunks (fname, chunks):
    with open(fname, "wb") as f:
        for chunk in chunks:
            f.write(chunk[1])

# WIP, unsatisfactory - 
# get (address,data) bitmap masks
#
# In half-channel (full depth) mode, I don't think there's a way to
# identify which pod in a pair is being used. That is, the 'sfor:label?' query will 
# return a bit mask of whatever pods were enabled, but the GUI lets you change that
# (e.g. A8 instead of A7) and I don't know any query that reflects this.
def get_masks(instr):
    am=instr.query(':mach1:sfor:label? "ADDR"').split(',')[3:]
    dm=instr.query(':mach1:sfor:label? "DATA"').split(',')[3:]
# returns something like '"ADDR  ",POSITIVE,0,0,3840,65535'
# where the numeric fields are <clock_bits>,<bitmask>,<bitmask>...
# and each bitmask applies to a pod ; matches left-to-right ordering of Format display
# label string 'ADDR' is case-sensitive !
    am_ints = list(map(int,am))
    dm_ints = list(map(int,dm))
    # pack values as big endian; a bit of magic to call struct.pack('>HHH...'
    # with the correct number of H's
    amask = struct.pack(f'>{len(am_ints)}H', *am_ints)
    dmask = struct.pack(f'>{len(dm_ints)}H', *dm_ints)
    return ( amask, dmask )


# magic func to iterate over set bits. sauce:
# https://stackoverflow.com/a/8898977
def bits(n):
    while n:
        b = n & (~n+1)
        yield b
        n ^= b

# take a 'row' of data, e.g. 18 bytes on the hp1660, apply mask
# and right-align the bits.
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




# parse raw data according to dev config
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
    acqdata = rd[176:]
    print(f"parsing {bpr}B/row, {max_rows} rows")

    #convert to big integers
    #addr_mask = int.from_bytes(addr_mask)
    #data_mask = int.from_bytes(data_mask)
    #print(f"am: {addr_mask:X}, dm:{data_mask:X}")
    chunk_start = None
    chunklist=[]
    chunkdata = None
    last_addr = None
    for rawsample in itertools.batched(acqdata, bpr):
        sample=int.from_bytes(rawsample)
        addr=unshift_rawdata(sample, addr_mask)
        data=unshift_rawdata(sample, data_mask)
        print(f"@ {addr:X}: {data:X} ({sample:X})")
        if chunk_start is None:
            #first loop only
            chunk_start = addr
            chunkdata = data.to_bytes(datawidth)
            last_addr = addr - datawidth
        if addr == (last_addr + datawidth):
            chunkdata = chunkdata + data.to_bytes(datawidth)
        else:
            print(f"discontinuity from {last_addr:#x} to {addr:#x}")
            chunklist.append([chunk_start, chunkdata])
            chunk_start = addr
            chunkdata = data.to_bytes(datawidth)
        last_addr = addr
    return chunklist


# attempt to get raw data
def get_rawdata(instr):
    # for some reason pyvisa query* functions choke on blockdata. this doesn't help
#    ot=instr.read_termination()
#    instr.read_termination = ''
#    instr.read_termination = ot
    instr.write(':syst:data?')
    marker = instr.read_bytes(1)
    if marker != b'#':
        print(f"no # marker, got {marker}")
        return
    ndig = int(instr.read_bytes(1))
    datalen = int(instr.read_bytes(ndig))
#    print('expecting {datalen:#x} bytes')
    rawdata = instr.read_bytes(datalen)
    #purge trailing '\n'
    crumb = instr.read_bytes(1)
    if crumb != b'\n':
        print(f"didnt get expected trailing LF, got {crumb}")
    return rawdata


