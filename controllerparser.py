import matplotlib.pyplot as plt
import numpy as np
import argparse
import warnings
import os
import re
from math import floor, ceil

parser = argparse.ArgumentParser(description='Process data from DAPHNE Controller Fiber Output')
parser.add_argument('filename', nargs='?',
                    help='the file with data')

args = parser.parse_args()


def signed(val):
	if val > 2048:
		return val - 4096
	return val
class pulse:
	headerlen = 32
	maxlen = 0
	def __init__(self, chno, chlen, choffset, signal):
		self.chno = chno
		self.chlen = chlen
		self.choffset = choffset
		self.signal = [signed(point) for point in signal]

class spill:
	headerlen = 32
	maxlen = 0
	def __init__(self, data, spillno):
		self.header = None
		self.controllerheader = None
		self.ubun = None
		self.spillno = spillno
		self.extract(data)


	def extract(self, data):
		self.pulses = []
		self.data=[filter(None, line.rstrip().split(" ")) for line in data]
		self.header = self.data[0]
		self.controllerheader = self.data[1]
		self.signals = [word for seg in self.data[2:] for word in seg[1:9]]

		self.chinspill = set([])

		self.ubun = self.signals[0:2]
		self.ptr = 2
		#print self.controllerheader[1]
		#print "here " + str(int(self.controllerheader[2],16)-10)
		while self.ptr < int(self.controllerheader[2],16)-10:
			#print self.ptr, self.signals[self.ptr]
			chno = int(self.signals[self.ptr], 16)
			self.chinspill.add(chno)
			#print self.signals[self.ptr]
			chlen = int(self.signals[self.ptr+1], 16)>>12
			choffset = int(self.signals[self.ptr+1], 16)&4095
			#print chno, chlen, choffset
			self.pulses.append(pulse(chno, chlen, choffset, [int(sig, 16) for sig in self.signals[self.ptr+2:(self.ptr+2+chlen)]]))
			self.ptr += (2+chlen)
		self.wdcnt = self.ptr
		print "Spill " + str(self.spillno) + " wdcnt : " + str(self.wdcnt)
	def process(self):
		for ch in self.chinspill:
			waveform = [None]*256
			for pulse in self.pulses:
				if pulse.chno == ch:
					waveform[pulse.choffset:pulse.choffset+1+pulse.chlen] = pulse.signal
			plt.plot(waveform)
			plt.title("Spill: " + str(self.spillno) + " Ch: "+ str(ch))
			plt.show()


def process_file(path, spills):
	f = open(path, "r")
	lines = f.readlines()
	lineptr = 0
	spillno = 0
	print "No. Of Lines: ", len(lines)
	while lineptr < len(lines)-1:
		print "HEADER: ", lines[lineptr]
		linesinspill = int(filter(None, lines[lineptr].rstrip().split(" "))[3],16)
		print "Lines In Spill: " + str(linesinspill)
		
		#print lines[lineptr:lineptr+linesinspill+1]
		spills.append(spill(lines[lineptr:lineptr+linesinspill+1], spillno))
		lineptr += linesinspill+1
		spillno += 1


spills = []
process_file(args.filename, spills)

if spills:
	print "Number of Spills Processed: ", len(spills)
	for i, spill in enumerate(spills):
		print "Spill " + str(i) + " has "+ str(len(spill.pulses)) + " pulses"
		spill.process()


else:
	print "Spills Empty"
