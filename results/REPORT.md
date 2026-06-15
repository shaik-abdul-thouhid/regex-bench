# Regex engine benchmark — ezi_gex vs Rust `regex` vs Go `regexp`

A like-for-like, three-way throughput + compile-time comparison on **real**, byte-identical haystacks and real-world patterns. Modelled on [rebar](https://github.com/BurntSushi/rebar).

## Environment

- **When:** 2026-06-15 11:11 UTC
- **CPU:** Apple M4
- **OS:** Darwin 25.5.0
- **ezi_gex:** git 881f99459007 (Zig 0.17.0-dev.857+2b2b85c5f, ReleaseFast)
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
| lit_sherlock | `Sherlock` | 97 | **41.04 GiB/s** | 34.27 GiB/s | 18.34 GiB/s | ezi_gex |
| lit_the | `the` | 7,218 | **7.57 GiB/s** | 6.18 GiB/s | 489.8 MiB/s | ezi_gex |
| lit_phrase | `Sherlock Holmes` | 91 | **41.55 GiB/s** | 39.23 GiB/s | 14.63 GiB/s | ezi_gex |
| alt_names | `Sherlock\|Holmes\|Watson\|Mycroft\|Lestrad…` | 677 | 7.58 GiB/s | **7.88 GiB/s** | 20.4 MiB/s | Rust |
| ci_the | `(?i)the` | 7,987 | 1.73 GiB/s | **2.07 GiB/s** | 60.9 MiB/s | Rust |
| ci_phrase | `(?i)sherlock holmes` | 96 | 6.73 GiB/s | **9.59 GiB/s** | 53.3 MiB/s | Rust |
| bword_the | `\bthe\b` | 5,426 | 484.8 MiB/s | **3.48 GiB/s** | 75.3 MiB/s | Rust |
| letters_uni | `\p{L}+` | 108,992 | 200.3 MiB/s | **205.7 MiB/s** | 27.2 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 253 | **19.00 GiB/s** | 2.97 GiB/s | 53.7 MiB/s | ezi_gex |
| cap_word | `\p{Lu}\p{Ll}+` | 9,451 | **454.0 MiB/s** | 431.2 MiB/s | 42.1 MiB/s | ezi_gex |
| alpha_ascii | `[A-Za-z]+` | 109,000 | **201.9 MiB/s** | 193.3 MiB/s | 31.4 MiB/s | ezi_gex |
| digits | `\d+` | 253 | **18.89 GiB/s** | 3.03 GiB/s | 79.2 MiB/s | ezi_gex |
| near | `Holmes.{0,30}Watson\|Watson.{0,30}Holmes` | 7 | 5.31 GiB/s | **7.44 GiB/s** | 57.1 MiB/s | Rust |
| the_word | `the\s+\p{L}+` | 5,404 | 815.9 MiB/s | **2.15 GiB/s** | 266.9 MiB/s | Rust |

### `subtitles-ru` (613,423 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| ci_ru | `(?i)что` | 1,285 | 4.39 GiB/s | **6.14 GiB/s** | 50.0 MiB/s | Rust |
| letters_uni | `\p{L}+` | 56,496 | 279.8 MiB/s | **289.1 MiB/s** | 45.0 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 303 | 1.25 GiB/s | **3.03 GiB/s** | 90.7 MiB/s | Rust |
| cap_word | `\p{Lu}\p{Ll}+` | 12,682 | 318.5 MiB/s | **431.0 MiB/s** | 62.9 MiB/s | Rust |
| script_cyrillic | `\p{Cyrillic}+` | 56,493 | 266.8 MiB/s | **290.6 MiB/s** | 52.0 MiB/s | Rust |

### `logs` (600,225 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| bword_the | `\bthe\b` | 260 | 25.22 GiB/s | **28.42 GiB/s** | 79.1 MiB/s | Rust |
| alpha_ascii | `[A-Za-z]+` | 67,976 | 374.9 MiB/s | **446.7 MiB/s** | 40.9 MiB/s | Rust |
| digits | `\d+` | 59,966 | **643.5 MiB/s** | 464.9 MiB/s | 46.5 MiB/s | ezi_gex |
| words_perl | `\w+` | 117,413 | 280.4 MiB/s | **346.7 MiB/s** | 29.1 MiB/s | Rust |
| word_boundary | `\b\w+\b` | 117,413 | 261.7 MiB/s | **391.5 MiB/s** | 25.4 MiB/s | Rust |
| ipv4 | `(?:\d{1,3}\.){3}\d{1,3}` | 3,153 | 350.6 MiB/s | **677.8 MiB/s** | 49.7 MiB/s | Rust |
| date_iso | `\d{4}-\d{2}-\d{2}` | 1,248 | 530.9 MiB/s | **6.26 GiB/s** | 59.2 MiB/s | Rust |
| email | `[\w.+-]+@[\w-]+\.[\w.-]+` | 1,248 | 4.52 GiB/s | **7.05 GiB/s** | 45.5 MiB/s | Rust |
| uri | `https?://[^\s"]+` | 2,902 | 1.99 GiB/s | **2.20 GiB/s** | 267.5 MiB/s | Rust |
| log_line | `(?m)^(\S+) \S+ \S+ \[([^\]]+)\] "(\w+)…` | 1,905 | 217.0 MiB/s | **1.30 GiB/s** | 69.2 MiB/s | Rust |

### `subtitles-zh` (613,427 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| letters_uni | `\p{L}+` | 46,847 | 307.6 MiB/s | **364.5 MiB/s** | 56.0 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 6,811 | 763.7 MiB/s | **872.9 MiB/s** | 91.9 MiB/s | Rust |
| script_han | `\p{Han}+` | 26,657 | 386.7 MiB/s | **441.1 MiB/s** | 77.8 MiB/s | Rust |

## Compile time (median — lower is better)

Time to build the matcher object from the pattern string (engine construction; for ezi_gex this includes the eager-DFA determinization). Corpus-independent.

| pattern | regex | ezi_gex | Rust | Go |
|---|---|---|---|---|
| lit_sherlock | `Sherlock` | 792 ns | 1.33 µs | 500 ns |
| lit_the | `the` | 584 ns | 2.08 µs | 333 ns |
| lit_phrase | `Sherlock Holmes` | 917 ns | 1.75 µs | 667 ns |
| alt_names | `Sherlock\|Holmes\|Watson\|Mycroft\|Lestrad…` | 1.54 µs | 19.33 µs | 1.79 µs |
| ci_the | `(?i)the` | 26.21 µs | 13.29 µs | 292 ns |
| ci_phrase | `(?i)sherlock holmes` | 137.25 µs | 59.33 µs | 625 ns |
| ci_ru | `(?i)что` | 31.88 µs | 31.38 µs | 375 ns |
| bword_the | `\bthe\b` | 3.04 µs | 5.08 µs | 417 ns |
| letters_uni | `\p{L}+` | 32.01 ms | 107.62 µs | 2.71 µs |
| numbers_uni | `\p{N}+` | 989.21 µs | 35.46 µs | 750 ns |
| cap_word | `\p{Lu}\p{Ll}+` | 10.06 ms | 203.35 µs | 5.08 µs |
| alpha_ascii | `[A-Za-z]+` | 2.08 µs | 3.21 µs | 250 ns |
| digits | `\d+` | 97.54 µs | 22.79 µs | 209 ns |
| words_perl | `\w+` | 45.36 ms | 121.08 µs | 250 ns |
| word_boundary | `\b\w+\b` | 47.38 ms | 163.96 µs | 417 ns |
| script_cyrillic | `\p{Cyrillic}+` | 19.83 µs | 15.62 µs | 333 ns |
| script_han | `\p{Han}+` | 157.88 µs | 20.17 µs | 375 ns |
| near | `Holmes.{0,30}Watson\|Watson.{0,30}Holmes` | 13.60 ms | 112.08 µs | 5.29 µs |
| the_word | `the\s+\p{L}+` | 111.34 ms | 110.42 µs | 3.12 µs |
| ipv4 | `(?:\d{1,3}\.){3}\d{1,3}` | 1.07 ms | 127.25 µs | 1.12 µs |
| date_iso | `\d{4}-\d{2}-\d{2}` | 697.42 µs | 112.00 µs | 834 ns |
| email | `[\w.+-]+@[\w-]+\.[\w.-]+` | 891.00 ms | 420.38 µs | 1.00 µs |
| uri | `https?://[^\s"]+` | 54.17 µs | 18.88 µs | 750 ns |
| log_line | `(?m)^(\S+) \S+ \S+ \[([^\]]+)\] "(\w+)…` | 47.95 ms | 255.54 µs | 2.42 µs |

## Summary

Search speed relative to **ezi_gex** (geometric mean over all shared cells; `>1.0` means the engine is faster than ezi_gex, `<1.0` means slower):

| engine | geomean speed vs ezi_gex | cells fastest |
|---|--:|--:|
| ezi_gex | 1.00× | 8 / 32 |
| Rust | 1.28× | 24 / 32 |
| Go | 0.06× | 0 / 32 |

> Throughput drifts run-to-run with thermal/background load; read these as directional, not to 3 sig figs. The match-count cross-check above is exact.

