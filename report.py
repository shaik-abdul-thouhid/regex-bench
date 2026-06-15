#!/usr/bin/env python3
"""Merge the three engines' TSV results into a human-readable report.

Reads results/{zig,rust,go}.tsv (written by the runners), cross-checks that every
engine agrees on the match count for each (pattern x corpus) cell — the built-in
correctness gate — and renders results/REPORT.md plus a condensed console summary.

Throughput and time are auto-scaled to human units (MiB/s, GiB/s; ns, us, ms).
"""
import os
import sys
import math
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")

ENGINES = ["ezi_gex", "rust", "go"]
ENGINE_LABEL = {"ezi_gex": "ezi_gex", "rust": "Rust", "go": "Go"}
ENGINE_FILE = {"ezi_gex": "zig.tsv", "rust": "rust.tsv", "go": "go.tsv"}


# ───────────────────────────── human units ─────────────────────────────────

def human_throughput(bytes_, ns):
    if not ns or not bytes_:
        return "n/a"
    bps = bytes_ * 1e9 / ns
    KiB, MiB, GiB = 1024.0, 1024.0 ** 2, 1024.0 ** 3
    if bps >= GiB:
        return f"{bps / GiB:.2f} GiB/s"
    if bps >= MiB:
        return f"{bps / MiB:.1f} MiB/s"
    if bps >= KiB:
        return f"{bps / KiB:.1f} KiB/s"
    return f"{bps:.0f} B/s"


def human_time(ns):
    if ns is None:
        return "—"
    f = float(ns)
    if f < 1e3:
        return f"{f:.0f} ns"
    if f < 1e6:
        return f"{f / 1e3:.2f} µs"
    if f < 1e9:
        return f"{f / 1e6:.2f} ms"
    return f"{f / 1e9:.2f} s"


def human_count(n):
    return f"{n:,}"


def fmt_pattern(pat):
    """Display a regex in a Markdown table cell: truncate, escape table-breakers."""
    p = pat if len(pat) <= 40 else pat[:38] + "…"
    p = p.replace("|", "\\|").replace("`", "'")
    return f"`{p}`"


# ───────────────────────────── data loading ────────────────────────────────

def load_tsv(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        header = None
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if header is None:
                header = parts
                continue
            rows.append(dict(zip(header, parts)))
    return rows


def load_cases_order():
    """Canonical case order + display pattern + corpora, from cases.tsv."""
    order, pattern, corpora = [], {}, {}
    path = os.path.join(HERE, "cases.tsv")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) < 3:
                continue
            name = fields[0]
            order.append(name)
            pattern[name] = fields[2]
            corpora[name] = fields[1].split(",")
    return order, pattern, corpora


def load_meta():
    path = os.path.join(RESULTS, "meta.txt")
    if not os.path.exists(path):
        return {}
    meta = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.rstrip("\n").split("=", 1)
                meta[k] = v
    return meta


# ────────────────────────────── main ───────────────────────────────────────

def main():
    case_order, patterns, case_corpora = load_cases_order()
    meta = load_meta()

    # cell[(case, corpus)][engine] = row dict
    cell = {}
    present_engines = []
    for eng in ENGINES:
        rows = load_tsv(os.path.join(RESULTS, ENGINE_FILE[eng]))
        if rows:
            present_engines.append(eng)
        for r in rows:
            key = (r["case"], r["corpus"])
            cell.setdefault(key, {})[eng] = r

    if not present_engines:
        print("No results found in", RESULTS, file=sys.stderr)
        sys.exit(1)

    # corpora in first-seen order
    corpora = []
    for name in case_order:
        for c in case_corpora.get(name, []):
            if (name, c) in cell and c not in corpora:
                corpora.append(c)

    # ── correctness cross-check ──
    disagreements = []
    agree_cells = 0
    for (case, corpus), engines in cell.items():
        counts = {e: int(r["matches"]) for e, r in engines.items()}
        if len(set(counts.values())) > 1:
            disagreements.append((case, corpus, counts))
        else:
            agree_cells += 1

    out = []
    w = out.append

    w("# Regex engine benchmark — ezi_gex vs Rust `regex` vs Go `regexp`\n")
    w("A like-for-like, three-way throughput + compile-time comparison on **real**, "
      "byte-identical haystacks and real-world patterns. Modelled on "
      "[rebar](https://github.com/BurntSushi/rebar).\n")

    # environment
    w("## Environment\n")
    w(f"- **When:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    if meta.get("cpu"):
        w(f"- **CPU:** {meta['cpu']}")
    if meta.get("os"):
        w(f"- **OS:** {meta['os']}")
    w(f"- **ezi_gex:** {meta.get('ezi_gex', 'local working copy')} "
      f"(Zig {meta.get('zig', '?')}, ReleaseFast)")
    w(f"- **Rust `regex`:** {meta.get('regex', '?')} "
      f"({meta.get('rustc', 'rustc ?')}, release + LTO, edition 2024)")
    w(f"- **Go `regexp`:** {meta.get('go', '?')} (stdlib RE2)")
    w("")

    # methodology
    w("## Method\n")
    w("- **Operation:** count all non-overlapping leftmost matches over the whole "
      "haystack — `re.count` (ezi_gex), `find_iter().count()` (Rust), "
      "`len(FindAllIndex(-1))` (Go). Go's stdlib has no allocation-free counting "
      "iterator, so its number includes materializing match positions (a real cost "
      "of Go's API).")
    w("- **Protocol (identical in all three):** compile once (excluded), warm up, "
      "then time each iteration until both a minimum sample count **and** a minimum "
      "wall-clock elapse (capped by a maximum). Reported throughput uses the "
      "**median**; `best` uses the fastest sample. Compile time is measured "
      "separately, the same way.")
    w("- **Correctness gate:** every engine must report the same match count for a "
      "cell, or the cell is flagged. This makes each comparison truly apples-to-apples.")
    w("")

    # correctness summary
    w("## Correctness cross-check\n")
    if disagreements:
        w(f"⚠️ **{len(disagreements)} cell(s) disagree** on match count "
          f"(comparison invalid there):\n")
        w("| case | corpus | counts |")
        w("|---|---|---|")
        for case, corpus, counts in disagreements:
            cs = ", ".join(f"{ENGINE_LABEL[e]}={v:,}" for e, v in counts.items())
            w(f"| `{case}` | {corpus} | {cs} |")
        w("")
    else:
        w(f"✅ **All {agree_cells} cells agree** on the match count across "
          f"{', '.join(ENGINE_LABEL[e] for e in present_engines)} — every comparison "
          "below is apples-to-apples.\n")

    # ── per-corpus search throughput ──
    w("## Search throughput (median — higher is better)\n")
    ratios = {e: [] for e in present_engines}  # engine throughput / ezi throughput
    win_count = {e: 0 for e in present_engines}

    for corpus in corpora:
        cbytes = None
        rows = []
        for case in case_order:
            key = (case, corpus)
            if key not in cell:
                continue
            engines = cell[key]
            cbytes = next((int(r["corpus_bytes"]) for r in engines.values()), None)
            matches = next((int(r["matches"]) for r in engines.values()), 0)
            tput = {}
            best_e, best_bps = None, -1.0
            for e in present_engines:
                if e in engines:
                    ns = int(engines[e]["search_median_ns"])
                    tput[e] = (cbytes, ns)
                    bps = cbytes * 1e9 / ns if ns else 0
                    if bps > best_bps:
                        best_bps, best_e = bps, e
                else:
                    tput[e] = None
            if best_e:
                win_count[best_e] += 1
            # ratios vs ezi_gex
            if "ezi_gex" in engines:
                ezi_ns = int(engines["ezi_gex"]["search_median_ns"])
                for e in present_engines:
                    if e in engines and ezi_ns:
                        e_ns = int(engines[e]["search_median_ns"])
                        if e_ns:
                            ratios[e].append(ezi_ns / e_ns)  # >1 means e faster than ezi
            rows.append((case, matches, tput, best_e))

        if not rows:
            continue
        size_h = human_throughput(cbytes, 1e9)  # dummy; show size instead
        w(f"### `{corpus}` ({cbytes:,} bytes)\n")
        header = "| pattern | regex | matches | " + " | ".join(ENGINE_LABEL[e] for e in present_engines) + " | fastest |"
        w(header)
        w("|" + "---|" * (4 + len(present_engines)))
        for case, matches, tput, best_e in rows:
            cells = []
            for e in present_engines:
                if tput[e] is None:
                    cells.append("—")
                else:
                    cb, ns = tput[e]
                    s = human_throughput(cb, ns)
                    if e == best_e:
                        s = f"**{s}**"
                    cells.append(s)
            w(f"| {case} | {fmt_pattern(patterns.get(case, ''))} | {human_count(matches)} | " +
              " | ".join(cells) + f" | {ENGINE_LABEL[best_e]} |")
        w("")

    # ── compile time ──
    w("## Compile time (median — lower is better)\n")
    w("Time to build the matcher object from the pattern string (engine construction; "
      "for ezi_gex this includes the eager-DFA determinization). Corpus-independent.\n")
    w("| pattern | regex | " + " | ".join(ENGINE_LABEL[e] for e in present_engines) + " |")
    w("|" + "---|" * (2 + len(present_engines)))
    seen = set()
    for case in case_order:
        # find any cell for this case
        row_for = {}
        for corpus in corpora:
            key = (case, corpus)
            if key in cell:
                for e, r in cell[key].items():
                    row_for.setdefault(e, r)
        if not row_for or case in seen:
            continue
        seen.add(case)
        cells = []
        for e in present_engines:
            if e in row_for:
                cells.append(human_time(int(row_for[e]["compile_median_ns"])))
            else:
                cells.append("—")
        w(f"| {case} | {fmt_pattern(patterns.get(case, ''))} | " + " | ".join(cells) + " |")
    w("")

    # ── aggregate summary ──
    w("## Summary\n")

    def geomean(xs):
        xs = [x for x in xs if x > 0]
        if not xs:
            return float("nan")
        return math.exp(sum(math.log(x) for x in xs) / len(xs))

    w("Search speed relative to **ezi_gex** (geometric mean over all shared cells; "
      "`>1.0` means the engine is faster than ezi_gex, `<1.0` means slower):\n")
    w("| engine | geomean speed vs ezi_gex | cells fastest |")
    w("|---|--:|--:|")
    total_cells = sum(win_count.values())
    for e in present_engines:
        if e == "ezi_gex":
            gm = 1.0
        else:
            gm = geomean(ratios[e])
        w(f"| {ENGINE_LABEL[e]} | {gm:.2f}× | {win_count[e]} / {total_cells} |")
    w("")
    w("> Throughput drifts run-to-run with thermal/background load; read these as "
      "directional, not to 3 sig figs. The match-count cross-check above is exact.")
    w("")

    report_md = "\n".join(out) + "\n"
    with open(os.path.join(RESULTS, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write(report_md)

    # ── console summary ──
    print("=" * 72)
    print("Regex benchmark — ezi_gex vs Rust vs Go")
    print("=" * 72)
    if disagreements:
        print(f"  CORRECTNESS: {len(disagreements)} disagreement(s)! see REPORT.md")
    else:
        print(f"  correctness: all {agree_cells} cells agree ✓")
    print(f"  engines: {', '.join(ENGINE_LABEL[e] for e in present_engines)}")
    print("  geomean search speed vs ezi_gex:")
    for e in present_engines:
        gm = 1.0 if e == "ezi_gex" else geomean(ratios[e])
        print(f"     {ENGINE_LABEL[e]:>8}: {gm:5.2f}×   (fastest in {win_count[e]}/{total_cells} cells)")
    print(f"\n  full report: {os.path.join(RESULTS, 'REPORT.md')}")
    print("=" * 72)


if __name__ == "__main__":
    main()
