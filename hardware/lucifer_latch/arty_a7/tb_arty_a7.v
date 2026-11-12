`timescale 1ns/1ps
module tb_arty_a7;
    reg clk = 0, reset_button = 0, trigger_async = 0;
    wire run_permit, tripped_led, ready_led;
    integer checks = 0;
    lucifer_arty_a7 #(.RESET_STABLE_CYCLES(8)) dut (
        .clk(clk), .reset_button(reset_button), .trigger_async(trigger_async),
        .run_permit(run_permit), .tripped_led(tripped_led), .ready_led(ready_led)
    );
    always #5 clk = ~clk;
    task tick(input integer n);
        integer i;
        begin for (i=0;i<n;i=i+1) begin @(posedge clk); #1; end end
    endtask
    task check(input condition, input [511:0] description);
        begin
            if (!condition) $fatal(1,"FAIL: %0s",description);
            checks = checks+1;
            $display("PASS: %0s",description);
        end
    endtask
    initial begin
        tick(2); check(run_permit===0,"startup holds permit OFF");
        tick(40); check(run_permit===1 && ready_led===1,"startup exits into armed bench state");
        // Asynchronous phase; minimum guaranteed capture pulse is >=3 clock periods.
        #2; trigger_async=1; tick(4); trigger_async=0;
        tick(100); check(run_permit===1,"original 68000-cycle deliberation floor retained");
        tick(68100); check(run_permit===0 && tripped_led===1,"asynchronous trigger trips interlock");
        // Software trigger activity cannot clear the latched veto.
        repeat(20) begin trigger_async=~trigger_async; tick(3); end
        trigger_async=0; tick(20);
        check(run_permit===0 && tripped_led===1,"trigger toggles cannot restore permit");
        // Short reset bounces cannot clear the latch.
        repeat(5) begin reset_button=1; tick(2); reset_button=0; tick(3); end
        tick(20); check(run_permit===0 && tripped_led===1,"reset bounce rejected while tripped");
        reset_button=1; tick(15);
        check(run_permit===0 && tripped_led===0 && ready_led===0,"qualified physical reset clears latch with permit OFF");
        // Release bounce must not briefly re-enable the effect boundary.
        repeat(4) begin reset_button=0; tick(2); reset_button=1; tick(3);
            check(run_permit===0,"release bounce keeps permit OFF"); end
        reset_button=0; tick(15);
        check(run_permit===1 && ready_led===1,"stable physical release rearms");
        $display("BOARD_WRAPPER_SIM: PASS (%0d checks; debounce scaled to 8 cycles)",checks);
        $finish;
    end
    initial begin #3000000; $fatal(1,"BOARD_WRAPPER_SIM_TIMEOUT"); end
endmodule
