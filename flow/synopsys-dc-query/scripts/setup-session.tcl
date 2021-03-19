#=========================================================================
# setup-session.tcl
#=========================================================================
# Author : Christopher Torng
# Date   : September 30, 2018

# Set up variables for this specific ASIC design kit

source -echo -verbose $dc_adk_tcl

#-------------------------------------------------------------------------
# System
#-------------------------------------------------------------------------

# Multicore support -- watch how many licenses we have!

set_host_options -max_cores $dc_num_cores

# Set up alib caching for faster consecutive runs

set_app_var alib_library_analysis_path $dc_alib_dir

#-------------------------------------------------------------------------
# Message suppression
#-------------------------------------------------------------------------


if { $dc_suppress_msg } {

  foreach m $dc_suppressed_msg {
    suppress_message $m
  }

}

#-------------------------------------------------------------------------
# Libraries
#-------------------------------------------------------------------------

# Set up search path for libraries and design files

set_app_var search_path ". $dc_additional_search_path $search_path"

# Important app vars
#
# - target_library    -- DC maps the design to gates in this library (db)
# - synthetic_library -- DesignWare library (sldb)
# - link_library      -- Libraries for any other design references (e.g.,
#                        SRAMs, hierarchical blocks, macros, IO libs) (db)

set_app_var target_library     $dc_target_libraries
set_app_var synthetic_library  dw_foundation.sldb
set_app_var link_library       [join "
                                 *
                                 $target_library
                                 $dc_extra_link_libraries
                                 $synthetic_library
                               "]



# Reuse existing Milkyway library, but ensure that it is consistent with
# the provided reference Milkyway libraries.

set_mw_lib_reference $milkyway_library \
  -mw_reference_library $dc_milkyway_ref_libraries


open_mw_lib $milkyway_library

# Set up TLU plus (if the files exist)

if { $dc_topographical == True } {
  if {[file exists [which $dc_tluplus_max]]} {
    set_tlu_plus_files -max_tluplus  $dc_tluplus_max \
                       -min_tluplus  $dc_tluplus_min \
                       -tech2itf_map $dc_tluplus_map

    check_tlu_plus_files
  }
}


# Remove new variable info messages from the end of the log file

set_app_var sh_new_variable_message false

# Hook to drop into interactive Design Compiler shell after setup

if {[info exists ::env(DC_EXIT_AFTER_SETUP)]} { set DC_SETUP_DONE true }


