"""Draw a GTKWave-style timing diagram of the systolic demo from sim/tb_demo.vcd.

Usage (from the repo root, after `make demo`; needs matplotlib):
    python3 scripts/plot_waveform.py sim/tb_demo.vcd docs/figures/waveform_demo.png
Shows the FSM state, the skewed A (west) and B (north) feeds, two PE
accumulators and done, from just before start to just after done.
"""
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def parse_vcd(path):
    ids, scope, changes = {}, [], {}
    t = 0
    with open(path) as f:
        in_defs = True
        for line in f:
            tok = line.split()
            if not tok:
                continue
            if in_defs:
                if tok[0] == "$scope":
                    scope.append(tok[2])
                elif tok[0] == "$upscope":
                    scope.pop()
                elif tok[0] == "$var":
                    width, code, name = int(tok[2]), tok[3], tok[4]
                    ids.setdefault(code, []).append((".".join(scope + [name]), width))
                elif tok[0] == "$enddefinitions":
                    in_defs = False
                continue
            c = tok[0]
            if c.startswith("#"):
                t = int(c[1:])
            elif c[0] in "01xz" and len(tok) == 1:
                changes.setdefault(c[1:], []).append((t, c[0]))
            elif c[0] == "b":
                changes.setdefault(tok[1], []).append((t, c[1:]))
    by_name = {}
    for code, names in ids.items():
        for name, width in names:
            by_name[name] = (width, changes.get(code, []))
    return by_name


def signed(bits, width):
    if any(ch in "xz" for ch in bits):
        return None
    v = int(bits, 2)
    if bits and len(bits) == width and bits[0] == "1":
        v -= 1 << width
    return v


def value_at(series, t):
    v = None
    for tt, val in series:
        if tt <= t:
            v = val
        else:
            break
    return v


def main(vcd, out):
    s = parse_vcd(vcd)
    root = "tb_demo"
    clk = s[f"{root}.clk"][1]
    start = s[f"{root}.start"][1]
    done = s[f"{root}.done_sys"][1]
    t_start = next(t for t, v in start if v == "1")
    t_done = next(t for t, v in done if v == "1" and t > t_start)
    period = 10000  # 10 ns in ps (timescale 1ps in VCD)
    t0 = t_start - period
    t1 = t_done + 2 * period

    rows = [("clk", f"{root}.clk", "bit"), ("start", f"{root}.start", "bit"),
            ("state", f"{root}.u_sys.u_ctrl.state", "state")]
    for i in range(4):
        rows.append((f"a_west[{i}]", f"{root}.u_sys.u_array.g_row[{i}].g_col[0].u_pe.a_in", "bus"))
    for j in range(4):
        rows.append((f"b_north[{j}]", f"{root}.u_sys.u_array.g_row[0].g_col[{j}].u_pe.b_in", "bus"))
    rows += [("C[0][0] (PE 0,0)", f"{root}.u_sys.u_array.g_row[0].g_col[0].u_pe.c_out", "bus"),
             ("C[3][3] (PE 3,3)", f"{root}.u_sys.u_array.g_row[3].g_col[3].u_pe.c_out", "bus"),
             ("done", f"{root}.done_sys", "bit")]
    state_names = {0: "IDLE", 1: "CLEAR", 2: "RUN", 3: "DONE"}

    fig, ax = plt.subplots(figsize=(10, 0.42 * len(rows) + 1.0))
    h = 0.32
    for r, (label, name, kind) in enumerate(rows):
        y = len(rows) - 1 - r
        width, ser = s[name]
        times = [t0] + [t for t, _ in ser if t0 < t < t1] + [t1]
        ax.text(t0 - 0.25 * period, y, label, ha="right", va="center", fontsize=11, family="monospace")
        for a, b in zip(times[:-1], times[1:]):
            raw = value_at(ser, a)
            if kind == "bit":
                level = y + (h if raw == "1" else -h)
                ax.plot([a, b], [level, level], color="#1f4e79", lw=1.4)
                ax.plot([b, b], [y - h, y + h], color="#1f4e79", lw=0.6, alpha=0.35)
            else:
                v = signed(raw, width) if raw is not None else None
                if kind == "state":
                    txt = state_names.get(int(raw, 2), "?") if raw else ""
                else:
                    txt = "" if v is None else str(v)
                zero = (v == 0) if kind == "bus" else False
                col = "#888888" if zero else "#b35900"
                ax.plot([a, b], [y + h, y + h], color=col, lw=1.1)
                ax.plot([a, b], [y - h, y - h], color=col, lw=1.1)
                ax.plot([b, b], [y - h, y + h], color=col, lw=1.1)
                if b - a >= 0.6 * period and txt:
                    ax.text((a + b) / 2, y, txt, ha="center", va="center", fontsize=10,
                            color="#555555" if zero else "black")
    # cycle grid at rising edges
    for t, v in clk:
        if v == "1" and t0 <= t <= t1:
            ax.axvline(t, color="#cccccc", lw=0.5, zorder=0)
    ax.axvline(t_start, color="green", lw=1, ls="--")
    ax.axvline(t_done, color="red", lw=1, ls="--")
    ax.text(t_start, len(rows) - 0.3, "start", color="green", fontsize=10, ha="center")
    ax.text(t_done, len(rows) - 0.3, "done (12 cycles)", color="red", fontsize=10, ha="center")
    ax.set_xlim(t0 - 2.6 * period, t1)
    ax.set_ylim(-0.8, len(rows) + 0.1)
    ax.set_yticks([])
    ticks = [t for t, v in clk if v == "1" and t0 <= t <= t1]
    ax.set_xticks(ticks)
    # cycle n = n-th rising clock edge after start is raised (matches cycle_count)
    after = [t for t in ticks if t > t_start]
    ax.set_xticklabels([str(after.index(t) + 1) if t in after else "" for t in ticks], fontsize=10)
    ax.set_xlabel("clock cycle after start (cycle_count); tb/tb_demo.v, N = 4, Icarus Verilog", fontsize=11)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    plt.tight_layout()
    plt.savefig(out, dpi=200)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
