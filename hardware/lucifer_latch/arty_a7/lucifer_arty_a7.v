// Bench interlock, 100 MHz Arty A7. No UART or software-accessible clear port.
// SRAM reconfiguration/power cycling clears FPGA state; this is not an OTP fuse.
module lucifer_arty_a7 #(
    parameter integer RESET_STABLE_CYCLES = 500000 // 5 ms at 100 MHz
) (
    input wire clk,
    input wire reset_button,
    input wire trigger_async,
    output wire run_permit,
    output wire tripped_led,
    output wire ready_led
);
    wire reset_pressed, reset_initialized;
    sync_debounce #(.STABLE_CYCLES(RESET_STABLE_CYCLES)) reset_filter (
        .clk(clk), .async_in(reset_button), .stable_out(reset_pressed),
        .initialized(reset_initialized)
    );
    (* ASYNC_REG = "TRUE", SHREG_EXTRACT = "NO" *) reg trigger_meta = 0;
    (* ASYNC_REG = "TRUE", SHREG_EXTRACT = "NO" *) reg trigger_sync = 0;
    reg [31:0] power_on = 0;
    always @(posedge clk) begin
        trigger_meta <= trigger_async;
        trigger_sync <= trigger_meta;
        power_on <= {power_on[30:0], 1'b1};
    end
    wire core_reset_n = power_on[31] && reset_initialized && !reset_pressed;
    wire latched, veto, status;
    lucifer_latch core (
        .clk(clk), .rst_n(core_reset_n), .trigger_in(trigger_sync),
        .threat_level(8'd0), .latch_state(latched), .veto_signal(veto), .status_led(status)
    );
    // External load enable MUST default OFF when this output is absent/unpowered.
    // reset_button is deliberately debounced before it can clear a trip.
    assign run_permit = core_reset_n && !veto;
    assign tripped_led = latched;
    assign ready_led = core_reset_n;
endmodule
