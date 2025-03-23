#!/usr/bin/env python
#
# fenugrec 2025
#
# File identification magic
#
# .R files, inverse assembler, config, etc... what a mess, not to mention LIF filesystem .

# TODO : make some kind of class that has a 'print info' , 'identify' method ?
#

import collections
import struct

# Once on the filesystem (i.e. once it has an HFSLIF header), there is a 'file type' field that we can use

filetype=collections.namedtuple('filetype', 'id shortname description')

'''
This table was prepared from
	- data and shortstrings from decompilation of HP 1660 firmware
	- long string from HP 1660C/CS/CP-Series Logic Analyzers - Programmer's Guide (01660-97024)
'''
filetype_list = [
    filetype(-0x3fff, "1650/1_system", ''),
    filetype(-0x3f00, "16500A_system", ''),
    filetype(-0x3eff, "16500X config", ''),
    filetype(-0x3ef3, "?tbd", 'HP 1660AS and HP 1660CS Oscilloscope Configuration'),
    filetype(-0x3ee0, "1650/1_config", 'HP 1660A/AS and HP 1660C/CS/CP Logic Analyzer Configuration'),
    filetype(-0x3ede, "?tbd", 'HP 1670A/AS Deep Memory Analyzer Configuration'),
    filetype(-0x3cff, "autoload_file", 'Autoload File'),
    filetype(-0x3cfe, "inverse_assem", 'Inverse Assembler'),
    filetype(-0x3cfd, "16500A_option", ''),
    filetype(-0x3cfc, "1650/1_option", ''),
    filetype(-0x3cfb, "  cal_factors", ''),
    filetype(-0x3cfa, "    text_file", ''),
    filetype(-0x3cf9, "    166xA_rom", 'HP 1660A/AS ROM Software'),
    filetype(-0x3cf8, " 166xA_system", 'HP 1660A/AS System Software'),
    filetype(-0x3cf7, "166xA_analyzr", 'HP 1660A/AS Logic Analyzer Software'),
    filetype(-0x3cf6, " 166xAS_scope", 'HP 1660AS Oscilloscope Software'),
    filetype(-0x3cf5, "16[6/7]x_cnfg", 'HP 1660A/AS, HP 1660C/CS/CP, and HP 1670A System External I/O'),
    filetype(-0x3cf4, "inverse_assem", 'Enhanced Inverse Assembler'),
    filetype(-0x3cf3, "16500B_system", ''),
    filetype(-0x3cf2, "16500B_option", ''),
    filetype(-0x3cf1, " 1664A_system", ''),
    filetype(-0x3cf0, "1664A_analyzr", ''),
    filetype(-0x3cef, " 16[6/7]x_rom", 'HP 1660C/CS/CP and HP 1670A ROM Software'),
    filetype(-0x3cee, " 16[6/7]x_sys", 'HP 1660C/CS/CP and HP 1670A System Software'),
    filetype(-0x3ced, "166xC_analyzr", 'HP 1660C/CS/CP Logic Analyzer Software'),
    filetype(-0x3cec, " 166xCS_scope", 'HP 1660CS Oscilloscope Software'),
    filetype(-0x3ceb, "167x_analyzer", 'HP 1670A/AS Deep Memory Analyzer Software'),
    filetype(-0x3cea, " 16[6/7]x_opt", 'HP 1660C/CS/CP and HP 1670A Option Software'),
    filetype(-0x3ce7, "166xCP_pattgn", ''),
    filetype(-9999, "    directory", ''),
    filetype(-0x270e, " volume label", ''),
    filetype(-0x16b5, "          DOS", 'DOS File (from Print to Disk)'),
    filetype(-2, "LIF_BINARY  ", ''),
    filetype(1, "LIF_ASCII   ", ''),
]

# some magic to implement a default filetype
class ftd(dict):
    def __missing__(self, key):
        return filetype(0, "-------", f"(unknown ID {key})")

filetype_tbl = ftd({x.id:x for x in filetype_list})

#and more magic for unknown module IDs
class mod_dict(dict):
    def __missing__(self, key):
        return f"(unknown mod ID {key})"

module_tbl = mod_dict({
    30: 'HP16511', #not 100% sure
    31: 'HP1650B/51B',
    32: 'HP1660C/CS/CP,HP16550A',
    34: 'HP1670D/G',
    40: 'HP16540',
})

'''
Config and invasm files will look like:

struct chunk {
    u16 chunk_length;   //usually 00 FE, so 254 bytes until the next chunk
    u8 chunk_data[chunk_length];
    }
Usually (always?) the last chunk will be padded to the next 256 byte boundary.
I think for the section data (described below) to make sense, it must be 'un-chunked'.


starting after the typical '00 FE', we have:
{
    u32 config_file_len;    //not 100% sure exactly what that includes
    char[32] description?;
}

##############
# config file
##############
In a config file, the char[32] field isfollowed by multiple 'sections'
(this is documented somewhat in the various Programmer Guide docs)

struct section {
    char[11] config;    //e.g. "CONFIG    " with trailing 0
    u8 module_id;
    u32 section_len;
    u8 section_data[section_len?];
}

##############
# invasm file
##############
After the char[32] field, we have one single 0x00 byte, followed by the magic 82 03.
'''

#######################################
#   identify specific types
#######################################
# These functions are passed data without HFS/LIF header
# Semantics are all weird: 
# - HFSLIF is a type of container, usually contains an invasm ?
# - 'is_chunked' only refers to 256-byte splits (file itself could be Config or invasm)
# - is_config / is_reloc are actually file 'types'

# a bit muddy; it seems like both invasm and config files can start with 00 FE
# which is simply a chunk size marker. So this just indicates if
# a file needs to be unchunked first.
def is_chunked(d: bytes):
    return d[0:2] == b'\x00\xFE'

def is_reloc(d: bytes):
    if is_chunked(d):
        return d[0x27:0x29] == b'\x82\x03'
    return d[0:2] == b'\x82\x03'

def is_hfs(d: bytes):
    return d[0:8] == b'\x80\x00HFSLIF'

def is_config(d: bytes):
    if is_chunked(d):
        return d[0x26:0x26+6] == b'CONFIG'
    return d[0x24:0x24+6] == b'CONFIG'


def is_s(d: bytes):
    return d[0:5] == b'"IAL"'


#######################################
#   parse and collect info
#######################################

# reconstruct file with the '00 FE <254 bytes of stuff>' chunking format. Discards trailing data
def unchunk(d:bytes):
    cleaned=b''
    while len(d) > 0:
        n = struct.unpack('>H',d[0:2])[0] 
#        if n == 0x1ff or n == 0x7ff:
            #let's assume that's how a last-chunk is signaled, always...
#            return cleaned
        if n > len(d):
            print(f"problem unchunking after {len(cleaned):#x}: chunk_len wants {n:#x}")
            return
        cleaned += d[2:n+2]
        d=d[n+2:]
        if n != 0xfe:
            break
    return cleaned

# data either starts with 82 03 magic, or is chunked and has a description field before the 8203
def parse_reloc(d: bytes):
    if is_chunked(d):
        descr=d[0x6:0x26].decode()
        print(f"chunked invasm, '{descr}'")
        d=unchunk(d)[0x25:]
    # here, d[0:2] has magic 82 03
    objname = d[3:0x12].decode().rstrip() # made up a name for this. Seems to be uppercase'd .S filename
    # oops, there's some variable-length fields here before the following. TODO
    # ia_marker = d[0x45:0x45+0x10].decode() # 'IAILXXXXXASSEMB'
    print(f"objname: {objname}")
    return


# expects data to start with '00 FE' chunk size marker
def parse_config(d: bytes):
    d2 = unchunk(d)
    config_len = struct.unpack('>I', d2[0:4])[0]
    descr = d2[4:0x24].decode().rstrip()
    print(f"config: '{descr}'")
    i = 0x24
    while (i + 17) < len(d2):
        sec_name=d2[i:i+10].decode().rstrip()
        mod_id=d2[i+11]
        sec_len=struct.unpack('>I', d2[i+12:i+16])[0]
        module=module_tbl[mod_id]
        print(f"section '{sec_name}', model {module}, section len {sec_len:#x}")
        if (sec_len == 0): break
        i += sec_len + 16 # skip our header and section
    return


# expects data to start with '80 00 HFSLIF' magic
def parse_hfs(d: bytes):
    if len(d) < 512:
        print("unlikely file, too small")
    #seems like the first 0x200 bytes are a fairly hardcoded struct
    filename=d[0x100:0x10a]
    file_id = struct.unpack('>h', d[0x10a:0x10c])[0]
    start_offset = struct.unpack('>I', d[0x10c:0x110])[0]*0x100
    if (start_offset != 0x200):
        print(f"unexpected header size {start_offset:#x}")
        return
    entry_len = struct.unpack('>I', d[0x110:0x114])[0]*0x100
    expect_len = start_offset + entry_len
    if (len(d) != expect_len):
        print(f"unexpected file size {len(d):#X} vs {expect_len:#X}")
        return
    shortname = filetype_tbl[file_id].shortname
    print(f"type {file_id}:{shortname}")
    # now, whatever it contains, must be also identified
    identify(d[0x200:])
    return


def identify (filedata: bytes):
    if len(filedata) < 256:
        print("unlikely file, too small")
        return

    if is_reloc(filedata):
        print("Relocatable file")
        return parse_reloc(filedata)
    elif is_hfs(filedata):
        print("HFSLIF container;")
        return parse_hfs(filedata)
    elif is_config(filedata):
        return parse_config(filedata)
    elif is_s(filedata):
        print(".S assembly")
        return
    else:
        print("Unrecognized format !")
    return

import sys
def main():
    print(f"Identifying: '{sys.argv[1]}'")
    with open(sys.argv[1], "rb") as f:
        d=f.read()
        identify(d)

if __name__ == '__main__':
        main()
