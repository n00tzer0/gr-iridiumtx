#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Data to iridium bursts into sigmf
# GNU Radio version: 3.10.10.0

from gnuradio import analog
from gnuradio import blocks
import numpy as np
import pmt
from gnuradio import digital
# from gnuradio import filter
from gnuradio import fft
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import gr, pdu, uhd
from gnuradio.filter import pfb
import time

from gnuradio import iridiumtx
import iridium_burst
import re


def convert_to_binary(binary_string):
    return np.array([int(bit) for bit in binary_string])

class iridium_bursts_uhd(gr.top_block):
    total = 0
    current_burst = 0
    def __init__(self, output_file='output', channels=1,debug=False, noise=False):
        gr.top_block.__init__(self, "Data to iridium bursts into sigmf", catch_exceptions=True)

        ##################################################
        # Variables
        ##################################################
        self.uw_downlink = "001100000011000011110011"
        self.uw_uplink =   "110011000011110011111100"
        self.sps = sps = 400
        self.samp_rate = samp_rate = 10e6
        self.center_freq = center_freq = 1622e6
        self.debug = debug
        self.channels = channels
        self.prev_offset = [-1] * self.channels
        self.counter = 0
        ##################################################
        # Blocks
        ##################################################
        # self.throttle_1 = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )

        self.sigmf_sink = blocks.sigmf_sink_minimal(
            item_size=gr.sizeof_gr_complex,
            filename=output_file,
            sample_rate=samp_rate,
            center_freq=center_freq,
            author='',
            description='',
            hw_info='',
            is_complex=True)

        self.bursts = []
        for i in range(self.channels):
            burst = iridium_burst.iridium_burst(sps=sps, samp_rate=samp_rate, center_freq=center_freq, debug=debug)
            self.bursts.append(burst)

        ##################################################
        # Input data
        ##################################################
        
        self.add = blocks.add_vcc(1)
        self.add_noise = blocks.add_vcc(1)
        self.preamble_source = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, 25e3, 1, 0, 0)
        self.postamble_source = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, 25e3, 1, 0, 0)
        self.analog_noise_source_x_0 = analog.noise_source_c(analog.GR_GAUSSIAN, 0.01, 0)


        ##################################################
        # Connections
        ##################################################
        
        # Sigmf sink
        for i, burst in enumerate(self.bursts):
            self.connect((burst, 0), (self.add, i))

        if noise:
            self.connect((self.add, 0), (self.add_noise, 0))
            self.connect((self.analog_noise_source_x_0, 0), (self.add_noise, 1))
            self.connect((self.add_noise, 0), (self.sigmf_sink, 0))
        else: self.connect((self.add, 0), (self.sigmf_sink, 0))
        # self.connect((self.resampler, 0), (self.sigmf_sink, 0))

        # if debug: self.connect((self.add, 0), (self.blocks_tag_debug_end, 0))
    
    def naive_burst_scheduler(self, offset, freq, direction, data, burst_type):
        burst_index = self.counter % self.channels
        if offset - self.prev_offset[burst_index] < 0.02:
            raise ValueError(f"Offset is too close to the previous offset {self.prev_offset[burst_index] - 1}")
        self.prev_offset[burst_index] = offset
        self.bursts[burst_index].send_message(offset, freq, direction, data, burst_type)
        self.counter += 1
        print(f"Sending burst {self.counter} at offset {offset} freq {freq} direction {direction} data {data} burst_type {burst_type}")

    def get_sps(self):
        return self.sps

    def set_sps(self, sps):
        self.sps = sps
        self.set_psf_taps(firdes.root_raised_cosine(self.nfilts/16, self.nfilts, 1, self.eb, (15*self.sps*self.nfilts)))
        self.resampler.set_rate(self.sps)

    def get_nfilts(self):
        return self.nfilts

    def set_nfilts(self, nfilts):
        self.nfilts = nfilts
        self.set_psf_taps(firdes.root_raised_cosine(self.nfilts/16, self.nfilts, 1, self.eb, (15*self.sps*self.nfilts)))
        self.set_taps_per_filt(int(len(self.psf_taps)/self.nfilts))

    def get_eb(self):
        return self.eb

    def set_eb(self, eb):
        self.eb = eb
        self.set_psf_taps(firdes.root_raised_cosine(self.nfilts/16, self.nfilts, 1, self.eb, (15*self.sps*self.nfilts)))

    def get_psf_taps(self):
        return self.psf_taps

    def set_psf_taps(self, psf_taps):
        self.psf_taps = psf_taps
        self.set_taps_per_filt(int(len(self.psf_taps)/self.nfilts))
        self.resampler.set_taps(self.psf_taps)

    def get_taps_per_filt(self):
        return self.taps_per_filt

    def set_taps_per_filt(self, taps_per_filt):
        self.taps_per_filt = taps_per_filt
        self.set_filt_delay(int(1+(self.taps_per_filt-1)//2))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.preamble_source.set_sampling_freq(self.samp_rate)
        # self.throttle_1.set_sample_rate(self.samp_rate)

    def get_pld_const(self):
        return self.pld_const

    def set_pld_const(self, pld_const):
        self.pld_const = pld_const

    def get_filt_delay(self):
        return self.filt_delay

    def set_filt_delay(self, filt_delay):
        self.filt_delay = filt_delay

    def get_center_freq(self):
        return self.center_freq

    def set_center_freq(self, center_freq):
        self.center_freq = center_freq



def bursts_from_file(filename, channels=1):
    bursts = []
    with open(filename, 'r') as infile:
        for line in infile:
            bursts.append(line)
    
    tb = iridium_bursts_uhd(channels=channels, debug=False, noise=False)
    tb.start()

    for burst in bursts:
        burst = burst.split(' ')
        burst_type = burst[0]
        offset = float(burst[1]) + 1
        freq = float(burst[2])
        direction = burst[3]
        data = burst[4].strip()
        tb.naive_burst_scheduler(offset, freq, direction, data, burst_type)

    tb.wait()
    tb.stop()
    tb.wait()

def bursts_from_gr_iridium_file(filename, channels=5, filter_freq=False):
    bursts = []
    send_bursts = [] 

    tb = iridium_bursts_uhd(channels=channels, debug=False, noise=True)
    tb.start()
    print("Starting")

    with open(filename, 'r') as infile:
        for line in infile:
            bursts.append(line)
    print(f"Bursts read: {len(bursts)} ")
    for burst in bursts:
        try:
            p = re.compile(r'(RAW|RWA|NC1): ([^ ]*) (-?[\d.]+) (\d+) (?:N:([+-]?\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)|A:(\w+)) [IL]:(\w+) +(\d+)% ([\d.]+|inf|nan) +(\d+) ([\[\]<> 01]+)(.*)')
            m=p.match(burst)
            if m is None:
                continue     
            offset = float(m.group(3))/1000 + 1 # time in s,  assume that the time burst[1] in seconds does not change 
            freq = float(m.group(4)) 

            # Filter by frequency # registering works at 1626e6 up
            if freq < 1626e6 and filter_freq:
                continue

            data = (re.sub(r"[\[\]<> ]","",m.group(12)))
            send_bursts.append(burst)
            tb.naive_burst_scheduler(offset, freq, "NULL", data, "")
        except Exception as e:
            print(burst)
            print(e)
            continue
    
    with open('send_bursts.bits', 'w') as outfile:
        for burst in send_bursts:
            outfile.write(burst)

    tb.wait()
    tb.stop()
    tb.wait()



def main(top_block_cls=iridium_bursts_uhd, options=None):
    # if gr.enable_realtime_scheduling() != gr.RT_OK:
    #     gr.logger("realtime").warn("Error: failed to enable real-time scheduling.")

    parser = ArgumentParser(description='Data to iridium bursts into sigmf')
    parser.add_argument('--debug', action='store_true', help="Enable debug mode")
    parser.add_argument('--noise', action='store_true', help="Add noise to the signal")
    args = parser.parse_args()

    tb = top_block_cls(1, args.debug, args.noise,)

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()
        sys.exit(0)
    tb.start()
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    bitstream = '0011000000110000111100110001010000010011010100000000001000101011001000010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101'
    dw = '001100000011000011110011'
    payload = convert_to_binary(dw + bitstream)
    offset = 1
    for _ in range(10):
        offset += 0.3
        time.sleep(0.5)
        # tb.set_frequency_shift(10e6)
        freq = np.random.randint(-1e6, 1e6) + tb.center_freq
        tb.naive_burst_scheduler(offset, freq, "NULL", bitstream, "")

    tb.wait()
    tb.stop()
    tb.wait()

if __name__ == '__main__':
    parser = ArgumentParser(description='Data to iridium bursts into sigmf')
    parser.add_argument('filename', type=str, help="Input file containing bursts")
    parser.add_argument('--channels', type=int, default=10, help="Number of channels to use")
    parser.add_argument('--filter_freq', default=False, action='store_true', help="Filter bursts by frequency")
    args = parser.parse_args()

    bursts_from_gr_iridium_file(args.filename, channels=args.channels, filter_freq=args.filter_freq)
