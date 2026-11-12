// One asynchronous bit only. This is not a coherent multi-bit bus crossing.
module sync_debounce #(
    parameter integer STABLE_CYCLES = 500000
) (
    input wire clk,
    input wire async_in,
    output reg stable_out = 1'b0,
    output reg initialized = 1'b0
);
    (* ASYNC_REG = "TRUE", SHREG_EXTRACT = "NO" *) reg sync_meta = 1'b0;
    (* ASYNC_REG = "TRUE", SHREG_EXTRACT = "NO" *) reg sync_value = 1'b0;
    localparam integer WIDTH = (STABLE_CYCLES < 2) ? 1 : $clog2(STABLE_CYCLES);
    reg [WIDTH-1:0] count = 0;
    reg last_sample = 1'b0;
    always @(posedge clk) begin
        sync_meta <= async_in;
        sync_value <= sync_meta;
        last_sample <= sync_value;
        // Qualify the initial level too: stable_out's initialization is not
        // an observation of the physical pin. Count the first changed sample.
        if (sync_value != last_sample) begin
            if (STABLE_CYCLES == 1) begin
                stable_out <= sync_value;
                initialized <= 1'b1;
                count <= 0;
            end else count <= 1;
        end else if (!initialized || sync_value != stable_out) begin
            if (count == STABLE_CYCLES-1) begin
                stable_out <= sync_value;
                initialized <= 1'b1;
                count <= 0;
            end else count <= count + 1'b1;
        end else count <= 0;
    end
endmodule
