# Pins verified against Digilent/digilent-xdc Arty-A7-35-Master.xdc.
set_property -dict {PACKAGE_PIN E3 IOSTANDARD LVCMOS33} [get_ports clk]
create_clock -name sys_clk -period 10.000 [get_ports clk]
set_property -dict {PACKAGE_PIN D9 IOSTANDARD LVCMOS33} [get_ports reset_button]
set_property -dict {PACKAGE_PIN G13 IOSTANDARD LVCMOS33 PULLDOWN TRUE} [get_ports trigger_async]
set_property -dict {PACKAGE_PIN B11 IOSTANDARD LVCMOS33 DRIVE 4 SLEW SLOW} [get_ports run_permit]
set_property -dict {PACKAGE_PIN H5 IOSTANDARD LVCMOS33} [get_ports tripped_led]
set_property -dict {PACKAGE_PIN J5 IOSTANDARD LVCMOS33} [get_ports ready_led]
# Only external-to-first-stage paths are asynchronous. Never cut stage1->stage2.
set_false_path -from [get_ports reset_button] -to [get_pins -hier -filter {NAME =~ *sync_meta_reg/D}]
set_false_path -from [get_ports trigger_async] -to [get_pins -hier -filter {NAME =~ *trigger_meta_reg/D}]
# Bench interface budget, to be replaced by measured load-board requirements.
set_output_delay -clock sys_clk -max 2.0 [get_ports {run_permit tripped_led ready_led}]
set_output_delay -clock sys_clk -min 0.0 [get_ports {run_permit tripped_led ready_led}]
