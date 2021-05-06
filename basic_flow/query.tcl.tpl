
report_timing \
  -through {{ from }} -through {{ to }} \
  -input_pins -capacitance -transition_time \
  -nets -significant_digits 4 -nosplit      \
  -path_type full_clock -attributes         \
  -nworst 10 -max_paths 30 -delay_type max  \
  > ${dc_reports_dir}/timing_query.rpt
