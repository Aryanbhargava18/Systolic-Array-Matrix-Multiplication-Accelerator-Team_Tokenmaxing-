//==============================================================================
// tb_demo.v
// Readable demo for presentations: loads one signed 4x4 example, runs the
// systolic accelerator and the sequential baseline on the same matrices,
// and prints A, B, the hardware result C, the expected C and the cycle counts.
//
//   make demo        (prints the matrices and PASS/FAIL)
//   make show_demo   (opens the waveform in GTKWave)
//==============================================================================

`timescale 1ns / 1ps

module tb_demo;

    localparam integer N      = 4;
    localparam integer DATA_W = 8;
    localparam integer ACC_W  = 32;

    reg clk, rst_n, start;
    reg wr_en, wr_sel_b;
    reg [$clog2(N*N)-1:0] wr_addr;
    reg signed [DATA_W-1:0] wr_data;

    wire done_sys, done_seq;
    wire [15:0] cyc_sys, cyc_seq;
    wire signed [ACC_W-1:0] c_sys [0:N-1][0:N-1];
    wire signed [ACC_W-1:0] c_seq [0:N-1][0:N-1];

    wire signed [DATA_W-1:0] a_mem [0:N*N-1];
    wire signed [DATA_W-1:0] b_mem [0:N*N-1];

    reg  signed [DATA_W-1:0] A [0:N*N-1];
    reg  signed [DATA_W-1:0] B [0:N*N-1];
    reg  signed [ACC_W-1:0]  exp_c;

    integer i, j, k, errors;

    // Separate buffer instance feeds the sequential baseline with the same data
    input_buffers #(.N(N), .DATA_W(DATA_W)) u_buf (
        .clk(clk), .rst_n(rst_n),
        .wr_en(wr_en), .wr_sel_b(wr_sel_b),
        .wr_addr(wr_addr), .wr_data(wr_data),
        .a_mem(a_mem), .b_mem(b_mem)
    );

    systolic_top #(.N(N), .DATA_W(DATA_W), .ACC_W(ACC_W)) u_sys (
        .clk(clk), .rst_n(rst_n), .start(start),
        .wr_en(wr_en), .wr_sel_b(wr_sel_b),
        .wr_addr(wr_addr), .wr_data(wr_data),
        .done(done_sys), .cycle_count(cyc_sys), .c_out(c_sys)
    );

    seq_matmul #(.N(N), .DATA_W(DATA_W), .ACC_W(ACC_W)) u_seq (
        .clk(clk), .rst_n(rst_n), .start(start),
        .a_mem(a_mem), .b_mem(b_mem),
        .done(done_seq), .cycle_count(cyc_seq), .c_out(c_seq)
    );

    initial clk = 0;
    always #5 clk = ~clk;

    task automatic tick; begin @(negedge clk); end endtask

    initial begin
        // A = [ 1  2  3  4 ;  5  6  7  8 ;  9 10 11 12 ; 13 14 15 16 ]
        for (i = 0; i < N*N; i = i + 1) A[i] = i + 1;
        // B: small signed values (shows negative-number support)
        B[0]  =  1; B[1]  =  0; B[2]  =  2; B[3]  = -1;
        B[4]  =  0; B[5]  =  1; B[6]  = -1; B[7]  =  2;
        B[8]  =  3; B[9]  = -2; B[10] =  1; B[11] =  0;
        B[12] = -1; B[13] =  2; B[14] =  0; B[15] =  1;

        errors = 0;
        rst_n = 0; start = 0; wr_en = 0; wr_sel_b = 0; wr_addr = 0; wr_data = 0;
        $dumpfile("sim/tb_demo.vcd");
        $dumpvars(0, tb_demo);

        repeat (3) tick;
        rst_n = 1;
        tick;

        // Load A then B through the write port (row-major)
        for (i = 0; i < N*N; i = i + 1) begin
            tick; wr_en = 1; wr_sel_b = 0; wr_addr = i[$clog2(N*N)-1:0]; wr_data = A[i];
        end
        for (i = 0; i < N*N; i = i + 1) begin
            tick; wr_en = 1; wr_sel_b = 1; wr_addr = i[$clog2(N*N)-1:0]; wr_data = B[i];
        end
        tick; wr_en = 0;

        tick; start = 1;

        begin : wait_both
            integer t;
            for (t = 0; t < 500; t = t + 1) begin
                @(posedge clk);
                if (done_sys && done_seq) disable wait_both;
            end
        end
        @(posedge clk); #1;

        $display("\n================ Systolic array demo (N = %0d, INT8 x INT8 -> INT32) ================", N);
        $display("\nMatrix A:");
        for (i = 0; i < N; i = i + 1)
            $display("  %5d %5d %5d %5d", A[i*N], A[i*N+1], A[i*N+2], A[i*N+3]);
        $display("\nMatrix B:");
        for (i = 0; i < N; i = i + 1)
            $display("  %5d %5d %5d %5d", B[i*N], B[i*N+1], B[i*N+2], B[i*N+3]);
        $display("\nC = A x B from the systolic array (hardware):");
        for (i = 0; i < N; i = i + 1)
            $display("  %5d %5d %5d %5d", c_sys[i][0], c_sys[i][1], c_sys[i][2], c_sys[i][3]);

        $display("\nExpected C (software reference):");
        for (i = 0; i < N; i = i + 1) begin
            $write("  ");
            for (j = 0; j < N; j = j + 1) begin
                exp_c = 0;
                for (k = 0; k < N; k = k + 1) exp_c = exp_c + A[i*N+k] * B[k*N+j];
                $write("%5d ", exp_c);
                if (c_sys[i][j] !== exp_c) errors = errors + 1;
                if (c_seq[i][j] !== exp_c) errors = errors + 1;
            end
            $write("\n");
        end

        $display("\nLatency, systolic array : %0d cycles (3N)", cyc_sys);
        $display("Latency, sequential MAC : %0d cycles (N^3 + 1)", cyc_seq);
        $display("Speed-up                : %0.2f x", cyc_seq * 1.0 / cyc_sys);

        if (errors == 0)
            $display("\n*** tb_demo: PASS (systolic and sequential both match the reference) ***\n");
        else
            $display("\n*** tb_demo: FAIL (%0d mismatches) ***\n", errors);

        $finish;
    end

endmodule
