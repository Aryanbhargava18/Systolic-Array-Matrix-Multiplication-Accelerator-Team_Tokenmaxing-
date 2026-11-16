# Systolic Array Matrix Multiplication — Architecture

## Goal

A small **output-stationary** systolic-array accelerator for \(C = A \times B\) with
signed 8-bit operands and 32-bit accumulators. Parameter `N` selects a
**3×3** or **4×4** PE grid (B.Tech-scale FPGA target).

## Why output-stationary?

Each PE owns one \(C_{ij}\) and accumulates all \(k\) products in place.
**A** streams left→right; **B** streams top→bottom, with intentional skew so
\(A_{ik}\) and \(B_{kj}\) meet at PE\((i,j)\).

Many published and teaching arrays use **weight-stationary** dataflow (often
higher steady-state PE utilization). Output-stationary is still a standard
option (e.g. Berkeley Gemmini can be configured OS or WS). The trade-off is
honest: fill/drain leave PEs idle part of the time (~33% utilization on 4×4).
See [related_work.md](related_work.md).

## Block diagram

```
                    wr_en / wr_addr / wr_data
                              |
                              v
                     +------------------+
                     |  input_buffers   |  A[], B[] scratchpads
                     +--------+---------+
                              |
              +---------------v----------------+
              |           controller           |
              |  IDLE -> CLEAR -> RUN -> DONE  |
              |  skewed a_west[] / b_north[]   |
              +-------+--------------+---------+
                      |              |
                      v              v
              +--------------------------------+
              |     systolic_array (N x N)     |
              |   PE = mac_unit + a/b pipes    |
              +----------------+---------------+
                               |
                               v
                      +----------------+
                      |  output_regs   |  capture C on done
                      +----------------+
```

## PE microarchitecture

On each enabled cycle:

- \(C \leftarrow C + a_{in} \times b_{in}\) (MAC)
- \(a_{out} \leftarrow a_{in}\), \(b_{out} \leftarrow b_{in}\) (systolic pipes)

`clear` zeros the accumulator (CLEAR state).

## Controller schedule

Injection at boundary time \(t\):

- west\([i] \leftarrow A[i][k]\) when \(t = i + k\)
- north\([j] \leftarrow B[k][j]\) when \(t = j + k\)

Meeting time at PE\((i,j)\): \(r = i + j + k\).
Last MAC: \(r = 3N - 3\). RUN window: \(3N - 2\) cycles.
**start → done latency = \(3N\)** (12 for \(N=4\), 9 for \(N=3\)).

## Baseline comparison

`seq_matmul`: one MAC per cycle → latency \(N^3 + 1\) (65 for \(N=4\)).

| N | Systolic | Sequential | Speed-up |
|---|----------|------------|----------|
| 3 | 9        | 28         | 3.11×    |
| 4 | 12       | 65         | 5.42×    |

Throughput (4×4): \(64\) MACs / \(12\) cycles ≈ **5.33 MACs/cycle**
vs sequential ≈ **0.98 MACs/cycle**.

PE utilization ≈ \(5.33 / 16 ≈ 33\%\) (fill/drain tax — expected for OS).

## Module list

| Module            | Role                                      |
|-------------------|-------------------------------------------|
| `mac_unit.v`      | Combinational signed MAC                  |
| `pe.v`            | Output-stationary PE                      |
| `systolic_array.v`| N×N PE mesh                               |
| `controller.v`    | FSM + skew feeder                         |
| `input_buffers.v` | A/B scratchpads                           |
| `output_regs.v`   | C capture on done                         |
| `systolic_top.v`  | Accelerator top                           |
| `seq_matmul.v`    | Sequential baseline                       |

## Tool flow

Verilog RTL → Icarus (`make test`) → VCD waveforms → Vivado synth
(resources + Fmax on lab FPGA) → report + live demo.

## Ports and parameters

All modules share three parameters:

| Parameter | Default | Meaning |
|-----------|---------|---------|
| `N`       | 4       | Array size (N×N PEs, N×N matrices). Tested with 3 and 4. |
| `DATA_W`  | 8       | Width of signed input elements of A and B (INT8). |
| `ACC_W`   | 32      | Width of signed accumulators / result elements of C (INT32). |

`clk` is the rising-edge clock and `rst_n` is an active-low asynchronous reset in every module.

### `systolic_top` (accelerator top level)

| Port | Dir | Width | Meaning |
|------|-----|-------|---------|
| `start` | in | 1 | Level-sensitive. Raise after loading A and B; keep high until `done`, then lower it to return to IDLE. |
| `wr_en` | in | 1 | Write one matrix element this cycle. |
| `wr_sel_b` | in | 1 | 0 = write into A, 1 = write into B. |
| `wr_addr` | in | `$clog2(N*N)` | Row-major element index (`i*N + j`). |
| `wr_data` | in | `DATA_W`, signed | Element value. |
| `done` | out | 1 | High from the end of the computation until `start` is lowered. |
| `cycle_count` | out | 16 | Cycles from `start` to `done` (3N; 12 for N = 4); holds its value in DONE. |
| `c_out[i][j]` | out | `ACC_W`, signed, N×N | Result C. Captured while `done` is high, so it is valid from the cycle **after** `done` rises. |

Typical use: write N² elements of A and N² of B (one per cycle), raise `start`, wait for `done`,
read `c_out` one cycle later, lower `start`.

### `input_buffers`

| Port | Dir | Width | Meaning |
|------|-----|-------|---------|
| `wr_en`, `wr_sel_b`, `wr_addr`, `wr_data` | in | as above | Write port (same as the top level). |
| `a_mem[k]`, `b_mem[k]` | out | `DATA_W`, signed, N² each | Stored A and B, row-major, read by the controller (and by `seq_matmul`). |

### `controller`

| Port | Dir | Width | Meaning |
|------|-----|-------|---------|
| `start` | in | 1 | Starts IDLE → CLEAR → RUN → DONE. |
| `a_mem`, `b_mem` | in | `DATA_W`, N² each | Matrices from the buffers. |
| `clear` | out | 1 | One-cycle pulse that zeroes every PE accumulator (CLEAR state). |
| `enable` | out | 1 | High during RUN: PEs perform a MAC each cycle. |
| `a_west[i]` | out | `DATA_W`, N | Left-edge input of row i: `A[i][k]` at step `t = i + k`, else 0. |
| `b_north[j]` | out | `DATA_W`, N | Top-edge input of column j: `B[k][j]` at step `t = j + k`, else 0. |
| `done`, `cycle_count` | out | 1, 16 | As at the top level. |

### `systolic_array`

| Port | Dir | Width | Meaning |
|------|-----|-------|---------|
| `clear`, `enable` | in | 1 | Broadcast to all PEs. |
| `a_west[i]` | in | `DATA_W`, N | Enters PE(i,0); moves east one PE per cycle. |
| `b_north[j]` | in | `DATA_W`, N | Enters PE(0,j); moves south one PE per cycle. |
| `c_pe[i][j]` | out | `ACC_W`, N×N | Accumulator of PE(i,j), i.e. C[i][j] once RUN ends. |

### `pe` and `mac_unit`

| Port | Dir | Width | Meaning |
|------|-----|-------|---------|
| `clear` | in | 1 | Zero the accumulator (has priority over `enable`). |
| `enable` | in | 1 | `c_out <= c_out + a_in * b_in` this cycle. |
| `a_in`, `b_in` | in | `DATA_W`, signed | Operands from the west / north neighbour. |
| `a_out`, `b_out` | out | `DATA_W`, signed | `a_in`, `b_in` delayed by one cycle (to the east / south neighbour). |
| `c_out` | out | `ACC_W`, signed | Accumulator C[i][j]. |

`mac_unit` is combinational: `y = acc + sign_extend(a * b)` with a full 2·`DATA_W`-bit product.

### `output_regs`

| Port | Dir | Width | Meaning |
|------|-----|-------|---------|
| `capture` | in | 1 | Copy `c_pe` into `c_out` on each clock edge while high (connected to `done`). |
| `c_pe[i][j]` | in | `ACC_W`, N×N | PE accumulators. |
| `c_out[i][j]` | out | `ACC_W`, N×N | Held result. |

### `seq_matmul` (baseline)

Same `start` / `done` handshake and `cycle_count` as the top level, reading `a_mem` / `b_mem` directly.
One MAC per cycle, latency N³ + 1 (65 for N = 4). It has no output register: `c_out` is written by the
last MAC on the same edge that raises `done`, so it is valid as soon as `done` is high.
