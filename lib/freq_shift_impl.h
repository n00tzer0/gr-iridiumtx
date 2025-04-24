/* -*- c++ -*- */
/*
 * Copyright 2025 Piotr Kulpinski.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_IRIDIUMTX_FREQ_SHIFT_IMPL_H
#define INCLUDED_IRIDIUMTX_FREQ_SHIFT_IMPL_H

#include <gnuradio/iridiumtx/freq_shift.h>
#include <gnuradio/fxpt_nco.h>

namespace gr {
namespace iridiumtx {

class freq_shift_impl : public freq_shift
{
private:
    // Nothing to declare in this block.
    double d_sampling_freq;
    double d_frequency;
    double d_ampl;
    gr::fxpt_nco d_nco;
    int d_length_tag_offset;

public:
    freq_shift_impl(double sampling_freq,
                    double wave_freq,
                    double ampl,
                    float phase);
    ~freq_shift_impl();

    void set_frequency(double frequency);
    void set_phase(float phase);
    void propagate_tags(int in_offset,
                                       int out_offset,
                                       int count,
                                       bool skip);

    // Where all the action really happens
    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items);
};

} // namespace iridiumtx
} // namespace gr

#endif /* INCLUDED_IRIDIUMTX_FREQ_SHIFT_IMPL_H */
