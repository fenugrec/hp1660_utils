#!/bin/python3
# (c) fenugrec 2023

# assumes file already has the HPFSLIF header (0x200 bytes) stripped.
# file should look like repeated blocks of "00 FE <254 bytes of fw data>"
# Format : "XX YY <byte_0> <byte...> <byte_n>", where n = XXYY - 1 (block length is big-endian and refers to actual payload data)



from argparse import ArgumentParser
import mmap

def extract_blocks(fname, out_file):
	with open(fname, "rb") as f:
		mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

	with open(out_file, "wb") as outf:
		pl_len = 0
		f_pos = 0
		last_len = 0
		while f_pos < mm.size():
			mm.seek(f_pos)
			block_len = (mm[f_pos] << 8) + mm[f_pos + 1]

			#possible last-block marker ? it may be part 
			if (block_len == 0xffff):
				remaining_payload = mm.size() - f_pos - 2
				print("lastblock ? {:#x} more bytes; previous block {:#x}".format(remaining_payload, last_len))
				block_len = remaining_payload

			if (block_len != 0xfe):
				print("irregular block @ fileoffs {:#x}: size={:#x}".format(f_pos, block_len))

			outf.write(mm[f_pos+2 : f_pos+2+block_len])
			pl_len += block_len
			f_pos += 2 + block_len
			last_len = block_len

		print("Done. Payload size: {:#x}, filesize {:#x}, last pos {:#x}".format(pl_len, mm.size(), f_pos))
	return

def list_blocks(fname):
	with open(fname, "rb") as f:
		mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

	pl_len = 0
	f_pos = 0
	last_len = 0
	while f_pos < mm.size():
		mm.seek(f_pos)
		block_len = (mm[f_pos] << 8) + mm[f_pos + 1]

		#possible last-block marker ? it may be part 
		if (block_len == 0xffff):
			remaining_payload = mm.size() - f_pos - 2
			print("lastblock ? {:#x} more bytes; previous block {:#x}".format(remaining_payload, last_len))
			block_len = remaining_payload

		if (block_len != 0xfe):
			print("irregular block @ fileoffs {:#x}: +{:#x}".format(f_pos, block_len))
		pl_len += block_len
		f_pos += 2 + block_len
		last_len = block_len

	print("Payload size: {:#x}, filesize {:#x}, last pos {:#x}".format(pl_len, mm.size(), f_pos))

	return

def main():
	parser = ArgumentParser()
	parser.add_argument('fname', help="filename")
	parser.add_argument('-x', help="extract payload to specified output file")
	parser.add_argument('-i', action="store_true", help="only print block info")
	args = parser.parse_args()

	#print(args)

	if args.i:
		list_blocks(args.fname)
		return

	if args.x:
		extract_blocks(args.fname, args.x)

if __name__ == '__main__':
    main()
