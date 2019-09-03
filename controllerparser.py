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
		self.header = [int(val, 16) for val in self.data[0]]
		print "Header: ", self.data[0]
		self.controllerheader = [int(val, 16) for val in self.data[1]]
		self.signals = [word for seg in self.data[2:] for word in seg[1:9]]

		self.chinspill = set([])

		self.ubun = int("".join(self.signals[0:2]),16)
		self.ptr = 2
		#print self.controllerheader[1]
		#print "here " + str(int(self.controllerheader[2],16)-10)
		while self.ptr < self.controllerheader[2]-10:
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
	def validate(self):
		# check the header
		print "Packet 1: Header"
		# word 0
		assert(self.header[0] & 0xff00 == 0x1c00)
		assert(self.header[0] & 0x001f == 0b00101)
		tx_seq_no = (self.header[0] & 0xe0) >> 5
		# TXSeqNo is a 3bit packet number
		print "Packet no: ", tx_seq_no
		# word 1
		assert(self.header[1] == 0)
		# word 2
		assert(self.header[2] == 0x8050)
		# word 3
		assert(self.header[3] & 0xf800== 0)
		# TxPkCnt is the count of TX packets in this event, not including the current
		# packet. It should be equal to word_count / 8 (rounded up). Word count is printed
		# below
		tx_pkt_count = self.header[3] & 0x7ff
		print "Packet send count: ", tx_pkt_count
		# words 4 - 6 make the "Timestamp" -- this should be the same as the HeartbeatCount
		tstmp = (self.header[4]) | (self.header[5] << 16) | (self.header[6] << 32)
		print "Timestamp: ", tstmp
		# words 7-8 (will) make the Trigger Timestamp
		trig_tstmp = (self.header[7]) | (self.header[8] << 16)
		print "Trig timestamp: ", trig_tstmp

		# word 9 is a checksum
		print "Checksum: ", self.header[9]

		print "\nPacket 2: Controller self.header"
		# check the controller self.header
		# word 0
		assert(self.controllerheader[0] & 0xff00 == 0x1c00)
		assert(self.controllerheader[0] & 0x001f == 0b00110)
		tx_seq_no = (self.controllerheader[0] & 0xe0) >> 5
		print "Packet no: ", tx_seq_no
		# word 1 contains idreg
		# ID reg is the controller ID -- always 1 for SBND
		assert(self.controllerheader[1] & 0xfff0 == 0x60)
		id_reg = self.controllerheader[1] & 0xf
		print "Controller ID: ", id_reg
		# word 2 contains a word count
		word_count = self.controllerheader[2]
		print "Word count: ", word_count
		# 3-4 contain the active FEB bits
		assert(self.controllerheader[3] & 0xff00 == 0)
		print "Active FEB's 23-16: {0:08b}".format(self.controllerheader[3] & 0xff)
		print "Active FEB's 15-0:  {0:016b}".format(self.controllerheader[4])
		# word 5 is the data request count
		print "Data Request Count: ", self.controllerheader[5]
		# word 6 is something in the Event Buffer
		print "Event buffer thingy: ", self.controllerheader[6]
		# two 0's and then checksum
		assert(self.controllerheader[7] == 0 and self.controllerheader[8] == 0)
		print "Checksum: ", self.controllerheader[9]

	def process(self):
		for ch in self.chinspill:
			waveform = [None]*256
			for pulse in self.pulses:
				if pulse.chno == ch:
					waveform[pulse.choffset:pulse.choffset+1+pulse.chlen] = pulse.signal
			plt.plot(waveform)
			plt.title("UBUN no: " + str(self.ubun) + " Spill: " + str(self.spillno) + " Ch: "+ str(ch))
			plt.show()


def process_file(path, spills):
	f = open(path, "r")
	lines = f.readlines()
	lineptr = 0
	spillno = 0
	print "No. Of Lines: ", len(lines)
	while lineptr < len(lines)-1:
		#print "HEADER: ", lines[lineptr]
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
		spill.validate()


else:
	print "Spills Empty"
