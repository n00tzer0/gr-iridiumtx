/* -*- c++ -*- */
/*
 * Copyright 2025 Piotr Kulpinski.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#ifndef INCLUDED_IRIDIUMTX_FREQ_SHIFT_H
#define INCLUDED_IRIDIUMTX_FREQ_SHIFT_H

#include <gnuradio/iridiumtx/api.h>
#include <gnuradio/sync_block.h>

namespace gr {
namespace iridiumtx {

/*!
 * \brief <+description of block+>
 * \ingroup iridiumtx
 *
 */
class IRIDIUMTX_API freq_shift : virtual public gr::sync_block
{
public:
    typedef std::shared_ptr<freq_shift> sptr;

    /*!
     * \brief Return a shared_ptr to a new instance of iridiumtx::freq_shift.
     *
     * To avoid accidental use of raw pointers, iridiumtx::freq_shift's
     * constructor is in a private implementation
     * class. iridiumtx::freq_shift::make is the public interface for
     * creating new instances.
     */
    static sptr make(double sampling_freq = 1000000.0,
                     double offset = 200000.0,
                     double ampl = 1.0,
                     float phase = 0.0);
};

} // namespace iridiumtx
} // namespace gr

#endif /* INCLUDED_IRIDIUMTX_FREQ_SHIFT_H */
