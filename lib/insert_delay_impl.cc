/* -*- c++ -*- */
/*
 * Copyright 2025 Piotr Kulpinski.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include "insert_delay_impl.h"
#include <gnuradio/io_signature.h>

namespace gr {
namespace iridiumtx {

using input_type = gr_complex;
using output_type = gr_complex;
insert_delay::sptr insert_delay::make(int sample_rate,
                                      const std::string& length_tag_name,
                                      const std::string& offset_tag_name)
{
    return gnuradio::make_block_sptr<insert_delay_impl>(
        sample_rate, length_tag_name, offset_tag_name);
}


/*
 * The private constructor
 */
insert_delay_impl::insert_delay_impl(int sample_rate,
                                     const std::string& length_tag_name,
                                     const std::string& offset_tag_name)
    : gr::block("insert_delay",
                gr::io_signature::make(
                    1 /* min inputs */, 1 /* max inputs */, sizeof(input_type)),
                gr::io_signature::make(
                    1 /* min outputs */, 1 /*max outputs */, sizeof(output_type))),
      d_sample_rate(sample_rate),
      d_length_tag_key(pmt::string_to_symbol(length_tag_name)),
      d_offset_tag_key(pmt::string_to_symbol(offset_tag_name))
{
    d_state = STATE_WAIT;
    d_prev_time_offset = 0.0;
    // printf("Insert delay\n");
}

/*
 * Our virtual destructor.
 */
insert_delay_impl::~insert_delay_impl() {}

void insert_delay_impl::forecast(int noutput_items, gr_vector_int& ninput_items_required)
{
    ninput_items_required[0] = noutput_items;
}

int insert_delay_impl::general_work(int noutput_items,
                                    gr_vector_int& ninput_items,
                                    gr_vector_const_void_star& input_items,
                                    gr_vector_void_star& output_items)
{
    auto in = static_cast<const input_type*>(input_items[0]);
    auto out = static_cast<output_type*>(output_items[0]);

    int nwritten = 0;
    int nread = 0;
    int nspace = 0;
    int nskip = 0;
    int curr_tag_index = 0;
    int sample_offset = 0;
    double time_offset = 0.0;
    std::vector<tag_t> tags;
    std::vector<tag_t> offset_tags;

    this->get_tags_in_window(tags, 0, 0, ninput_items[0]);
    auto tags_start = tags.begin();
    const auto tags_end = tags.end();

    while (nwritten < noutput_items) {
        // Only check the nread condition if we are actually reading
        // from the input stream.
            if (nread >= ninput_items[0]) {
                break;
            }
        

        if (d_finished) {
            d_finished = false;
            break;
        }
        nspace = noutput_items - nwritten;

        switch (d_state) {
        case (STATE_WAIT):
            if (tags_start != tags_end) {

                // Testing
                // d_length_tag_offset = tags_start->offset;
                // curr_tag_index = (int)(d_length_tag_offset - this->nitems_read(0));
                // d_ncopy = pmt::to_long(tags_start->value);
                // // tags_start++;
                // nskip = curr_tag_index - nread;
                // add_length_tag(nwritten);
                // // propagate_tags(curr_tag_index, nwritten, 1, false);
                // sample_offset = (int)(0.02 * d_sample_rate);
                // enter_prepad(sample_offset);


                // Time offset tag
                if (tags_start->key == pmt::intern("tx_time")){// d_offset_tag_key){
                    d_length_tag_offset = tags_start->offset;
                    curr_tag_index = (int)(d_length_tag_offset - this->nitems_read(0));
                    time_offset = pmt::to_double(tags_start->value);

                    sample_offset = (int)((time_offset - d_prev_time_offset) * d_sample_rate); // They are still shifted by any padding that is included in flowgraph
                    d_prev_time_offset = time_offset;
                    // printf("sample_offset: %d\n", sample_offset); 
                    // printf("time_offset: %f\n", time_offset);
                    // printf("prev_time_offset: %f\n", d_prev_time_offset);
                    nskip = curr_tag_index - nread; 
                    propagate_tags(curr_tag_index, nwritten, 1, false); 
                    enter_prepad(sample_offset);
                }

                // Length tag
                if (tags_start->key == d_length_tag_key) {
                    // printf("Length tag\n");
                    d_length_tag_offset = tags_start->offset;
                    d_ncopy = pmt::to_long(tags_start->value);
                    nskip = curr_tag_index - nread;
                    add_length_tag(nwritten);
                }


                // Advance to the next tag
                tags_start++;
            } else {
                nskip = ninput_items[0] - nread;
            }
            if (nskip > 0) {
                // this->d_logger->warn("Dropping {:d} samples", nskip);
                nread += nskip;
                in += nskip;
            }
            break;

        case (STATE_PREPAD):
            write_padding(out, nwritten, nspace);
            if (d_index == d_limit)
                enter_copy();
            break;

        case (STATE_COPY):
            copy_items(out, in, nwritten, nread, nspace);
            if (d_index == d_limit)
                enter_wait();
            break;
        default:
            throw std::runtime_error("insert: invalid state");
        }
    }

    this->consume_each(nread);

    return nwritten;
}

void insert_delay_impl::write_padding(gr_complex*& dst, int& nwritten, int nspace)
{
    int nprocess = std::min(d_limit - d_index, nspace);
    std::fill_n(dst, nprocess, 0x00);
    dst += nprocess;
    nwritten += nprocess;
    d_index += nprocess;
}

void insert_delay_impl::copy_items(
    gr_complex*& dst, const gr_complex*& src, int& nwritten, int& nread, int nspace)
{
    int nprocess = std::min(d_limit - d_index, nspace);
    propagate_tags(nread, nwritten, nprocess);
    std::memcpy(dst, src, nprocess * sizeof(gr_complex));
    dst += nprocess;
    nwritten += nprocess;
    src += nprocess;
    nread += nprocess;
    d_index += nprocess;
}


void insert_delay_impl::add_length_tag(int offset)
{
    this->add_item_tag(0,
                       this->nitems_written(0) + offset,
                       d_length_tag_key,
                       pmt::from_long(d_ncopy),
                       pmt::string_to_symbol(this->name()));
}


void insert_delay_impl::propagate_tags(int in_offset,
                                       int out_offset,
                                       int count,
                                       bool skip)
{
    uint64_t abs_start = this->nitems_read(0) + in_offset;
    uint64_t abs_end = abs_start + count;
    uint64_t abs_offset = this->nitems_written(0) + out_offset;
    tag_t temp_tag;

    std::vector<tag_t> tags;

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

void insert_delay_impl::enter_wait()
{
    d_finished = true;
    d_index = 0;
    d_state = STATE_WAIT;
}


void insert_delay_impl::enter_prepad(int nprepad)
{
    d_limit = nprepad;
    d_index = 0;
    d_state = STATE_PREPAD;
}

void insert_delay_impl::enter_copy()
{
    d_limit = d_ncopy;
    d_index = 0;
    d_state = STATE_COPY;
}


} /* namespace iridiumtx */
} /* namespace gr */
