`timescale 1ns/1ps
module tb_debounce_default;
    reg clk=0, button=0;
    wire qualified;
    sync_debounce dut(.clk(clk),.async_in(button),.stable_out(qualified));
    always #5 clk=~clk;
    task tick(input integer n);
        integer i;
        begin for(i=0;i<n;i=i+1) begin @(posedge clk); #1; end end
    endtask
    initial begin
        tick(5); #2; button=1;
        tick(500000);
        if(qualified!==0) $fatal(1,"Default debounce asserted before 500000 synchronized cycles");
        tick(3);
        if(qualified!==1) $fatal(1,"Default debounce failed to assert after stable hold");
        button=0; tick(500000);
        if(qualified!==1) $fatal(1,"Default debounce released too soon");
        tick(3);
        if(qualified!==0) $fatal(1,"Default debounce failed to release");
        $display("DEFAULT_DEBOUNCE_SIM: PASS (500000-cycle press and release, 5 ms each at 100 MHz)");
        $finish;
    end
    initial begin #11000000; $fatal(1,"DEFAULT_DEBOUNCE_TIMEOUT"); end
endmodule
