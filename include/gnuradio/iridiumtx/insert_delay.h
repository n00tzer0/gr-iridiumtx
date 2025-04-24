/* -*- c++ -*- */
/*
 * Copyright 2025 Piotr Kulpinski.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_IRIDIUMTX_INSERT_DELAY_H
#define INCLUDED_IRIDIUMTX_INSERT_DELAY_H

#include <gnuradio/block.h>
#include <gnuradio/iridiumtx/api.h>

namespace gr {
namespace iridiumtx {

/*!
 * \brief <+description of block+>
 * \ingroup iridiumtx
 *
 */
class IRIDIUMTX_API insert_delay : virtual public gr::block
{
public:
    typedef std::shared_ptr<insert_delay> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of iridiumtx::insert_delay.
     *
     * To avoid accidental use of raw pointers, iridiumtx::insert_delay's
     * constructor is in a private implementation
     * class. iridiumtx::insert_delay::make is the public interface for
     * creating new instances.
     */
    static sptr make(int sample_rate = 1000000,
                     const std::string& length_tag_name = "packet_len",
                     const std::string& offset_tag_name = "time_offset");
};

} // namespace iridiumtx
} // namespace gr

#endif /* INCLUDED_IRIDIUMTX_INSERT_DELAY_H */
