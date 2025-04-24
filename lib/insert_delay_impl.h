/* -*- c++ -*- */
/*
 * Copyright 2025 Piotr Kulpinski.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_IRIDIUMTX_INSERT_DELAY_IMPL_H
#define INCLUDED_IRIDIUMTX_INSERT_DELAY_IMPL_H

#include <gnuradio/iridiumtx/insert_delay.h>

namespace gr {
namespace iridiumtx {

class insert_delay_impl : public insert_delay
{
protected:
    enum state_t {
        STATE_WAIT,
        STATE_PREPAD,
        STATE_COPY
    };
    
private:
    const int d_sample_rate;
    const pmt::pmt_t d_length_tag_key;
    const pmt::pmt_t d_offset_tag_key;
    int d_ncopy;
    int d_limit;
    int d_index;
    uint64_t d_length_tag_offset;
    bool d_finished;
    state_t d_state;
    double d_prev_time_offset;

    void write_padding(gr_complex*& dst, int& nwritten, int nspace);
    void copy_items(gr_complex*& dst, const gr_complex*& src, int& nwritten, int& nread, int nspace);
    void add_length_tag(int offset);
    void propagate_tags(int in_offset, int out_offset, int count, bool skip = true);
    void enter_wait();
    void enter_prepad(int nprepad);
    void enter_copy();
public:
    insert_delay_impl(int sample_rate, const std::string& length_tag_name, const std::string& offset_tag_name);
    ~insert_delay_impl();

    // Where all the action really happens
    void forecast(int noutput_items, gr_vector_int& ninput_items_required);

    int general_work(int noutput_items,
                     gr_vector_int& ninput_items,
                     gr_vector_const_void_star& input_items,
                     gr_vector_void_star& output_items);
};

} // namespace iridiumtx
} // namespace gr

#endif /* INCLUDED_IRIDIUMTX_INSERT_DELAY_IMPL_H */
