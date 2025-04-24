/* -*- c++ -*- */
/*
 * Copyright 2025 Piotr Kulpinski.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "add_usrp_tags_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace iridiumtx {


using input_type = gr_complex;
using output_type = gr_complex;
add_usrp_tags::sptr
add_usrp_tags::make(int sps, double current_time, int preamble_len, int padding_len)
{
    return gnuradio::make_block_sptr<add_usrp_tags_impl>(
        sps, current_time, preamble_len, padding_len);
}


/*
 * The private constructor
 */
add_usrp_tags_impl::add_usrp_tags_impl(int sps,
                                   double current_time,
                                   int preamble_len,
                                   int padding_len)
    : gr::sync_block("add_usrp_tags",
                     gr::io_signature::make(
                         1 /* min inputs */, 1 /* max inputs */, sizeof(input_type)),
                     gr::io_signature::make(
                         1 /* min outputs */, 1 /*max outputs */, sizeof(output_type)))
{
    _sps = sps;
    _start_time = current_time + 1;
    _preamble_len = preamble_len;
    _padding_len = padding_len;
    _tx_pkt_len_offset = 0;
}

/*
 * Our virtual destructor.
 */
add_usrp_tags_impl::~add_usrp_tags_impl() {}

int add_usrp_tags_impl::work(int noutput_items,
                           gr_vector_const_void_star& input_items,
                           gr_vector_void_star& output_items)
{
    auto in = static_cast<const input_type*>(input_items[0]);
    auto out = static_cast<output_type*>(output_items[0]);

    int offset_preamble = 0;
    int current_offset = 0;
    std::vector<tag_t> tags;
    get_tags_in_window(tags, 0, 0, noutput_items);
    for (size_t indx = 0; indx < tags.size(); ++indx) {
        const tag_t& tag = tags[indx];

        if (pmt::symbol_to_string(tag.key) == "preamble_len") {
            _preamble_len = pmt::to_long(tag.value);
            current_offset = tag.offset;
        }

        if (pmt::symbol_to_string(tag.key) == "packet_len") {

            int value_len = pmt::to_long(tag.value) - _padding_len;
            _tx_pkt_len_offset = tag.offset;
            offset_preamble = _tx_pkt_len_offset + _padding_len;
            add_item_tag(0,
                         offset_preamble,
                         pmt::intern("tx_pkt_len"),
                         pmt::from_long(value_len),
                         pmt::string_to_symbol(this->name()));
        }

        if (pmt::symbol_to_string(tag.key) == "time_offset") {
            int offset = tag.offset - _preamble_len;
            // printf("add_usrp_tags_impl: tx_time offset = %d\n", offset);
            // printf("add_usrp_tags_impl: tx_pkt_len_offset = %d\n", _tx_pkt_len_offset + _padding_len);
            // double burst_time = _start_time + pmt::to_double(tag.value);

            // pmt::pmt_t burst_time_tuple =
            // pmt::make_tuple(pmt::from_uint64(static_cast<uint64_t>(burst_time)),
            // 												pmt::from_double(burst_time
            // - static_cast<uint64_t>(burst_time))); add_item_tag(0, offset,
            // pmt::intern("tx_time"), burst_time_tuple);

            // For sigmf for now, just offset to where the burst starts
            add_item_tag(0, _tx_pkt_len_offset + _padding_len, pmt::intern("tx_time"), tag.value, pmt::string_to_symbol(this->name()));
        }

        if (pmt::symbol_to_string(tag.key) == "freq_init") {
            int prev_burst_offset = tag.offset - _preamble_len - _padding_len;
            add_item_tag(0, _tx_pkt_len_offset , pmt::intern("tx_freq"), tag.value, pmt::string_to_symbol(this->name()));
        }
    }

    std::memcpy(out, in, noutput_items * sizeof(gr_complex));
    return noutput_items;
}

void add_usrp_tags_impl::set_preamble_len(int preamble_len) {
    _preamble_len = preamble_len;
}

} /* namespace iridiumtx */
} /* namespace gr */
