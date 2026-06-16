# Regex engine benchmark — ezi_gex vs Rust `regex` vs Go `regexp`

A like-for-like, three-way throughput + compile-time comparison on **real**, byte-identical haystacks and real-world patterns. Modelled on [rebar](https://github.com/BurntSushi/rebar).

## Environment

- **When:** 2026-06-16 20:02 UTC
- **CPU:** Apple M4
- **OS:** Darwin 25.5.0
- **ezi_gex:** git 87db38e1b674 (Zig 0.17.0-dev.864+3deb86baf, ReleaseFast)
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
| lit_sherlock | `Sherlock` | 97 | **40.67 GiB/s** | 38.43 GiB/s | 18.22 GiB/s | ezi_gex |
| lit_the | `the` | 7,218 | 6.61 GiB/s | **6.82 GiB/s** | 490.2 MiB/s | Rust |
| lit_phrase | `Sherlock Holmes` | 91 | **41.30 GiB/s** | 39.34 GiB/s | 14.79 GiB/s | ezi_gex |
| alt_names | `Sherlock\|Holmes\|Watson\|Mycroft\|Lestrad…` | 677 | 7.38 GiB/s | **7.93 GiB/s** | 20.7 MiB/s | Rust |
| ci_the | `(?i)the` | 7,987 | 1.69 GiB/s | **2.11 GiB/s** | 63.3 MiB/s | Rust |
| ci_phrase | `(?i)sherlock holmes` | 96 | 6.97 GiB/s | **9.91 GiB/s** | 54.7 MiB/s | Rust |
| bword_the | `\bthe\b` | 5,426 | 3.17 GiB/s | **3.41 GiB/s** | 75.9 MiB/s | Rust |
| letters_uni | `\p{L}+` | 108,992 | 185.0 MiB/s | **209.3 MiB/s** | 26.6 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 253 | **19.00 GiB/s** | 3.03 GiB/s | 53.6 MiB/s | ezi_gex |
| cap_word | `\p{Lu}\p{Ll}+` | 9,451 | 507.1 MiB/s | **695.4 MiB/s** | 44.6 MiB/s | Rust |
| alpha_ascii | `[A-Za-z]+` | 109,000 | 195.2 MiB/s | **200.9 MiB/s** | 32.6 MiB/s | Rust |
| digits | `\d+` | 253 | **19.13 GiB/s** | 3.04 GiB/s | 82.3 MiB/s | ezi_gex |
| near | `Holmes.{0,30}Watson\|Watson.{0,30}Holmes` | 7 | 5.40 GiB/s | **7.47 GiB/s** | 56.7 MiB/s | Rust |
| the_word | `the\s+\p{L}+` | 5,404 | 769.3 MiB/s | **2.28 GiB/s** | 258.2 MiB/s | Rust |

### `subtitles-ru` (613,423 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| ci_ru | `(?i)что` | 1,285 | 4.49 GiB/s | **6.23 GiB/s** | 56.5 MiB/s | Rust |
| letters_uni | `\p{L}+` | 56,496 | 266.1 MiB/s | **290.8 MiB/s** | 45.1 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 303 | 1.38 GiB/s | **3.05 GiB/s** | 91.5 MiB/s | Rust |
| cap_word | `\p{Lu}\p{Ll}+` | 12,682 | 338.8 MiB/s | **548.9 MiB/s** | 67.0 MiB/s | Rust |
| script_cyrillic | `\p{Cyrillic}+` | 56,493 | 263.9 MiB/s | **289.8 MiB/s** | 51.9 MiB/s | Rust |

### `logs` (600,225 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| bword_the | `\bthe\b` | 260 | 27.66 GiB/s | **28.36 GiB/s** | 77.6 MiB/s | Rust |
| alpha_ascii | `[A-Za-z]+` | 67,976 | 367.8 MiB/s | **446.5 MiB/s** | 41.0 MiB/s | Rust |
| digits | `\d+` | 59,966 | **586.8 MiB/s** | 473.7 MiB/s | 47.1 MiB/s | ezi_gex |
| words_perl | `\w+` | 117,413 | 282.7 MiB/s | **347.6 MiB/s** | 29.3 MiB/s | Rust |
| word_boundary | `\b\w+\b` | 117,413 | 230.2 MiB/s | **398.2 MiB/s** | 25.6 MiB/s | Rust |
| ipv4 | `(?:\d{1,3}\.){3}\d{1,3}` | 3,153 | 426.7 MiB/s | **700.2 MiB/s** | 49.3 MiB/s | Rust |
| date_iso | `\d{4}-\d{2}-\d{2}` | 1,248 | **8.82 GiB/s** | 6.36 GiB/s | 60.1 MiB/s | ezi_gex |
| email | `[\w.+-]+@[\w-]+\.[\w.-]+` | 1,248 | 4.42 GiB/s | **6.80 GiB/s** | 42.8 MiB/s | Rust |
| uri | `https?://[^\s"]+` | 2,902 | 1.96 GiB/s | **2.19 GiB/s** | 262.0 MiB/s | Rust |
| log_line | `(?m)^(\S+) \S+ \S+ \[([^\]]+)\] "(\w+)…` | 1,905 | 979.1 MiB/s | **1.30 GiB/s** | 69.6 MiB/s | Rust |

### `subtitles-zh` (613,427 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| letters_uni | `\p{L}+` | 46,847 | 299.2 MiB/s | **376.7 MiB/s** | 54.9 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 6,811 | 839.6 MiB/s | **1.01 GiB/s** | 95.0 MiB/s | Rust |
| script_han | `\p{Han}+` | 26,657 | 397.1 MiB/s | **447.0 MiB/s** | 77.1 MiB/s | Rust |

## Compile time (median — lower is better)

Time to build the matcher object from the pattern string (engine construction; for ezi_gex this includes the eager-DFA determinization). Corpus-independent.

| pattern | regex | ezi_gex | Rust | Go |
|---|---|---|---|---|
| lit_sherlock | `Sherlock` | 792 ns | 1.71 µs | 500 ns |
| lit_the | `the` | 709 ns | 1.17 µs | 333 ns |
| lit_phrase | `Sherlock Holmes` | 1.00 µs | 2.12 µs | 667 ns |
| alt_names | `Sherlock\|Holmes\|Watson\|Mycroft\|Lestrad…` | 1.62 µs | 20.92 µs | 1.83 µs |
| ci_the | `(?i)the` | 26.17 µs | 14.12 µs | 333 ns |
| ci_phrase | `(?i)sherlock holmes` | 137.75 µs | 62.29 µs | 625 ns |
| ci_ru | `(?i)что` | 32.17 µs | 32.42 µs | 375 ns |
| bword_the | `\bthe\b` | 3.50 µs | 5.75 µs | 417 ns |
| letters_uni | `\p{L}+` | 621.25 µs | 118.79 µs | 2.67 µs |
| numbers_uni | `\p{N}+` | 128.33 µs | 37.75 µs | 750 ns |
| cap_word | `\p{Lu}\p{Ll}+` | 568.29 µs | 149.04 µs | 4.71 µs |
| alpha_ascii | `[A-Za-z]+` | 2.42 µs | 3.71 µs | 250 ns |
| digits | `\d+` | 43.46 µs | 24.54 µs | 209 ns |
| words_perl | `\w+` | 847.69 µs | 133.75 µs | 250 ns |
| word_boundary | `\b\w+\b` | 1.23 ms | 174.42 µs | 417 ns |
| script_cyrillic | `\p{Cyrillic}+` | 13.58 µs | 16.71 µs | 333 ns |
| script_han | `\p{Han}+` | 33.67 µs | 21.42 µs | 375 ns |
| near | `Holmes.{0,30}Watson\|Watson.{0,30}Holmes` | 229.00 µs | 126.54 µs | 5.33 µs |
| the_word | `the\s+\p{L}+` | 583.83 µs | 122.29 µs | 3.08 µs |
| ipv4 | `(?:\d{1,3}\.){3}\d{1,3}` | 595.21 µs | 148.33 µs | 1.12 µs |
| date_iso | `\d{4}-\d{2}-\d{2}` | 421.92 µs | 128.38 µs | 833 ns |
| email | `[\w.+-]+@[\w-]+\.[\w.-]+` | 832.96 µs | 464.79 µs | 958 ns |
| uri | `https?://[^\s"]+` | 29.67 µs | 20.21 µs | 750 ns |
| log_line | `(?m)^(\S+) \S+ \S+ \[([^\]]+)\] "(\w+)…` | 1.13 ms | 279.71 µs | 2.38 µs |

## Summary

Search speed relative to **ezi_gex** (geometric mean over all shared cells; `>1.0` means the engine is faster than ezi_gex, `<1.0` means slower):

| engine | geomean speed vs ezi_gex | cells fastest |
|---|--:|--:|
| ezi_gex | 1.00× | 6 / 32 |
| Rust | 1.10× | 26 / 32 |
| Go | 0.05× | 0 / 32 |

> Throughput drifts run-to-run with thermal/background load; read these as directional, not to 3 sig figs. The match-count cross-check above is exact.

