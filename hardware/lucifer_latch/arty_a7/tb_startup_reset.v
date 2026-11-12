`timescale 1ns/1ps
module tb_startup_reset;
    reg clk=0, held_reset=1, bouncing_reset=0;
    wire held_permit, released_permit, bouncing_permit;
    integer i;
    always #5 clk=~clk;
    lucifer_arty_a7 held(.clk(clk), .reset_button(held_reset),
        .trigger_async(1'b0), .run_permit(held_permit), .tripped_led(), .ready_led());
    lucifer_arty_a7 released(.clk(clk), .reset_button(1'b0),
        .trigger_async(1'b0), .run_permit(released_permit), .tripped_led(), .ready_led());
    lucifer_arty_a7 bouncing(.clk(clk), .reset_button(bouncing_reset),
        .trigger_async(1'b0), .run_permit(bouncing_permit), .tripped_led(), .ready_led());
    task tick(input integer n);
        integer k;
        begin for(k=0;k<n;k=k+1) begin @(posedge clk); #1; end end
    endtask
    initial begin
        // Default 500000-cycle qualification, including reset already held at boot.
        for(i=0;i<499999;i=i+1) begin
            tick(1);
            if(held_permit!==0 || released_permit!==0 || bouncing_permit!==0)
                $fatal(1,"Permit before initial stable-level qualification at cycle %0d", i+1);
            if(i==249999) bouncing_reset=1;
            if(i==349999) bouncing_reset=0;
        end
        tick(8);
        if(released_permit!==1 || held_permit!==0 || bouncing_permit!==0)
            $fatal(1,"Initial release, held reset or bounce incorrectly qualified");
        // Bounced release must qualify from the last transition, not boot time.
        tick(350010);
        if(bouncing_permit!==1 || held_permit!==0)
            $fatal(1,"Post-bounce initialization or held reset failed");
        // Qualified held reset still requires a fully qualified release.
        held_reset=0;
        for(i=0;i<500000;i=i+1) begin
            tick(1);
            if(held_permit!==0) $fatal(1,"Held reset released before qualification");
        end
        tick(3);
        if(held_permit!==1) $fatal(1,"Stable reset release did not rearm");
        $display("STARTUP_RESET_SIM: PASS (default 5 ms qualification; held, released, bouncing and release cases)");
        $finish;
    end
    initial begin #15000000; $fatal(1,"STARTUP_RESET_TIMEOUT"); end
endmodule
