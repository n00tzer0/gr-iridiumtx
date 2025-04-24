/* -*- c++ -*- */
/*
 * Copyright 2025 Piotr Kulpinski.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_IRIDIUMTX_ADD_USRP_TAGS_IMPL_H
#define INCLUDED_IRIDIUMTX_ADD_USRP_TAGS_IMPL_H

#include <gnuradio/iridiumtx/add_usrp_tags.h>

namespace gr {
namespace iridiumtx {

class add_usrp_tags_impl : public add_usrp_tags
{
private:
    // Nothing to declare in this block.
    int _sps;
    double _start_time;
    int _preamble_len;
    int _padding_len;
    int _tx_pkt_len_offset;

public:
    add_usrp_tags_impl(int sps, double current_time, int preamble_len, int padding_len);
    ~add_usrp_tags_impl();

    // Where all the action really happens
    int work(int noutput_items,
             gr_vector_const_void_star& input_items,
             gr_vector_void_star& output_items);

    void set_preamble_len(int preamble_len);
};

} // namespace iridiumtx
} // namespace gr

#endif /* INCLUDED_IRIDIUMTX_ADD_USRP_TAGS_IMPL_H */
