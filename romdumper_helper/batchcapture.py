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
        print(f"CAPTURE ({start_addr:#X}-{end_addr:#X}): "
              f"waiting for trigger on addr={ca:#X}; reset target now")
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


