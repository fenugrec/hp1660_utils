#! python
#
# fenugrec 2025
#
# slightly different implementation that doesn't depend on 'telnetlib' which is deprecated
# Anyway these LA are really "pseudo-telnet" (per the docs) and sometimes choke on extra
# stuff sent by actual telnet clients like e.g. putty.
#
# Instead this uses pyvisa, with the added benefit of supporting TCP,GPIB,and serial back-ends

import sys
import pyvisa
import argparse

parser = argparse.ArgumentParser(description="Python IALDOWN for HP Logic Analysers")
parser.add_argument('-r', '--res', help='optional, full VISA resource string like TCPIP::x.y.z.w::5025::SOCKET')
parser.add_argument('-H', '--host', help='LA hostname')
parser.add_argument('-p', '--port', type=int, default=5025, help='defaults to 5025')
parser.add_argument('-i', '--ifield', default='a', help='"Invasm" field option [A,B,C,D]')
parser.add_argument('-f', '--file', required=True, type=argparse.FileType('rb'), help='relocatable file to send')
args = parser.parse_args(sys.argv[1:])

resource=args.res
hostname=args.host
port=args.port
rfile=args.file
ifield=args.ifield

# read the data file
buffer = rfile.read()


# may need to change this line if not using pyvisa + 'pyvisa-py' (i.e. NI / other backend)
rm = pyvisa.ResourceManager('@py')
if not resource:
    resource = 'TCPIP0::' + hostname + '::' + str(port) + '::SOCKET'
print(f"Opening VISA resource '{resource}'")
la=rm.open_resource(resource)


# because the 1660 isn't "discoverable" we need to use ::SOCKET mode, which means we need to set terminator
la.read_termination='\n'
print("Connected to: " + la.query('*idn?'))

params = {}

# file will be written to root of storage device; must send explicit 'CD' commands to change dir before
params['filename'] = input("Filename on target LA (truncated to 10 chars):").rstrip()[0:10]
params['description'] = input("Description (truncated to 32 chars):").rstrip()[0:32]

if not ifield:
    ifield = input(""""Invasm" Field Options:
     A = No "Invasm" Field
     B = "Invasm" Field with no pop-up
     C = "Invasm" Field with pop-up. 2 choices in pop-up.
     D = "Invasm" Field with pop-up. 8 choices in pop-up.
    Select the appropriate letter (A, B, C or D)""").rstrip()[0].upper()
params['option'] = ifield


# get the params. 
if params['option'] == 'A':
    type_byte = b'\xFF'
elif params['option'] == 'B':
    type_byte = b'\x00'
elif params['option'] == 'C':
    type_byte = b'\x01'
elif params['option'] == 'D':
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
