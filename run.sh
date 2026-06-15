#!/usr/bin/env bash
# One-command driver for the three-engine regex benchmark.
#
#   ./run.sh              # rigorous run of all three engines + report
#   ./run.sh --quick      # fast, lower-confidence run (for iterating)
#   ./run.sh --engines ezi,rust   # subset (names: ezi, rust, go)
#   ./run.sh --report-only        # just regenerate REPORT.md from existing results
#
# Builds each runner optimized, runs the identical measurement protocol, writes
# results/{zig,rust,go}.tsv, then renders results/REPORT.md (human-readable).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# ── parse args ──
QUICK=0
REPORT_ONLY=0
ENGINES="ezi,rust,go"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --quick)       QUICK=1; shift ;;
    --report-only) REPORT_ONLY=1; shift ;;
    --engines)     ENGINES="$2"; shift 2 ;;
    --engines=*)   ENGINES="${1#*=}"; shift ;;
    -h|--help)     sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ── measurement tuning (forwarded identically to every engine) ──
if [[ $QUICK -eq 1 ]]; then
  RB_WARMUP=2
  RB_SEARCH_MIN_SAMPLES=8;  RB_SEARCH_MIN_MS=150;  RB_SEARCH_MAX_MS=500
  RB_COMPILE_MIN_SAMPLES=8; RB_COMPILE_MIN_MS=80;  RB_COMPILE_MAX_MS=300
else
  RB_WARMUP=5
  RB_SEARCH_MIN_SAMPLES=40;  RB_SEARCH_MIN_MS=600;  RB_SEARCH_MAX_MS=3000
  RB_COMPILE_MIN_SAMPLES=50; RB_COMPILE_MIN_MS=300; RB_COMPILE_MAX_MS=2000
fi
export RB_WARMUP RB_SEARCH_MIN_SAMPLES RB_SEARCH_MIN_MS RB_SEARCH_MAX_MS \
       RB_COMPILE_MIN_SAMPLES RB_COMPILE_MIN_MS RB_COMPILE_MAX_MS

mkdir -p results results/.bin

has_engine() { [[ ",$ENGINES," == *",$1,"* ]]; }

if [[ $REPORT_ONLY -eq 1 ]]; then
  python3 report.py
  exit 0
fi

# ── corpora ──
echo "==> provisioning corpora"
python3 corpus.py

# ── metadata (engine versions, machine) ──
echo "==> recording environment"
{
  echo "cpu=$(sysctl -n machdep.cpu.brand_string 2>/dev/null || uname -m)"
  echo "os=$(uname -sr)"
  echo "zig=$(zig version 2>/dev/null || echo '?')"
  echo "rustc=$(rustc --version 2>/dev/null | sed 's/rustc //' || echo '?')"
  echo "go=$(go version 2>/dev/null | sed 's/go version //' || echo '?')"
  reg=$(grep -A1 'name = "regex"' rust/Cargo.lock 2>/dev/null | grep version | head -1 | sed 's/.*"\(.*\)".*/regex \1/')
  echo "regex=${reg:-?}"
  # Pinned engine commit, read from THIS repo's dependency manifest (self-contained — no local
  # ezi_gex checkout required). Shows the short commit the benchmark was built against.
  ezicommit=$(grep -m1 'ezi-gex.git?ref=' zig/build.zig.zon 2>/dev/null | sed 's/.*#\([0-9a-f]*\).*/\1/' | cut -c1-12)
  echo "ezi_gex=${ezicommit:+git ${ezicommit}}"
} > results/meta.txt

ZARGS="$RB_WARMUP $RB_SEARCH_MIN_SAMPLES $RB_SEARCH_MIN_MS $RB_SEARCH_MAX_MS $RB_COMPILE_MIN_SAMPLES $RB_COMPILE_MIN_MS $RB_COMPILE_MAX_MS"

# ── ezi_gex (Zig) ──
if has_engine ezi; then
  echo "==> building ezi_gex runner (Zig, ReleaseFast)"
  ( cd zig && zig build --release=fast )
  echo "==> running ezi_gex"
  # Zig writes results/zig.tsv directly; progress goes to stderr.
  zig/zig-out/bin/zig-runner "$ROOT" $ZARGS
fi

# ── Rust ──
if has_engine rust; then
  echo "==> building Rust runner (release + LTO)"
  cargo build --release --manifest-path rust/Cargo.toml
  echo "==> running Rust"
  rust/target/release/rust-runner "$ROOT"
fi

# ── Go ──
if has_engine go; then
  echo "==> building Go runner"
  go build -C go -o "$ROOT/results/.bin/go-runner" .
  echo "==> running Go"
  results/.bin/go-runner "$ROOT"
fi

# ── report ──
echo "==> generating report"
python3 report.py
