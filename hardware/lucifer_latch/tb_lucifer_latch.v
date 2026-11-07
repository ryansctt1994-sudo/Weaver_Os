`timescale 1ns/1ps
// Testbench for lucifer_latch — verifies the SAFETY-CRITICAL claims:
//   1. Reset -> ARMED, all safety outputs deasserted
//   2. trigger_in path arms the countdown
//   3. threat_level >= 191 path arms the countdown
//   4. threat_level < 191 with no trigger does NOT arm
//   5. Latch fires at the 68000-cycle timing floor (680us @100MHz)
//   6. IRREVERSIBILITY: once TRIGGERED, dropping trigger_in cannot clear it
//   7. Only physical reset (rst_n) clears the latch
module tb_lucifer_latch;
    reg clk = 0, rst_n = 0, trigger_in = 0;
    reg [7:0] threat_level = 0;
    wire latch_state, veto_signal, status_led;

    integer pass = 0, fail = 0;
    integer fire_cycle = -1, arm_cycle = -1, cyc = 0;

    lucifer_latch dut(.clk(clk), .rst_n(rst_n), .trigger_in(trigger_in),
        .threat_level(threat_level), .latch_state(latch_state),
        .veto_signal(veto_signal), .status_led(status_led));

    always #5 clk = ~clk;                 // 100MHz -> 10ns period
    always @(posedge clk) cyc = cyc + 1;  // cycle counter

    task check(input cond, input [255:0] name);
        begin
            if (cond) begin pass=pass+1; $display("  PASS: %0s", name); end
            else      begin fail=fail+1; $display("  FAIL: %0s", name); end
        end
    endtask

    initial begin
        $dumpfile("lucifer_latch.vcd"); $dumpvars(0, tb_lucifer_latch);

        // ---- T1: reset state ----
        rst_n=0; trigger_in=0; threat_level=0; repeat(4) @(posedge clk);
        $display("[T1] Reset / ARMED");
        check(latch_state===0 && veto_signal===0, "armed: latch & veto deasserted on reset");
        rst_n=1; @(posedge clk);

        // ---- T2: sub-threshold threat must NOT arm ----
        $display("[T2] Sub-threshold threat (190) does not trigger");
        threat_level=190; repeat(100) @(posedge clk);
        check(latch_state===0 && veto_signal===0, "threat=190 stays armed");
        threat_level=0;

        // ---- T3: trigger_in arms countdown; measure fire time ----
        $display("[T3] trigger_in -> countdown -> fire at timing floor");
        arm_cycle = cyc; trigger_in=1; @(posedge clk); trigger_in=0; // pulse only
        // wait until it fires (bounded)
        begin: wait_fire integer k;
          for (k=0;k<70000;k=k+1) begin
            @(posedge clk);
            if (latch_state===1 && fire_cycle<0) fire_cycle=cyc;
            if (latch_state===1) disable wait_fire;
          end
        end
        check(latch_state===1 && veto_signal===1, "latch fired after trigger pulse");
        $display("       fired ~%0d cycles after arming (expected ~68000)", fire_cycle-arm_cycle);
        check((fire_cycle-arm_cycle) >= 68000 && (fire_cycle-arm_cycle) <= 68010,
              "timing floor ~= 68000 cycles (680us)");

        // ---- T4: IRREVERSIBILITY — software cannot clear it ----
        $display("[T4] Irreversibility under continued software activity");
        trigger_in=0; threat_level=0; repeat(500) @(posedge clk);
        check(latch_state===1 && veto_signal===1, "stays TRIGGERED with all inputs low");
        threat_level=255; trigger_in=1; repeat(50) @(posedge clk); trigger_in=0;
        check(latch_state===1 && veto_signal===1, "stays TRIGGERED under max threat toggling");

        // ---- T5: only physical reset clears ----
        $display("[T5] Physical reset clears the latch");
        rst_n=0; repeat(4) @(posedge clk);
        check(latch_state===0 && veto_signal===0, "rst_n clears latch & veto");
        rst_n=1; @(posedge clk);

        // ---- T6: threat>=threshold path also fires ----
        $display("[T6] threat_level>=191 path arms countdown");
        threat_level=191;
        begin: wait_fire2 integer k;
          for (k=0;k<70000;k=k+1) begin @(posedge clk); if (latch_state===1) disable wait_fire2; end
        end
        check(latch_state===1 && veto_signal===1, "threat=191 path triggers latch");

        $display("\n================ RESULT ================");
        $display("  PASSED: %0d   FAILED: %0d", pass, fail);
        $display("=======================================");
        if (fail==0) $display("  VERDICT: SAFETY-CRITICAL BEHAVIOR VERIFIED");
        else         $display("  VERDICT: DESIGN HAS FAILURES — SEE ABOVE");
        $finish;
    end

    // global watchdog
    initial begin #2000000; $display("WATCHDOG TIMEOUT"); $finish; end
endmodule
