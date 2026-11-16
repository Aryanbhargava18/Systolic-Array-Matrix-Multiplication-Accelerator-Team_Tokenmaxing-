# Related work (for report / viva)

RTL and testbenches in this repository are an original output-stationary
design. The notes below are only for **citing concepts** in the report.

## Dataflow context

Spatial / systolic accelerators commonly use one of:

- **Weight-stationary (WS)** — weights stay in the PE; often high steady-state
  PE utilization when the same weights are reused.
- **Output-stationary (OS)** — each PE owns one \(C_{ij}\) (this project).
- **Input-stationary (IS)** — less common in small teaching arrays.

Berkeley **Gemmini** can be configured for OS or WS (and related modes), which
shows that output-stationary is a legitimate design choice, not a shortcut.
**SCALE-Sim** is useful if you want an independent cycle / utilization model
to compare against your measured 3N latency and ~33% PE use on 4×4.

### Trade-off to state clearly

| | Typical WS | This project (OS) |
|---|---|---|
| What stays in the PE | Weight | Partial sum \(C_{ij}\) |
| Steady-state PE use | Often high once the pipeline is full | ~33% on 4×4 (fill/drain) |
| Natural fit | Reuse same weights many times | One C tile while streaming A and B |

Lower OS utilization is expected; explain fill/drain rather than hiding it.

## Paper notes (same reference list as the IEEE report)

| # | Work | What it does | Why it matters here |
|---|------|--------------|---------------------|
| 1 | H. T. Kung and C. E. Leiserson, "Systolic arrays (for VLSI)," *Sparse Matrix Proceedings 1978*, SIAM, 1979 | Introduces systolic arrays: grids of simple cells, each talking only to its neighbours, for matrix operations. | Origin of the idea we implement; our skewed A/B feed is the classic matrix-multiply mapping. |
| 2 | H. T. Kung, "Why systolic architectures?" *IEEE Computer*, 15(1), 1982 ([doi](https://doi.org/10.1109/MC.1982.1653825)) | Explains the benefits: each operand fetched once and reused many times, local wiring, regular design. | Justifies why an N×N array beats a single MAC (5.42× at N = 4) without extra memory bandwidth. |
| 3 | N. P. Jouppi et al., "In-datacenter performance analysis of a tensor processing unit," ISCA 2017 ([arXiv](https://arxiv.org/abs/1704.04760)) | Google TPU v1: a 256×256 INT8 systolic array, weight-stationary, for neural-network inference. | Shows the same structure at industrial scale with the same INT8 operands we use. |
| 4 | Y.-H. Chen, J. Emer, V. Sze, "Eyeriss," ISCA 2016 ([project page](https://eyeriss.mit.edu/)) | Spatial accelerator for CNNs; proposes row-stationary dataflow and compares dataflows by energy. | Source of the "what stays in the PE" view used to explain our output-stationary choice. |
| 5 | V. Sze et al., "Efficient processing of deep neural networks: A tutorial and survey," *Proc. IEEE*, 2017 ([arXiv](https://arxiv.org/abs/1703.09039)) | Survey of DNN hardware; defines weight-, output- and input-stationary dataflows. | Clear definitions of WS vs OS for the report and viva. |
| 6 | H. Genc et al., "Gemmini," DAC 2021 ([GitHub](https://github.com/ucb-bar/gemmini)) | Open-source generator of systolic-array accelerators, configurable as OS or WS. | Shows OS is a standard, supported option, not a shortcut. |
| 7 | A. Samajdar et al., "SCALE-Sim," 2018 ([arXiv](https://arxiv.org/abs/1811.02883), [GitHub](https://github.com/ARM-software/SCALE-Sim)) | Cycle-level simulator for systolic arrays across sizes and dataflows. | Independent reference for our measured 3N latency and 1/3 utilisation. |
| 8 | Xilinx, "7 Series DSP48E1 Slice User Guide," UG479 ([PDF](https://docs.amd.com/v/u/en-US/ug479_7Series_DSP48E1)) | Describes the FPGA DSP slice (25×18 multiplier, 48-bit accumulator). | Explains why each PE maps to one DSP48E1 (Yosys estimate) and why 4×4 needs about 16. |

Tools: [Icarus Verilog](https://steveicarus.github.io/iverilog/) (simulation),
[GTKWave](https://gtkwave.sourceforge.net/) (waveforms), [Yosys](https://yosyshq.net/yosys/) (early synthesis estimate), Vivado (FPGA synthesis, Phase II).

## Suggested citation sentence

> The accelerator implements an original output-stationary N×N systolic array
> with a sequential MAC baseline for speed-up comparison. Configuration options
> in spatial-array generators such as Gemmini, and cycle models such as
> SCALE-Sim, were consulted only for architectural context.
