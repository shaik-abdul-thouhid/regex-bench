# Regex engine benchmark — ezi_gex vs Rust `regex` vs Go `regexp`

A like-for-like, three-way throughput + compile-time comparison on **real**, byte-identical haystacks and real-world patterns. Modelled on [rebar](https://github.com/BurntSushi/rebar).

## Environment

- **When:** 2026-06-15 19:40 UTC
- **CPU:** Apple M4
- **OS:** Darwin 25.5.0
- **ezi_gex:** git 0c92160c477c (Zig 0.17.0-dev.857+2b2b85c5f, ReleaseFast)
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
| lit_sherlock | `Sherlock` | 97 | **40.30 GiB/s** | 38.54 GiB/s | 18.32 GiB/s | ezi_gex |
| lit_the | `the` | 7,218 | **6.23 GiB/s** | 5.97 GiB/s | 489.5 MiB/s | ezi_gex |
| lit_phrase | `Sherlock Holmes` | 91 | **40.79 GiB/s** | 39.46 GiB/s | 14.84 GiB/s | ezi_gex |
| alt_names | `Sherlock\|Holmes\|Watson\|Mycroft\|Lestrad…` | 677 | 6.89 GiB/s | **7.90 GiB/s** | 20.5 MiB/s | Rust |
| ci_the | `(?i)the` | 7,987 | 1.69 GiB/s | **1.99 GiB/s** | 61.2 MiB/s | Rust |
| ci_phrase | `(?i)sherlock holmes` | 96 | 6.91 GiB/s | **9.95 GiB/s** | 53.6 MiB/s | Rust |
| bword_the | `\bthe\b` | 5,426 | **3.33 GiB/s** | 3.15 GiB/s | 74.7 MiB/s | ezi_gex |
| letters_uni | `\p{L}+` | 108,992 | 190.1 MiB/s | **205.7 MiB/s** | 26.6 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 253 | **18.89 GiB/s** | 3.04 GiB/s | 53.9 MiB/s | ezi_gex |
| cap_word | `\p{Lu}\p{Ll}+` | 9,451 | 411.2 MiB/s | **632.8 MiB/s** | 44.2 MiB/s | Rust |
| alpha_ascii | `[A-Za-z]+` | 109,000 | 183.0 MiB/s | **208.9 MiB/s** | 32.6 MiB/s | Rust |
| digits | `\d+` | 253 | **18.81 GiB/s** | 3.03 GiB/s | 79.7 MiB/s | ezi_gex |
| near | `Holmes.{0,30}Watson\|Watson.{0,30}Holmes` | 7 | 5.41 GiB/s | **7.47 GiB/s** | 53.1 MiB/s | Rust |
| the_word | `the\s+\p{L}+` | 5,404 | 854.3 MiB/s | **2.05 GiB/s** | 266.9 MiB/s | Rust |

### `subtitles-ru` (613,423 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| ci_ru | `(?i)что` | 1,285 | 4.05 GiB/s | **6.30 GiB/s** | 57.4 MiB/s | Rust |
| letters_uni | `\p{L}+` | 56,496 | 265.1 MiB/s | **286.6 MiB/s** | 45.0 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 303 | 1.22 GiB/s | **3.05 GiB/s** | 92.6 MiB/s | Rust |
| cap_word | `\p{Lu}\p{Ll}+` | 12,682 | 334.8 MiB/s | **540.9 MiB/s** | 68.1 MiB/s | Rust |
| script_cyrillic | `\p{Cyrillic}+` | 56,493 | 265.7 MiB/s | **288.9 MiB/s** | 51.8 MiB/s | Rust |

### `logs` (600,225 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| bword_the | `\bthe\b` | 260 | 25.03 GiB/s | **25.95 GiB/s** | 77.5 MiB/s | Rust |
| alpha_ascii | `[A-Za-z]+` | 67,976 | 324.6 MiB/s | **447.7 MiB/s** | 41.3 MiB/s | Rust |
| digits | `\d+` | 59,966 | **591.4 MiB/s** | 474.1 MiB/s | 46.9 MiB/s | ezi_gex |
| words_perl | `\w+` | 117,413 | 280.0 MiB/s | **344.3 MiB/s** | 29.0 MiB/s | Rust |
| word_boundary | `\b\w+\b` | 117,413 | 224.0 MiB/s | **397.7 MiB/s** | 25.2 MiB/s | Rust |
| ipv4 | `(?:\d{1,3}\.){3}\d{1,3}` | 3,153 | 418.4 MiB/s | **698.6 MiB/s** | 49.8 MiB/s | Rust |
| date_iso | `\d{4}-\d{2}-\d{2}` | 1,248 | **8.07 GiB/s** | 5.87 GiB/s | 59.4 MiB/s | ezi_gex |
| email | `[\w.+-]+@[\w-]+\.[\w.-]+` | 1,248 | 4.39 GiB/s | **7.02 GiB/s** | 44.8 MiB/s | Rust |
| uri | `https?://[^\s"]+` | 2,902 | 1.97 GiB/s | **2.20 GiB/s** | 265.9 MiB/s | Rust |
| log_line | `(?m)^(\S+) \S+ \S+ \[([^\]]+)\] "(\w+)…` | 1,905 | 984.3 MiB/s | **1.30 GiB/s** | 69.2 MiB/s | Rust |

### `subtitles-zh` (613,427 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| letters_uni | `\p{L}+` | 46,847 | 293.9 MiB/s | **377.2 MiB/s** | 55.9 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 6,811 | 672.5 MiB/s | **1.00 GiB/s** | 96.5 MiB/s | Rust |
| script_han | `\p{Han}+` | 26,657 | 388.6 MiB/s | **446.3 MiB/s** | 78.1 MiB/s | Rust |

## Compile time (median — lower is better)

Time to build the matcher object from the pattern string (engine construction; for ezi_gex this includes the eager-DFA determinization). Corpus-independent.

| pattern | regex | ezi_gex | Rust | Go |
|---|---|---|---|---|
| lit_sherlock | `Sherlock` | 833 ns | 1.25 µs | 500 ns |
| lit_the | `the` | 625 ns | 875 ns | 333 ns |
| lit_phrase | `Sherlock Holmes` | 958 ns | 1.67 µs | 667 ns |
| alt_names | `Sherlock\|Holmes\|Watson\|Mycroft\|Lestrad…` | 1.50 µs | 19.21 µs | 1.75 µs |
| ci_the | `(?i)the` | 26.29 µs | 13.00 µs | 292 ns |
| ci_phrase | `(?i)sherlock holmes` | 137.42 µs | 56.83 µs | 625 ns |
| ci_ru | `(?i)что` | 32.79 µs | 30.04 µs | 375 ns |
| bword_the | `\bthe\b` | 3.12 µs | 5.00 µs | 416 ns |
| letters_uni | `\p{L}+` | 31.94 ms | 107.83 µs | 2.62 µs |
| numbers_uni | `\p{N}+` | 956.42 µs | 34.25 µs | 750 ns |
| cap_word | `\p{Lu}\p{Ll}+` | 10.11 ms | 135.71 µs | 4.67 µs |
| alpha_ascii | `[A-Za-z]+` | 2.21 µs | 3.12 µs | 250 ns |
| digits | `\d+` | 98.71 µs | 22.58 µs | 209 ns |
| words_perl | `\w+` | 45.15 ms | 121.08 µs | 250 ns |
| word_boundary | `\b\w+\b` | 47.58 ms | 161.67 µs | 417 ns |
| script_cyrillic | `\p{Cyrillic}+` | 20.67 µs | 15.79 µs | 333 ns |
| script_han | `\p{Han}+` | 156.42 µs | 20.00 µs | 375 ns |
| near | `Holmes.{0,30}Watson\|Watson.{0,30}Holmes` | 127.50 µs | 111.21 µs | 5.29 µs |
| the_word | `the\s+\p{L}+` | 107.43 ms | 109.92 µs | 3.08 µs |
| ipv4 | `(?:\d{1,3}\.){3}\d{1,3}` | 1.06 ms | 127.04 µs | 1.08 µs |
| date_iso | `\d{4}-\d{2}-\d{2}` | 701.50 µs | 112.71 µs | 833 ns |
| email | `[\w.+-]+@[\w-]+\.[\w.-]+` | 6.37 ms | 423.50 µs | 958 ns |
| uri | `https?://[^\s"]+` | 54.42 µs | 18.62 µs | 750 ns |
| log_line | `(?m)^(\S+) \S+ \S+ \[([^\]]+)\] "(\w+)…` | 47.58 ms | 252.46 µs | 2.38 µs |

## Summary

Search speed relative to **ezi_gex** (geometric mean over all shared cells; `>1.0` means the engine is faster than ezi_gex, `<1.0` means slower):

| engine | geomean speed vs ezi_gex | cells fastest |
|---|--:|--:|
| ezi_gex | 1.00× | 8 / 32 |
| Rust | 1.12× | 24 / 32 |
| Go | 0.05× | 0 / 32 |

> Throughput drifts run-to-run with thermal/background load; read these as directional, not to 3 sig figs. The match-count cross-check above is exact.

