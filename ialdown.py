#! python
# 'port' of IALDOWN.EXE for python2 by user sleary78
# https://www.eevblog.com/forum/testgear/hp-logic-analyzer-inverse-assemblers/25/
# updated to work on python3, but you need special 'telnetlib-313-and-up' compatibility package
# note, the HP LA is not really proper telnet servers

import sys
import telnetlib
import argparse
import logging

parser = argparse.ArgumentParser(description="Python IALDOWN for HP Logic Analysers")
parser.add_argument('-H', '--host', required=True, help='LA hostname')
parser.add_argument('-p', '--port', type=int, default=5025, help='defaults to 5025')
parser.add_argument('-r', '--rfile', required=True, type=argparse.FileType('rb'), help='relocatable file to send')
args = parser.parse_args(sys.argv[1:])

hostname=args.host
port=args.port
rfile=args.rfile

# read the data file
buffer = rfile.read()


# open up the telnet connection first
# otherwise the user doesnt find out if its going to 
# work until after he types all the info in. 
tn = telnetlib.Telnet(hostname, port)

params = {}

# file will be written to root of storage device; must send explicit 'CD' commands to change dir before
params['filename'] = input("Filename on target LA (truncated to 10 chars):").rstrip()[0:10]
params['description'] = input("Logic Analyzer File Description\n(truncated to 32 chars):").rstrip()[0:32]
params['option'] = input(""""Invasm" Field Options:
 A = No "Invasm" Field
 B = "Invasm" Field with no pop-up
 C = "Invasm" Field with pop-up. 2 choices in pop-up.
 D = "Invasm" Field with pop-up. 8 choices in pop-up.
Select the appropriate letter (A, B, C or D)""").rstrip()


# get the params. 
if params['option'].upper() == 'A':
    type_byte = b'\xFF'
elif params['option'].upper() == 'B':
    type_byte = b'\x00'
elif params['option'].upper() == 'C':
    type_byte = b'\x01'
elif params['option'].upper() == 'D':
    type_byte = b'\x02'
else:
    raise Exception("Unknown type optiom specified (A,B,C or D)")

# now actually do the transfer. 
tn.write(""":MMEMory:DOWNload '{filename}',INTERNAL0,'{description}',-15614,""".format(**params).encode('ascii'))
data_size = len(buffer)+1

tn.write("#8%08i".encode('ascii') % data_size)
tn.write(type_byte)
tn.write(buffer)
tn.write(b'\n')
tn.close()
