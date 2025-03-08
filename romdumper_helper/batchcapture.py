#! python
# (fenugrec 2025)
#need pyvisa and pyvisa-py (or other backend)
#
# could work over GPIB and RS232 transports as well, hopefully

import sys
import argparse
import pyvisa

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

# from https://github.com/joukos/ghettoib , hopefully not necessary as pyvisa should parse this
def readblock (ifc, timeout = 0.5):
		"""Read definite-length block data from instrument.
		Response is in the form '#<number of digits in block length><block length><data>',
		for example "#800000075<75 bytes of data>", where '#8' means the next 8 digits represent
		the length of the block, ie. 00000075 = 75 bytes.
		"""
		blockpound = self.serialport.read(1) # read block header
		data = ""
		if blockpound == '#':
			numdigits = int(self.serialport.read())
			numdata = int(self.serialport.read(numdigits))
			self.dbg("Receiving block of " + str(numdata) + " bytes", "cyan")
			data = self.serialport.read(numdata)
			self.dbg("Received " + str(len(data)) + " bytes.", "cyan")
		self.serialport.timeout=self.timeout
		if not data:
			self.dbg("Didn't receive anything.", "yellow")
		self.serialport.flushInput() # for eating extra newlines and such (upload_query...)
		return data
