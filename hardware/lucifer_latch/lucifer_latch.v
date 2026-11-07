module lucifer_latch (
    input  wire       clk,           // 100MHz system clock
    input  wire       rst_n,         // Active-low reset (physical button only)
    input  wire       trigger_in,    // Software trigger signal from Python
    input  wire [7:0] threat_level,  // 0-255 threat level from detection system
    output reg        latch_state,   // 0=ARMED, 1=TRIGGERED (irreversible)
    output reg        veto_signal,   // Kill signal to main computation
    output reg        status_led     // Visual indicator
);

// =============================================================================
// TIMING PARAMETERS
// =============================================================================
// 100MHz clock = 10ns period
// 670µs = 670,000ns = 67,000 clock cycles
// We add a small margin for safety: 68,000 cycles

localparam TIMING_FLOOR_CYCLES = 17'd68000;  // 680µs (includes margin)
localparam THREAT_THRESHOLD    = 8'd191;      // ~75% of 255 (0.75 * 255 ≈ 191)

// =============================================================================
// STATE MACHINE
// =============================================================================
localparam STATE_ARMED     = 2'b00;
localparam STATE_EVALUATING = 2'b01;
localparam STATE_TRIGGERED = 2'b10;

reg [1:0]  current_state;
reg [16:0] timing_counter;
reg        trigger_latched;
reg [23:0] blink_counter;   // free-running, for clean LED blink (~6Hz @100MHz)

// =============================================================================
// MAIN LOGIC
// =============================================================================
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        // ONLY physical reset can clear the latch
        current_state   <= STATE_ARMED;
        latch_state     <= 1'b0;
        veto_signal     <= 1'b0;
        status_led      <= 1'b0;
        timing_counter  <= 17'd0;
        trigger_latched <= 1'b0;
        blink_counter   <= 24'd0;
    end
    else begin
        blink_counter <= blink_counter + 1'b1;   // always counts while powered
        case (current_state)
            
            STATE_ARMED: begin
                status_led <= 1'b0;  // LED off when armed
                
                // Check for trigger conditions
                if (trigger_in || (threat_level >= THREAT_THRESHOLD)) begin
                    trigger_latched <= 1'b1;
                    timing_counter  <= 17'd0;
                    current_state   <= STATE_EVALUATING;
                end
            end
            
            STATE_EVALUATING: begin
                status_led <= blink_counter[23];  // clean synthesizable blink (no clock-as-data)
                
                // Count up to timing floor
                if (timing_counter < TIMING_FLOOR_CYCLES) begin
                    timing_counter <= timing_counter + 1'b1;
                end
                else begin
                    // Timing floor met - TRIGGER IS NOW IRREVERSIBLE
                    current_state <= STATE_TRIGGERED;
                    latch_state   <= 1'b1;
                    veto_signal   <= 1'b1;
                end
            end
            
            STATE_TRIGGERED: begin
                // PERMANENT STATE - only physical reset can exit
                status_led  <= 1'b1;  // LED solid on
                latch_state <= 1'b1;
                veto_signal <= 1'b1;
                // No transition out of this state via software
            end
            
            default: begin
                // Fail-safe: unknown state triggers latch
                current_state <= STATE_TRIGGERED;
                latch_state   <= 1'b1;
                veto_signal   <= 1'b1;
            end
            
        endcase
    end
end

endmodule
