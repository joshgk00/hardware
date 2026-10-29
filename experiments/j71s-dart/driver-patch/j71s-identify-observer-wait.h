/* SPDX-License-Identifier: GPL-2.0-only */
/* Wait at most iterations * 100 ms; caller owns the gate for the whole wait. */
static bool j71s_identify_wait_observer(const bool *gate, unsigned int iterations)
{
 if (!gate)
  return false;
 while (iterations-- && !READ_ONCE(*gate))
  msleep(100);
 return READ_ONCE(*gate);
}
