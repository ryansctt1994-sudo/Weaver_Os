module weaver_veto_latch #(
    parameter logic [7:0] THREAT_THRESHOLD = 8'd191
) (
    input  logic       clk,
    input  logic       physical_reset_n,
    input  logic       trip_async,
    input  logic [7:0] threat_level,
    output logic       veto,
    output logic       latched
);
    // trip_async is an asynchronous assertion path. The target FPGA/ASIC flow
    // must constrain and review the mapping of this path; simulation alone is
    // not silicon validation.
    always_ff @(posedge clk or negedge physical_reset_n or posedge trip_async) begin
        if (!physical_reset_n) begin
            veto    <= 1'b0;
            latched <= 1'b0;
        end else if (trip_async) begin
            veto    <= 1'b1;
            latched <= 1'b1;
        end else if (latched || threat_level >= THREAT_THRESHOLD) begin
            veto    <= 1'b1;
            latched <= 1'b1;
        end else begin
            veto    <= 1'b0;
            latched <= 1'b0;
        end
    end
endmodule

