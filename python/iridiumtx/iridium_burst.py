#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2025 Piotr Kulpinski.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#



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

def convert_to_binary(binary_string):
    return np.array([int(bit) for bit in binary_string])

def differential_encoding(bits):
    symbols = []
    imap = [0, 1, 3, 2]
    
    # Convert bits to symbols
    for x in range(0, len(bits), 2):
        symbols.append(imap.index(int(bits[x]) + int(bits[x + 1]) * 2)) # reversed order

    
    # Apply differential encoding
    for c in range(1, len(symbols)):
        symbols[c] = (symbols[c] + symbols[c - 1]) % 4

    return symbols


class iridium_burst(gr.hier_block2):
    """
    docstring for block iridium_burst
    """
    def __init__(self, id=0, sps=40, samp_rate=1e6, center_freq=1622e6, debug=False):
        gr.hier_block2.__init__(self,
            "iridium_burst",
            gr.io_signature(0, 0, 0),  # Input signature
            gr.io_signature(1, 1, gr.sizeof_gr_complex*1)) # Output signature

        # Define blocks and connect them
        ##################################################
        # Variables
        ##################################################
        self.uw_downlink = "001100000011000011110011"
        self.uw_uplink =   "110011000011110011111100"
        self.sps = sps
        self.nfilts = nfilts = 32
        self.eb = eb = 0.22
        self.psf_taps = psf_taps = firdes.root_raised_cosine(nfilts/16, nfilts,1, eb, (5*sps*nfilts))
        self.taps_per_filt = taps_per_filt = int(len(psf_taps)/nfilts)
        self.samp_rate = samp_rate
        self.pld_const = pld_const = digital.constellation_dqpsk().base()
        # self.pld_const.set_npwr(1)
        # self.pld_const.gen_soft_dec_lut(8)
        self.filt_delay = filt_delay = int(1+(taps_per_filt-1)//2)
        
        self.center_freq = center_freq
        self.debug = debug

        self.offset_outside = 0.5

        ##################################################
        # Blocks
        ##################################################
        # self.freq_shift_mult = blocks.multiply_vcc(1)
        self.resampler = pfb.arb_resampler_ccf(
            sps,
            flt_size=nfilts,
            atten=100)
        self.resampler.declare_sample_delay(self.filt_delay)
        self.filter = pfb.arb_resampler_ccf(
            1,
            taps=psf_taps,
            flt_size=nfilts,
            atten=100)
        
        ### Testing
        # self.msg_strobe_pl = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(len(self._data), self._data)), 500)

        self.pdu_to_tagged_pl = pdu.pdu_to_tagged_stream(gr.types.byte_t, 'packet_len')
        # self.digital_map_bb_1_0 = digital.map_bb([0,1,3,2])
        # self.digital_diff_encoder_bb_0_0 = digital.diff_encoder_bb(4, digital.DIFF_DIFFERENTIAL)
        self.digital_chunks_to_symbols_xx_0_0 = digital.chunks_to_symbols_bc(pld_const.points(), 1)
        self.digital_burst_shaper_xx_0 = digital.burst_shaper_cc(firdes.window(window.WIN_HANN, 16, 0), 100, 100, False, "packet_len")
        self.throttle_1 = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True )
        self.throttle_2 = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True )
        self.throttle_3 = blocks.throttle( gr.sizeof_char*1, samp_rate, True )
        self.throttle_4 = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True )
        self.tagged_mux = blocks.tagged_stream_mux(gr.sizeof_gr_complex*1, "packet_len", 0)
        if debug: self.blocks_tag_debug_end = blocks.tag_debug(gr.sizeof_gr_complex*1, 'End', "")
        if debug: self.blocks_tag_debug_end.set_display(True)

        if debug: self.blocks_tag_debug_delayed = blocks.tag_debug(gr.sizeof_gr_complex*1, 'Shifted', "")
        if debug: self.blocks_tag_debug_delayed.set_display(True)

        if debug: self.blocks_tag_debug_resampled = blocks.tag_debug(gr.sizeof_gr_complex*1, 'Resampled', "")
        if debug: self.blocks_tag_debug_resampled.set_display(True)
        self.preamble_to_tagged = blocks.stream_to_tagged_stream(gr.sizeof_gr_complex, 1, 64, "packet_len") # 16 symbols for basic preamble (32 bits) - 64 symbols for BC, always 64 symbols so the longest possible
        self.postamble_to_tagged = blocks.stream_to_tagged_stream(gr.sizeof_gr_complex, 1, 8, "packet_len") # 8 symbols for postamble just to be sure the last bits of payload are properly modulated after burst shaper
        
        self.blocks_multiply_length = blocks.tagged_stream_multiply_length(gr.sizeof_gr_complex, "tx_pkt_len", sps)
        
        current_time = time.time()

        # self.repack_bits = blocks.repack_bits_bb(1, pld_const.bits_per_symbol(), 'packet_len', False, gr.GR_MSB_FIRST)

        # self.freq_shift_source = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, 200e3, 1, 0, 0)
        
        self.add_usrp_tags = iridiumtx.add_usrp_tags(sps=sps, current_time=current_time+1,preamble_len=64, padding_len=100) # offset by 10 sec in future otherwise I cannot keep up with the burst amount
        self.burst_delay = iridiumtx.insert_delay(int(samp_rate), "tx_pkt_len", "tx_time")

        self.freq_shift = iridiumtx.freq_shift(samp_rate, 1e5, 1.0, 0.0)

        ##################################################
        # Input data
        ##################################################
        
        self.blocks_add_xx_0 = blocks.add_vcc(1)
        self.preamble_source = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, 25e3, 1, 0, 0)
        self.postamble_source = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, 25e3, 1, 0, 0)
        self.analog_noise_source_x_0 = analog.noise_source_c(analog.GR_GAUSSIAN, 0.01, 0)

        self.selectPortName = 'pdus'
        self.message_port_register_hier_in(self.selectPortName)
        
        # self.set_msg_handler(self.selectPortName, self.handle_message)


        ##################################################
        # Connections
        ##################################################
        
        # Preamble
        self.connect((self.preamble_source, 0), (self.throttle_2, 0))
        self.connect((self.throttle_2, 0), (self.preamble_to_tagged, 0))
        self.connect((self.preamble_to_tagged, 0), (self.tagged_mux, 0))
        
        self.connect((self.postamble_source, 0), (self.throttle_4, 0))
        self.connect((self.throttle_4, 0), (self.postamble_to_tagged, 0))
        self.connect((self.postamble_to_tagged, 0), (self.tagged_mux, 2))
        
        # Data (Unique Word + Payload)
        # self.msg_connect(self, 'pdus', self.pdu_to_tagged_pl, 'pdus')
        self.connect((self.pdu_to_tagged_pl, 0), (self.throttle_3, 0))
        # self.connect((self.throttle_3, 0), (self.repack_bits, 0))
        
        # Digital
        # self.connect((self.repack_bits, 0), (self.digital_map_bb_1_0, 0))
        # self.connect((self.digital_map_bb_1_0, 0), (self.digital_diff_encoder_bb_0_0, 0))
        self.connect((self.throttle_3, 0), (self.digital_chunks_to_symbols_xx_0_0, 0))
        self.connect((self.digital_chunks_to_symbols_xx_0_0, 0), (self.tagged_mux, 1))
        self.connect((self.tagged_mux, 0), (self.digital_burst_shaper_xx_0, 0))

        # Add tags
        self.connect((self.digital_burst_shaper_xx_0, 0), (self.add_usrp_tags, 0))

        # Time Domain
        self.connect((self.add_usrp_tags, 0), (self.filter, 0))
        self.connect((self.filter, 0), (self.resampler, 0))
        self.connect((self.resampler, 0), (self.throttle_1, 0))
        self.connect((self.throttle_1, 0), (self.blocks_multiply_length, 0))

        # # Shift frequency
        self.connect((self.blocks_multiply_length, 0), (self.freq_shift, 0))
        
        # Delay
        self.connect((self.freq_shift, 0), (self.burst_delay, 0))

        # Output
        self.connect((self.burst_delay, 0), (self, 0))

    def handle_message(self, msg):
        tags = pmt.car(msg)
        values = pmt.cdr(msg)
        
        time_offset = pmt.to_float(pmt.dict_ref(tags, pmt.intern("time_offset"), pmt.PMT_NIL))
        self.offset_outside += 0.1
        time_offset = self.offset_outside
        freq = pmt.to_long(pmt.dict_ref(tags, pmt.intern("freq"), pmt.PMT_NIL))
        direction = pmt.symbol_to_string(pmt.dict_ref(tags, pmt.intern("direction"), pmt.PMT_NIL))
        data = ''.join([str(bit) for bit in pmt.u8vector_elements(values)])
        type = pmt.symbol_to_string(pmt.dict_ref(tags, pmt.intern("type"), pmt.PMT_NIL))
        # print(f"Received message: {data} at {time_offset} with freq: {freq} and direction: {direction}")
        
        self.send_message(time_offset, freq, direction, data, type)

    def send_message(self, time_offset, freq, direction, data, type="IRA"):
        preamble_len = 16
        if type == "IBC":
            preamble_len = 64
        elif type == "IRA":
            preamble_len = 64

        # # Wait for the frequency to actually change
        # # Only required for the sigmf recordings
        
        symbol_len = int(len(data)/2)
        # # Preamble tweaking (same sync of each burst)
        # self.preamble_source = analog.sig_source_c(self.samp_rate, analog.GR_COS_WAVE, 25e3, 1, 0, 0)
        # self.preamble_source.set_phase(0)
        # self.preamble_to_tagged.set_packet_len(preamble_len)
        # self.add_usrp_tags.set_preamble_len(preamble_len)




        self._direction = direction 
        if self._direction == "DL":
            self.uw_direction = self.uw_downlink
        elif self._direction == "UL":
            self.uw_direction = self.uw_uplink
        elif self._direction == "NULL":
            self.uw_direction = ""
        else:
            raise RuntimeError("Invalid direction. Choose either 'DL' or 'UL'. For downlink and uplink, respectively.")

        # print(convert_to_binary(self.uw_direction + data))
        self._data = differential_encoding(convert_to_binary(self.uw_direction + data)) # data to be transmitted in the burst (binary string)      
        # self._data = differential_encoding(convert_to_binary(data)) # data to be transmitted in the burst (binary string)
        # self._data = self.uw_direction + self._data
        if self.debug: print(f"Sending... len symbols: {symbol_len} at: {freq} data: {''.join(map(str, self._data))} at: {time_offset}")

        port = pmt.intern("pdus")
        tags = pmt.make_dict()
        tags = pmt.dict_add(tags, pmt.intern("freq_init"), pmt.from_long(int(freq)))
        
        tags = pmt.dict_add(tags, pmt.intern("time_offset"), pmt.from_float(time_offset))
        tags = pmt.dict_add(tags, pmt.intern("preamble_len"), pmt.from_long(int(preamble_len)))
        msg = pmt.cons(tags, pmt.init_u8vector(len(self._data), self._data))

        self.pdu_to_tagged_pl.to_basic_block()._post(port, msg)