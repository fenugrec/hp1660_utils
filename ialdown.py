#! python
# 'port' of IALDOWN.EXE for python (probaby python2)
# https://www.eevblog.com/forum/testgear/hp-logic-analyzer-inverse-assemblers/25/

import sys
import telnetlib
import argparse
import logging

parser = argparse.ArgumentParser(description="Python IALDOWN for HP Logic Analysers")
parser.add_argument('-H', '--host', required=True, help='LA hostname')
parser.add_argument('-p', '--port', type=int, default=5025, help='defaults to 5025')
args = parser.parse_args(sys.argv[1:])

hostname=args.host
port=args.port

# open up the telnet connection first
# otherwise the user doesnt find out if its going to 
# work until after he types all the info in. 
tn = telnetlib.Telnet(hostname, port)

params = {}

params['filename'] = raw_input("Logic Analyzer Filename = ").rstrip()
params['description'] = raw_input("Logic Analyzer File Description\n(must be 32 characters or less) = ").rstrip()
params['rfile'] = raw_input("Relocatable File on the PC = ").rstrip()
# ignored but here for compatibility with scripts
params['comport'] = raw_input("COM Port (Ignored) = ").rstrip()
params['option'] = raw_input(""""Invasm" Field Options:
 A = No "Invasm" Field
 B = "Invasm" Field with no pop-up
 C = "Invasm" Field with pop-up. 2 choices in pop-up.
 D = "Invasm" Field with pop-up. 8 choices in pop-up.
Select the appropriate letter (A, B, C or D)""").rstrip()

if len(params['description']) > 32:
    print "Description too long will be trimmed"

# read the data file
with open(params['rfile'], 'rb') as f:
    buffer = f.read()

# get the params. 
if params['option'].upper() == 'A':
    type_byte = '\xFF'
elif params['option'].upper() == 'B':
    type_byte = '\x00'
elif params['option'].upper() == 'C':
    type_byte = '\x01'
elif params['option'].upper() == 'D':
    type_byte = '\x02'
else:
    raise Exception("Unknown type optiom specified (A,B,C or D)")

# now actually do the transfer. 
tn.write(""":MMEMory:DOWNload '{filename}',INTERNAL0,'{description}',-15614,""".format(**params))
data_size = len(buffer)+1

tn.write("#8%08i" % data_size)
tn.write(type_byte)
tn.write(buffer)
tn.write('\n')
tn.close()
