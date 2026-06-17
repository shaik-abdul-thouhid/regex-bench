# Regex engine benchmark — ezi_gex vs Rust `regex` vs Go `regexp`

A like-for-like, three-way throughput + compile-time comparison on **real**, byte-identical haystacks and real-world patterns. Modelled on [rebar](https://github.com/BurntSushi/rebar).

## Environment

- **When:** 2026-06-17 17:56 UTC
- **CPU:** Apple M4
- **OS:** Darwin 25.5.0
- **ezi_gex:** git 92b7f73212b5 (Zig 0.17.0-dev.864+3deb86baf, ReleaseFast)
- **Rust `regex`:** regex 1.12.4 (1.96.0 (ac68faa20 2026-05-25), release + LTO, edition 2024)
- **Go `regexp`:** go1.26.4 darwin/arm64 (stdlib RE2)

## Method

- **Operation:** count all non-overlapping leftmost matches over the whole haystack — `re.count` (ezi_gex), `find_iter().count()` (Rust), `len(FindAllIndex(-1))` (Go). Go's stdlib has no allocation-free counting iterator, so its number includes materializing match positions (a real cost of Go's API).
- **Protocol (identical in all three):** compile once (excluded), warm up, then time each iteration until both a minimum sample count **and** a minimum wall-clock elapse (capped by a maximum). Reported throughput uses the **median**; `best` uses the fastest sample. Compile time is measured separately, the same way.
- **Correctness gate:** every engine must report the same match count for a cell, or the cell is flagged. This makes each comparison truly apples-to-apples.

## Correctness cross-check

✅ **All 32 cells agree** on the match count across ezi_gex, Rust, Go — every comparison below is apples-to-apples.

## Search throughput (median — higher is better)

### `sherlock` (594,933 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| lit_sherlock | `Sherlock` | 97 | **40.42 GiB/s** | 38.66 GiB/s | 18.27 GiB/s | ezi_gex |
| lit_the | `the` | 7,218 | **6.68 GiB/s** | 5.37 GiB/s | 483.4 MiB/s | ezi_gex |
| lit_phrase | `Sherlock Holmes` | 91 | **41.17 GiB/s** | 39.34 GiB/s | 14.79 GiB/s | ezi_gex |
| alt_names | `Sherlock\|Holmes\|Watson\|Mycroft\|Lestrad…` | 677 | 7.38 GiB/s | **7.63 GiB/s** | 20.1 MiB/s | Rust |
| ci_the | `(?i)the` | 7,987 | 1.70 GiB/s | **2.02 GiB/s** | 62.9 MiB/s | Rust |
| ci_phrase | `(?i)sherlock holmes` | 96 | 6.97 GiB/s | **9.66 GiB/s** | 54.0 MiB/s | Rust |
| bword_the | `\bthe\b` | 5,426 | 3.18 GiB/s | **3.59 GiB/s** | 77.1 MiB/s | Rust |
| letters_uni | `\p{L}+` | 108,992 | 158.3 MiB/s | **207.2 MiB/s** | 26.2 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 253 | **18.78 GiB/s** | 3.03 GiB/s | 52.7 MiB/s | ezi_gex |
| cap_word | `\p{Lu}\p{Ll}+` | 9,451 | 448.7 MiB/s | **672.8 MiB/s** | 44.3 MiB/s | Rust |
| alpha_ascii | `[A-Za-z]+` | 109,000 | 190.2 MiB/s | **203.7 MiB/s** | 32.6 MiB/s | Rust |
| digits | `\d+` | 253 | **19.08 GiB/s** | 3.03 GiB/s | 82.5 MiB/s | ezi_gex |
| near | `Holmes.{0,30}Watson\|Watson.{0,30}Holmes` | 7 | 5.40 GiB/s | **7.34 GiB/s** | 55.3 MiB/s | Rust |
| the_word | `the\s+\p{L}+` | 5,404 | 734.8 MiB/s | **2.16 GiB/s** | 266.7 MiB/s | Rust |

### `subtitles-ru` (613,423 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| ci_ru | `(?i)что` | 1,285 | 4.45 GiB/s | **6.28 GiB/s** | 56.8 MiB/s | Rust |
| letters_uni | `\p{L}+` | 56,496 | 268.0 MiB/s | **288.4 MiB/s** | 45.2 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 303 | 1.27 GiB/s | **3.02 GiB/s** | 92.0 MiB/s | Rust |
| cap_word | `\p{Lu}\p{Ll}+` | 12,682 | 316.9 MiB/s | **558.6 MiB/s** | 67.8 MiB/s | Rust |
| script_cyrillic | `\p{Cyrillic}+` | 56,493 | 264.8 MiB/s | **290.3 MiB/s** | 50.7 MiB/s | Rust |

### `logs` (600,225 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| bword_the | `\bthe\b` | 260 | **28.30 GiB/s** | 27.32 GiB/s | 74.6 MiB/s | ezi_gex |
| alpha_ascii | `[A-Za-z]+` | 67,976 | 351.1 MiB/s | **446.8 MiB/s** | 41.8 MiB/s | Rust |
| digits | `\d+` | 59,966 | **604.0 MiB/s** | 468.5 MiB/s | 47.7 MiB/s | ezi_gex |
| words_perl | `\w+` | 117,413 | 280.7 MiB/s | **343.4 MiB/s** | 29.3 MiB/s | Rust |
| word_boundary | `\b\w+\b` | 117,413 | 234.3 MiB/s | **391.1 MiB/s** | 24.4 MiB/s | Rust |
| ipv4 | `(?:\d{1,3}\.){3}\d{1,3}` | 3,153 | 396.7 MiB/s | **680.3 MiB/s** | 49.7 MiB/s | Rust |
| date_iso | `\d{4}-\d{2}-\d{2}` | 1,248 | **8.89 GiB/s** | 6.21 GiB/s | 60.9 MiB/s | ezi_gex |
| email | `[\w.+-]+@[\w-]+\.[\w.-]+` | 1,248 | 4.40 GiB/s | **6.75 GiB/s** | 45.0 MiB/s | Rust |
| uri | `https?://[^\s"]+` | 2,902 | 1.97 GiB/s | **2.19 GiB/s** | 265.1 MiB/s | Rust |
| log_line | `(?m)^(\S+) \S+ \S+ \[([^\]]+)\] "(\w+)…` | 1,905 | 973.7 MiB/s | **1.30 GiB/s** | 71.6 MiB/s | Rust |

### `subtitles-zh` (613,427 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| letters_uni | `\p{L}+` | 46,847 | 288.5 MiB/s | **367.2 MiB/s** | 47.8 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 6,811 | 826.5 MiB/s | **1005.4 MiB/s** | 96.7 MiB/s | Rust |
| script_han | `\p{Han}+` | 26,657 | 385.6 MiB/s | **430.2 MiB/s** | 77.9 MiB/s | Rust |

## Compile time (median — lower is better)

Time to build the matcher object from the pattern string (engine construction; for ezi_gex this includes the eager-DFA determinization). Corpus-independent.

| pattern | regex | ezi_gex | Rust | Go |
|---|---|---|---|---|
| lit_sherlock | `Sherlock` | 833 ns | 1.58 µs | 500 ns |
| lit_the | `the` | 708 ns | 1.12 µs | 333 ns |
| lit_phrase | `Sherlock Holmes` | 1.00 µs | 2.12 µs | 667 ns |
| alt_names | `Sherlock\|Holmes\|Watson\|Mycroft\|Lestrad…` | 1.62 µs | 20.50 µs | 1.79 µs |
| ci_the | `(?i)the` | 26.92 µs | 14.17 µs | 333 ns |
| ci_phrase | `(?i)sherlock holmes` | 137.58 µs | 64.58 µs | 625 ns |
| ci_ru | `(?i)что` | 32.12 µs | 32.46 µs | 375 ns |
| bword_the | `\bthe\b` | 3.58 µs | 5.79 µs | 417 ns |
| letters_uni | `\p{L}+` | 611.23 µs | 118.38 µs | 2.75 µs |
| numbers_uni | `\p{N}+` | 129.33 µs | 37.67 µs | 875 ns |
| cap_word | `\p{Lu}\p{Ll}+` | 558.83 µs | 149.27 µs | 4.79 µs |
| alpha_ascii | `[A-Za-z]+` | 2.42 µs | 3.67 µs | 250 ns |
| digits | `\d+` | 43.54 µs | 24.54 µs | 209 ns |
| words_perl | `\w+` | 836.92 µs | 132.67 µs | 250 ns |
| word_boundary | `\b\w+\b` | 1.21 ms | 174.67 µs | 417 ns |
| script_cyrillic | `\p{Cyrillic}+` | 13.54 µs | 16.58 µs | 333 ns |
| script_han | `\p{Han}+` | 33.50 µs | 21.46 µs | 375 ns |
| near | `Holmes.{0,30}Watson\|Watson.{0,30}Holmes` | 233.17 µs | 126.08 µs | 5.25 µs |
| the_word | `the\s+\p{L}+` | 566.58 µs | 121.88 µs | 3.17 µs |
| ipv4 | `(?:\d{1,3}\.){3}\d{1,3}` | 598.54 µs | 149.33 µs | 1.08 µs |
| date_iso | `\d{4}-\d{2}-\d{2}` | 418.12 µs | 126.12 µs | 834 ns |
| email | `[\w.+-]+@[\w-]+\.[\w.-]+` | 811.42 µs | 463.92 µs | 958 ns |
| uri | `https?://[^\s"]+` | 29.50 µs | 20.29 µs | 750 ns |
| log_line | `(?m)^(\S+) \S+ \S+ \[([^\]]+)\] "(\w+)…` | 1.06 ms | 279.58 µs | 2.38 µs |

## Summary

Search speed relative to **ezi_gex** (geometric mean over all shared cells; `>1.0` means the engine is faster than ezi_gex, `<1.0` means slower):

| engine | geomean speed vs ezi_gex | cells fastest |
|---|--:|--:|
| ezi_gex | 1.00× | 8 / 32 |
| Rust | 1.10× | 24 / 32 |
| Go | 0.05× | 0 / 32 |

> Throughput drifts run-to-run with thermal/background load; read these as directional, not to 3 sig figs. The match-count cross-check above is exact.

