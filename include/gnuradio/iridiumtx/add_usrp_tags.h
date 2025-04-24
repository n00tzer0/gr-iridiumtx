/* -*- c++ -*- */
/*
 * Copyright 2025 Piotr Kulpinski.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_IRIDIUMTX_ADD_USRP_TAGS_H
#define INCLUDED_IRIDIUMTX_ADD_USRP_TAGS_H

#include <gnuradio/iridiumtx/api.h>
#include <gnuradio/sync_block.h>

namespace gr {
namespace iridiumtx {

/*!
 * \brief <+description of block+>
 * \ingroup iridiumtx
 *
 */
class IRIDIUMTX_API add_usrp_tags : virtual public gr::sync_block
{
public:
    typedef std::shared_ptr<add_usrp_tags> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of iridiumtx::add_usrp_tags.
     *
     * To avoid accidental use of raw pointers, iridiumtx::add_usrp_tags's
     * constructor is in a private implementation
     * class. iridiumtx::add_usrp_tags::make is the public interface for
     * creating new instances.
     */
    static sptr make(int sps = 40,
                     double current_time = 1744444,
                     int preamble_len = 16,
                     int padding_len = 100);

    /*!
     * Sets the length of the preamble for offsetting of tags.
     * \param preamble_len preamble length in symbols
     */
    virtual void set_preamble_len(int preamble_len) = 0;
};

} // namespace iridiumtx
} // namespace gr

#endif /* INCLUDED_IRIDIUMTX_ADD_USRP_TAGS_H */
