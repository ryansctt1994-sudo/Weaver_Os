# Run: vivado -mode batch -source build.tcl -tclargs xc7a35ticsg324-1L NEW_OUTPUT_DIR
if {$argc != 2} { error "Expected exact FPGA part and NEW output directory" }
set part [lindex $argv 0]
if {$part != "xc7a35ticsg324-1L"} { error "This constraint set is for Arty A7-35T only; verify model first" }
set out [file normalize [lindex $argv 1]]
if {[file exists $out]} { error "Output already exists; preserve previous build" }
file mkdir $out
set here [file dirname [file normalize [info script]]]
read_verilog [file join $here .. lucifer_latch.v]
read_verilog [file join $here sync_debounce.v]
read_verilog [file join $here lucifer_arty_a7.v]
read_xdc [file join $here arty_a7_35.xdc]
synth_design -top lucifer_arty_a7 -part $part
write_checkpoint [file join $out post_synth.dcp]
report_utilization -file [file join $out utilization.rpt]
opt_design
place_design
phys_opt_design
route_design
report_timing_summary -delay_type min_max -check_timing_verbose -file [file join $out timing.rpt]
report_cdc -details -file [file join $out cdc.rpt]
report_drc -file [file join $out drc.rpt]
write_checkpoint [file join $out routed.dcp]
set setup [get_timing_paths -delay_type max -max_paths 1]
set hold [get_timing_paths -delay_type min -max_paths 1]
if {[llength $setup] == 0 || [llength $hold] == 0} { error "No usable timing paths; qualification incomplete" }
if {[get_property SLACK $setup] < 0 || [get_property SLACK $hold] < 0} { error "Timing closure failed" }
if {[llength [get_drc_violations -filter {SEVERITY == Error}]] > 0} { error "Unresolved error DRCs" }
# CDC and unconstrained-path review still require an explicit operator receipt.
write_bitstream [file join $out lucifer_arty_a7.bit]
puts "BITSTREAM_WRITTEN; physical/CDC acceptance NOT_ASSESSED"
