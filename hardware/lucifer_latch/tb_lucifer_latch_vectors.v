`timescale 1ns/1ps
// Differential testbench: replays the shared vectors against the RTL.
//
// Each line of the vector file is
//   cycles rst_n trigger_in threat_level exp_state exp_latch exp_veto exp_led
// Inputs change half a cycle before a rising edge and are held for `cycles` edges.
// One time unit after the last edge, state, latch, veto and LED are compared with the
// expected values, which come from the Python twin (weaver_runtime.veto). Any
// mismatch is printed and the run ends with $fatal, so a disagreement fails CI.
//
// Run from the repository root:
//   iverilog -g2012 -o /tmp/tbv.vvp hardware/lucifer_latch/tb_lucifer_latch_vectors.v \
//            hardware/lucifer_latch/lucifer_latch.v
//   vvp -n /tmp/tbv.vvp +VECTORS=hardware/lucifer_latch/vectors/lucifer_latch_vectors.txt
module tb_lucifer_latch_vectors;
    reg clk = 0, rst_n = 0, trigger_in = 0;
    reg [7:0] threat_level = 0;
    wire latch_state, veto_signal, status_led;

    lucifer_latch dut(.clk(clk), .rst_n(rst_n), .trigger_in(trigger_in),
        .threat_level(threat_level), .latch_state(latch_state),
        .veto_signal(veto_signal), .status_led(status_led));

    always #5 clk = ~clk;

    integer fd, n, segments, mismatches, k;
    integer cycles, r, t, th, es, el, ev, ed;
    reg [8*512-1:0] path;
    longint total_cycles;

    initial begin
        if (!$value$plusargs("VECTORS=%s", path)) begin
            $fatal(1, "missing +VECTORS=<file>");
        end
        fd = $fopen(path, "r");
        if (fd == 0) $fatal(1, "cannot open vector file");
        segments = 0; mismatches = 0; total_cycles = 0;
        @(negedge clk);
        while (!$feof(fd)) begin
            n = $fscanf(fd, "%d %d %d %d %d %d %d %d\n", cycles, r, t, th, es, el, ev, ed);
            if (n == 8) begin
                rst_n = r[0]; trigger_in = t[0]; threat_level = th[7:0];
                if (r == 0) #1;  // async reset takes effect before the first edge
                for (k = 0; k < cycles; k = k + 1) @(posedge clk);
                #1;
                if (dut.current_state !== es[1:0] || latch_state !== el[0] ||
                    veto_signal !== ev[0] || status_led !== ed[0]) begin
                    mismatches = mismatches + 1;
                    $display("MISMATCH segment %0d: got state=%0d latch=%0d veto=%0d led=%0d, expected %0d %0d %0d %0d",
                             segments, dut.current_state, latch_state, veto_signal, status_led,
                             es, el, ev, ed);
                end
                segments = segments + 1;
                total_cycles = total_cycles + cycles;
                @(negedge clk);
            end else if (n > 0) begin
                $fatal(1, "malformed vector line after segment %0d", segments);
            end
        end
        $fclose(fd);
        $display("SEGMENTS: %0d  CYCLES: %0d  MISMATCHES: %0d", segments, total_cycles, mismatches);
        if (segments == 0) $fatal(1, "no segments read");
        if (mismatches != 0) $fatal(1, "RTL and twin disagree");
        $display("VERDICT: RTL MATCHES TWIN ON ALL SEGMENTS");
        $finish;
    end
endmodule
