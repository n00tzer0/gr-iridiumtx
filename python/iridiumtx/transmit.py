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

class iridium_bursts_uhd(gr.top_block):

    def __init__(self, debug=False, tag_filter=False):
        gr.top_block.__init__(self, "Data to iridium bursts into sigmf", catch_exceptions=True)

        ##################################################
        # Variables
        ##################################################
        self.uw_downlink = "001100000011000011110011"
        self.uw_uplink =   "110011000011110011111100"
        self.sps = sps = 4
        self.nfilts = nfilts = 32
        self.eb = eb = 0.22
        self.psf_taps = psf_taps = firdes.root_raised_cosine(nfilts/16, nfilts,1, eb, (5*sps*nfilts))
        self.taps_per_filt = taps_per_filt = int(len(psf_taps)/nfilts)
        self.samp_rate = samp_rate = 1e5
        self.pld_const = pld_const = digital.constellation_dqpsk().base()
        self.pld_const.set_npwr(1)
        self.pld_const.gen_soft_dec_lut(8)
        self.filt_delay = filt_delay = int(1+(taps_per_filt-1)//2)
        
        self.center_freq = center_freq = 1626e6
        self.debug = debug
        #symbol_len = int(len(self._data)/2)
        #if self.debug: print(f"Sending... len symbols: {symbol_len} data: {self._data}")
        #if self.debug: print(f"Filter delay: {filt_delay}")
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
        # self.filter.declare_sample_delay(self.filt_delay)


        # self.block_delay = blocks.delay(gr.sizeof_gr_complex*1, 5000) # Delay for USRP after resampling
        
        ### Testing
        # self.msg_strobe_pl = blocks.message_strobe(pmt.cons(pmt.make_dict(), pmt.init_u8vector(len(self._data), self._data)), 500)

        self.pdu_to_tagged_pl = pdu.pdu_to_tagged_stream(gr.types.byte_t, 'packet_len')
        self.digital_map_bb_1_0 = digital.map_bb([0,1,3,2])
        self.digital_diff_encoder_bb_0_0 = digital.diff_encoder_bb(4, digital.DIFF_DIFFERENTIAL)
        self.digital_chunks_to_symbols_xx_0_0 = digital.chunks_to_symbols_bc(pld_const.points(), 1)
        self.digital_burst_shaper_xx_0 = digital.burst_shaper_cc(firdes.window(window.WIN_HANN, 16, 0), 100, 100, False, "packet_len")
        self.blocks_throttle2_0 = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.mux_with_preamble = blocks.tagged_stream_mux(gr.sizeof_gr_complex*1, "packet_len", 0)
        if debug: self.blocks_tag_debug_0 = blocks.tag_debug(gr.sizeof_gr_complex*1, '', "")
        if debug: self.blocks_tag_debug_0.set_display(True)
        self.preamble_to_tagged = blocks.stream_to_tagged_stream(gr.sizeof_gr_complex, 1, 16, "packet_len") # 16 symbols for basic preamble (32 bits) - 64 symbols for BC
        
        if tag_filter: self.tag_filter_freq = blocks.tag_gate(gr.sizeof_gr_complex * 1, False)
        if tag_filter: self.tag_filter_freq.set_single_key("freq")
        if tag_filter: self.tag_filter_packet_len = blocks.tag_gate(gr.sizeof_gr_complex * 1, False)
        if tag_filter: self.tag_filter_packet_len.set_single_key("packet_len")
        if tag_filter: self.tag_filter_time_offset = blocks.tag_gate(gr.sizeof_gr_complex * 1, False)
        if tag_filter: self.tag_filter_time_offset.set_single_key("time_offset")

        self.blocks_multiply_length = blocks.tagged_stream_multiply_length(gr.sizeof_gr_complex, "tx_pkt_len", sps)

        self.usrp_sink = uhd.usrp_sink(
            ",".join(("", '')),
            uhd.stream_args(
                cpu_format="fc32",
                args='num_send_frames=100,send_frame_size=8192',
                channels=list(range(0,1)),
            ),
            "tx_pkt_len",
        )
        self.usrp_sink.set_samp_rate(samp_rate)
        current_time = time.time()
        self.usrp_sink.set_time_now(uhd.time_spec(current_time), uhd.ALL_MBOARDS)

        self.usrp_sink.set_center_freq(center_freq, 0)
        self.usrp_sink.set_antenna("TX/RX", 0)
        self.usrp_sink.set_bandwidth(0, 0)
        self.usrp_sink.set_gain(40, 0)

        # self.blocks_sigmf_sink_minimal_0 = blocks.sigmf_sink_minimal(
        #     item_size=gr.sizeof_gr_complex,
        #     filename='test',
        #     sample_rate=samp_rate,
        #     center_freq=center_freq,
        #     author='',
        #     description='',
        #     hw_info='',
        #     is_complex=True)

        self.repack_bits = blocks.repack_bits_bb(1, pld_const.bits_per_symbol(), 'packet_len', False, gr.GR_MSB_FIRST)

        # self.freq_shift_source = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, 0, 1, 0, 0)
        
        self.add_usrp_tags = iridiumtx.add_usrp_tags(sps=sps, current_time=current_time+1,preamble_len=16, padding_len=100) # offset by 10 sec in future otherwise I cannot keep up with the burst amount
        ##################################################
        # Input data
        ##################################################
        
        self.blocks_add_xx_0 = blocks.add_vcc(1)
        self.preamble_source = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, 25e3, 1, 0, 0)
        self.analog_noise_source_x_0 = analog.noise_source_c(analog.GR_GAUSSIAN, 0.01, 0)


        ##################################################
        # Connections
        ##################################################
        
        # Preamble
        self.connect((self.preamble_source, 0), (self.preamble_to_tagged, 0))
        self.connect((self.preamble_to_tagged, 0), (self.mux_with_preamble, 0))
        
        
        # Testing
        # self.msg_connect((self.msg_strobe_pl, 'strobe'), (self.pdu_to_tagged_pl, 'pdus'))

        # Data (Unique Word + Payload)
        self.connect((self.pdu_to_tagged_pl, 0), (self.repack_bits, 0))
        
        
        # Digital
        self.connect((self.repack_bits, 0), (self.digital_map_bb_1_0, 0))
        self.connect((self.digital_map_bb_1_0, 0), (self.digital_diff_encoder_bb_0_0, 0))
        self.connect((self.digital_diff_encoder_bb_0_0, 0), (self.digital_chunks_to_symbols_xx_0_0, 0))
        self.connect((self.digital_chunks_to_symbols_xx_0_0, 0), (self.mux_with_preamble, 1))
        self.connect((self.mux_with_preamble, 0), (self.digital_burst_shaper_xx_0, 0))

        # Add tags
        self.connect((self.digital_burst_shaper_xx_0, 0), (self.add_usrp_tags, 0))
        if tag_filter: self.connect((self.add_usrp_tags, 0), (self.tag_filter_freq, 0))
        self.connect((self.add_usrp_tags, 0), (self.filter, 0))

        # Filter unwanted tags
        if tag_filter: self.connect((self.tag_filter_freq, 0), (self.tag_filter_packet_len, 0))
        if tag_filter: self.connect((self.tag_filter_packet_len, 0), (self.tag_filter_time_offset, 0))

        
        # Time Domain
        if tag_filter: self.connect((self.tag_filter_time_offset, 0), (self.filter, 0))
        self.connect((self.filter, 0), (self.resampler, 0))

        # Delay for USRP
        # self.connect((self.resampler, 0), (self.block_delay, 0))


        # self.connect((self.resampler, 0), (self.add_usrp_tags, 0))

        self.connect((self.resampler, 0), (self.blocks_multiply_length, 0))


        # # Shift frequency
        # self.connect((self.blocks_multiply_length, 0), (self.freq_shift_mult, 0))
        # self.connect((self.freq_shift_source, 0), (self.freq_shift_mult, 1))

        
        # USRP Sink
        self.connect((self.blocks_multiply_length, 0), (self.usrp_sink, 0))
        # self.connect((self.resampler, 0), (self.blocks_sigmf_sink_minimal_0, 0))

        if debug: self.connect((self.blocks_multiply_length, 0), (self.blocks_tag_debug_0, 0))

    def set_frequency_shift(self, freq):
        self.freq_shift_source.set_frequency(int(freq)) # = analog.sig_source_c(self.samp_rate, analog.GR_COS_WAVE, int(freq), 1, 0, 0)

# Preamble len in bits (symbols * 2)
    def send_message(self, time_offset, freq, direction, data, type="IRA"):
        # preamble_len = 16
        # if type == "IBC":
        #     preamble_len = 64
        # elif type == "IRA":
        #     preamble_len = 16
        
        # # Wait for the frequency to actually change
        # # Only required for the sigmf recordings
        
        symbol_len = int(len(data)/2)
        # # Preamble tweaking (same sync of each burst)
        # self.preamble_source = analog.sig_source_c(self.samp_rate, analog.GR_COS_WAVE, 25e3, 1, 0, 0)
        # self.preamble_to_tagged.set_packet_len(preamble_len)

        # time.sleep(0.2)
        

        if self.debug: print(f"Sending... len symbols: {symbol_len} at: {freq} data: {data}")

        self._direction = direction 
        if self._direction == "DL":
            self.uw_direction = self.uw_downlink
        elif self._direction == "UL":
            self.uw_direction = self.uw_uplink
        else:
            raise RuntimeError("Invalid direction. Choose either 'DL' or 'UL'. For downlink and uplink, respectively.")

        self._data = convert_to_binary(self.uw_direction + data) # data to be transmitted in the burst (binary string)        

        port = pmt.intern("pdus")
        tags = pmt.make_dict()
        tags = pmt.dict_add(tags, pmt.intern("freq"), pmt.from_long(int(freq)))
        
        tags = pmt.dict_add(tags, pmt.intern("time_offset"), pmt.from_float(time_offset))
        msg = pmt.cons(tags, pmt.init_u8vector(len(self._data), self._data))

        self.pdu_to_tagged_pl.to_basic_block()._post(port, msg)

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
        self.blocks_throttle2_0.set_sample_rate(self.samp_rate)

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

def bursts_from_file(filename):
    bursts = []
    with open(filename, 'r') as infile:
        for line in infile:
            bursts.append(line)
    
    tb = iridium_bursts_uhd(debug=True, tag_filter=False)
    tb.start()

    for burst in bursts:
        burst = burst.split(' ')
        burst_type = burst[0]
        offset = float(burst[1])
        freq = float(burst[2])
        direction = burst[3]
        data = burst[4].strip()
        tb.send_message(offset, freq, direction, data, burst_type)

    tb.wait()
    tb.stop()
    tb.wait()


def main(top_block_cls=iridium_bursts_uhd, options=None):
    # if gr.enable_realtime_scheduling() != gr.RT_OK:
    #     gr.logger("realtime").warn("Error: failed to enable real-time scheduling.")

    parser = ArgumentParser(description='Data to iridium bursts into sigmf')
    parser.add_argument('--debug', action='store_true', help="Enable debug mode")
    args = parser.parse_args()

    tb = top_block_cls(args.debug)

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()
        sys.exit(0)
    tb.start()
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    bitstream = '0000000010111101110001110110010011101100011001111111101111110011101100110110001100101011010001011101100000001101011101110100000100000010000100010110010001011001001010010101000101010001101000011100111000010001011001000101100100101001010100010101000110100001110011'
    dw = '001100000011000011110011'
    payload = convert_to_binary(dw + bitstream)
    offset = 1
    for _ in range(1000):
        offset += 0.2
        # tb.set_frequency_shift(10e6)
        freq = np.random.randint(-1e6, 1e6) + tb.center_freq
        tb.send_message(offset, freq, "DL", payload, "IBC")


    tb.wait()
    tb.stop()
    tb.wait()

if __name__ == '__main__':
    # main()
    bursts_from_file("sample_data/register-short.spoof")
