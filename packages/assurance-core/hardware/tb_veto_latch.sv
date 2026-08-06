`timescale 1ns/1ps
module tb_veto_latch;
    logic clk = 0;
    logic physical_reset_n = 0;
    logic trip_async = 0;
    logic [7:0] threat_level = 0;
    logic veto, latched;

    weaver_veto_latch dut(.*);
    always #5 clk = ~clk;

    task check_condition(input logic condition, input string message);
        if (!condition) begin
            $display("FAIL: %s", message);
            $fatal(1);
        end
    endtask

    initial begin
        repeat (2) @(posedge clk);
        check_condition(!veto && !latched, "reset must clear latch");
        physical_reset_n = 1;
        threat_level = 8'd190;
        repeat (2) @(posedge clk);
        check_condition(!veto && !latched, "sub-threshold input must remain armed");
        threat_level = 8'd191;
        @(posedge clk); #1;
        check_condition(veto && latched, "threshold must trip");
        threat_level = 0;
        repeat (4) @(posedge clk);
        check_condition(veto && latched, "software inputs must not clear latch");
        physical_reset_n = 0;
        #1;
        check_condition(!veto && !latched, "physical reset must clear latch");
        physical_reset_n = 1;
        #2 trip_async = 1;
        #1;
        check_condition(veto && latched, "asynchronous trip must assert veto");
        trip_async = 0;
        repeat (2) @(posedge clk);
        check_condition(veto && latched, "asynchronous trip must remain latched");
        $display("PASS: veto latch reference behavior");
        $finish;
    end
endmodule
