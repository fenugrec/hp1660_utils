#!/usr/bin/env python
#
# fenugrec 2025
#
# File identification magic
#
# .R files, inverse assembler, config, etc... what a mess, not to mention LIF filesystem .


import collections

# Once on the filesystem (i.e. once it has an HFSLIF header), there is a 'file type' field that we can use

filetype=collections.namedtuple('filetype', 'id shortname description')

'''
This table was prepared from
	- data and shortstrings from decompilation of HP 1660 firmware
	- long string from HP 1660C/CS/CP-Series Logic Analyzers - Programmer's Guide (01660-97024)
'''
filetype(-0x3fff, "1650/1_system", '')
filetype(-0x3f00, "16500A_system", '')
filetype(-0x3eff, "16500X config", '')
filetype(-0x3ef3, "?tbd", 'HP 1660AS and HP 1660CS Oscilloscope Configuration')
filetype(-0x3ee0, "1650/1_config", 'HP 1660A/AS and HP 1660C/CS/CP Logic Analyzer Configuration')
filetype(-0x3ede, "?tbd", 'HP 1670A/AS Deep Memory Analyzer Configuration')
filetype(-0x3cff, "autoload_file", 'Autoload File')
filetype(-0x3cfe, "inverse_assem", 'Inverse Assembler')
filetype(-0x3cfd, "16500A_option", '')
filetype(-0x3cfc, "1650/1_option", '')
filetype(-0x3cfb, "  cal_factors", '')
filetype(-0x3cfa, "    text_file", '')
filetype(-0x3cf9, "    166xA_rom", 'HP 1660A/AS ROM Software')
filetype(-0x3cf8, " 166xA_system", 'HP 1660A/AS System Software')
filetype(-0x3cf7, "166xA_analyzr", 'HP 1660A/AS Logic Analyzer Software')
filetype(-0x3cf6, " 166xAS_scope", 'HP 1660AS Oscilloscope Software')
filetype(-0x3cf5, "16[6/7]x_cnfg", 'HP 1660A/AS, HP 1660C/CS/CP, and HP 1670A System External I/O')
filetype(-0x3cf4, "inverse_assem", 'Enhanced Inverse Assembler')
filetype(-0x3cf3, "16500B_system", '')
filetype(-0x3cf2, "16500B_option", '')
filetype(-0x3cf1, " 1664A_system", '')
filetype(-0x3cf0, "1664A_analyzr", '')
filetype(-0x3cef, " 16[6/7]x_rom", 'HP 1660C/CS/CP and HP 1670A ROM Software')
filetype(-0x3cee, " 16[6/7]x_sys", 'HP 1660C/CS/CP and HP 1670A System Software')
filetype(-0x3ced, "166xC_analyzr", 'HP 1660C/CS/CP Logic Analyzer Software')
filetype(-0x3cec, " 166xCS_scope", 'HP 1660CS Oscilloscope Software')
filetype(-0x3ceb, "167x_analyzer", 'HP 1670A/AS Deep Memory Analyzer Software')
filetype(-0x3cea, " 16[6/7]x_opt", 'HP 1660C/CS/CP and HP 1670A Option Software')
filetype(-0x3ce7, "166xCP_pattgn", '')
filetype(-9999, "    directory", '')
filetype(-0x270e, " volume label", '')
filetype(-0x16b5, "          DOS", 'DOS File (from Print to Disk)')
filetype(-2, "LIF_BINARY  ", '')
filetype(1, "LIF_ASCII   ", '')

