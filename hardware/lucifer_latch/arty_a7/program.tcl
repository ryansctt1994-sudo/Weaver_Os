# Volatile FPGA programming only, never board flash/eFUSE. Requires explicit serial.
# vivado -mode batch -source program.tcl -tclargs EXACT_TARGET_SERIAL BITSTREAM
if {$argc != 2} { error "Expected exact hardware target serial and bitstream" }
set serial [lindex $argv 0]
set bitfile [file normalize [lindex $argv 1]]
if {![file isfile $bitfile]} { error "Bitstream missing" }
open_hw_manager
connect_hw_server
set matches {}
foreach target [get_hw_targets] {
    if {[file tail $target] eq $serial} { lappend matches $target }
}
if {[llength $matches] != 1} { error "Exact target serial not uniquely found" }
open_hw_target [lindex $matches 0]
set devices [get_hw_devices -filter {PART =~ xc7a35t*}]
if {[llength $devices] != 1} { error "Expected exactly one Artix-7 35T; inspect topology" }
set device [lindex $devices 0]
current_hw_device $device
refresh_hw_device $device
set_property PROGRAM.FILE $bitfile $device
program_hw_devices $device
refresh_hw_device $device
puts "VOLATILE_PROGRAM_OPERATION_COMPLETED; physical interlock qualification NOT_ASSESSED"
close_hw_target
disconnect_hw_server
close_hw_manager
