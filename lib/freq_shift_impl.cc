/* -*- c++ -*- */
/*
 * Copyright 2025 Piotr Kulpinski.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "freq_shift_impl.h"
#include <gnuradio/io_signature.h>
#include <gnuradio/math.h>
#include <volk/volk.h>

namespace gr {
namespace iridiumtx {

using input_type = gr_complex;
using output_type = gr_complex;
freq_shift::sptr freq_shift::make(double sampling_freq,
                                  double wave_freq,
                                  double ampl,
                                  float phase)
{
    return gnuradio::make_block_sptr<freq_shift_impl>(
        sampling_freq, wave_freq, ampl, phase);
}


/*
 * The private constructor
 */
freq_shift_impl::freq_shift_impl(double sampling_freq,
                                 double wave_freq,
                                 double ampl,
                                 float phase)
    : gr::sync_block("freq_shift",
                     gr::io_signature::make(
                         1 /* min inputs */, 1 /* max inputs */, sizeof(input_type)),
                     gr::io_signature::make(
                         1 /* min outputs */, 1 /*max outputs */, sizeof(output_type))),
      d_sampling_freq(sampling_freq),
      d_frequency(wave_freq),
      d_ampl(ampl),
      d_length_tag_offset(0)
{
    this->set_frequency(d_frequency);
    this->set_phase(phase);
    const int alignment_multiple = volk_get_alignment() / sizeof(gr_complex);
    set_alignment(std::max(1, alignment_multiple));
}

/*
 * Our virtual destructor.
 */
freq_shift_impl::~freq_shift_impl() {}

int freq_shift_impl::work(int noutput_items,
                          gr_vector_const_void_star& input_items,
                          gr_vector_void_star& output_items)
{
    gr_complex* in = (gr_complex*)(input_items[0]);
    // auto out = static_cast<output_type*>(output_items[0]);
    gr_complex* out = (gr_complex*)output_items[0];
    gr_complex* cos = (gr_complex*)output_items[0];
    double center_freq = 1622.0e6;

    // Get tags ... 
    std::vector<tag_t> freq_tags;
    get_tags_in_window(freq_tags, 0, 0, noutput_items);

    for (auto& tag : freq_tags) {
        if (tag.key == pmt::intern("tx_freq")) {
        double freq = pmt::to_double(tag.value);
        freq -= center_freq;
        // printf("freq_shift_impl: freq offset = %f\n", freq);
        this->set_frequency(freq);
        }

    }

    d_nco.set_freq(2 * GR_M_PI * this->d_frequency / this->d_sampling_freq);
    d_nco.sincos(cos, noutput_items, d_ampl);

    for (size_t i = 0; i < noutput_items; i++) {
        gr_complex acc = ((const gr_complex*)input_items[0])[i];
        acc = acc * cos[i];
        *out++ = (gr_complex)acc;
    }

    // SIMD multiply idk why it does not work
    // int noi = noutput_items;
    // memcpy(out, input_items[0], noi * sizeof(gr_complex));
    // for (size_t i = 1; i < input_items.size(); i++)
    //     volk_32fc_x2_multiply_32fc(out, in, (const gr_complex*)input_items[i], noi);


    // Do <+signal processing+>
    // printf("mul: %f + %fj\n", out[1].real(), out[1].imag());
    // Tell runtime system how many output items we produced.
    return noutput_items;
}

void freq_shift_impl::set_frequency(double frequency)
{
    d_frequency = frequency;
    d_nco.set_freq(2 * GR_M_PI * this->d_frequency / this->d_sampling_freq);
}

void freq_shift_impl::set_phase(float phase)
{
    gr::thread::scoped_lock l(this->d_setlock);
    d_nco.set_phase(phase);
}

void freq_shift_impl::propagate_tags(int in_offset,
                                       int out_offset,
                                       int count,
                                       bool skip)
{
    uint64_t abs_start = this->nitems_read(0) + in_offset;
    uint64_t abs_end = abs_start + count;
    uint64_t abs_offset = this->nitems_written(0) + out_offset;
    tag_t temp_tag;

    std::vector<tag_t> tags;
    pmt::pmt_t d_length_tag_key = pmt::intern("tx_pkt_len");

    this->get_tags_in_range(tags, 0, abs_start, abs_end);

    for (const auto& tag : tags) {
        if (!pmt::equal(tag.key, d_length_tag_key)) {
            if (skip && (tag.offset == d_length_tag_offset))
                continue;
            temp_tag = tag;
            temp_tag.offset = abs_offset + tag.offset - abs_start;
            this->add_item_tag(0, temp_tag);
        }
    }
}



} /* namespace iridiumtx */
} /* namespace gr */
