#=========================================================================
# reporting.tcl
#=========================================================================
# Final reports
#
# Author : Christopher Torng
# Date   : May 14, 2018
#

report_timing \
  -input_pins -capacitance -transition_time \
  -nets -significant_digits 4 -nosplit      \
  -path_type full_clock -attributes         \
  -nworst 10 -max_paths 30 -delay_type max  \
  > reports/timing_query.rpt

