# Regex engine benchmark — ezi_gex vs Rust `regex` vs Go `regexp`

A like-for-like, three-way throughput + compile-time comparison on **real**, byte-identical haystacks and real-world patterns. Modelled on [rebar](https://github.com/BurntSushi/rebar).

## Environment

- **When:** 2026-06-21 10:30 UTC
- **CPU:** Apple M4
- **OS:** Darwin 25.5.0
- **ezi_gex:** git 016372a0540a (Zig 0.17.0-dev.931+84f84267c, ReleaseFast)
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
| lit_sherlock | `Sherlock` | 97 | **40.30 GiB/s** | 38.77 GiB/s | 18.09 GiB/s | ezi_gex |
| lit_the | `the` | 7,218 | **7.10 GiB/s** | 6.70 GiB/s | 482.2 MiB/s | ezi_gex |
| lit_phrase | `Sherlock Holmes` | 91 | **41.04 GiB/s** | 39.23 GiB/s | 14.60 GiB/s | ezi_gex |
| alt_names | `Sherlock\|Holmes\|Watson\|Mycroft\|Lestrad…` | 677 | 7.37 GiB/s | **7.90 GiB/s** | 20.0 MiB/s | Rust |
| ci_the | `(?i)the` | 7,987 | 1.54 GiB/s | **2.02 GiB/s** | 64.2 MiB/s | Rust |
| ci_phrase | `(?i)sherlock holmes` | 96 | 7.60 GiB/s | **9.90 GiB/s** | 53.4 MiB/s | Rust |
| bword_the | `\bthe\b` | 5,426 | 3.17 GiB/s | **3.20 GiB/s** | 74.5 MiB/s | Rust |
| letters_uni | `\p{L}+` | 108,992 | 183.7 MiB/s | **204.6 MiB/s** | 26.6 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 253 | **25.52 GiB/s** | 3.04 GiB/s | 53.6 MiB/s | ezi_gex |
| cap_word | `\p{Lu}\p{Ll}+` | 9,451 | **905.4 MiB/s** | 680.3 MiB/s | 43.5 MiB/s | ezi_gex |
| alpha_ascii | `[A-Za-z]+` | 109,000 | **184.6 MiB/s** | 173.9 MiB/s | 32.2 MiB/s | ezi_gex |
| digits | `\d+` | 253 | **25.38 GiB/s** | 3.01 GiB/s | 80.1 MiB/s | ezi_gex |
| near | `Holmes.{0,30}Watson\|Watson.{0,30}Holmes` | 7 | 5.28 GiB/s | **7.47 GiB/s** | 54.3 MiB/s | Rust |
| the_word | `the\s+\p{L}+` | 5,404 | 2.19 GiB/s | **2.22 GiB/s** | 264.2 MiB/s | Rust |

### `subtitles-ru` (613,423 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| ci_ru | `(?i)что` | 1,285 | 4.28 GiB/s | **6.28 GiB/s** | 55.8 MiB/s | Rust |
| letters_uni | `\p{L}+` | 56,496 | 262.7 MiB/s | **288.3 MiB/s** | 44.6 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 303 | 2.00 GiB/s | **3.04 GiB/s** | 92.3 MiB/s | Rust |
| cap_word | `\p{Lu}\p{Ll}+` | 12,682 | 303.3 MiB/s | **562.5 MiB/s** | 67.4 MiB/s | Rust |
| script_cyrillic | `\p{Cyrillic}+` | 56,493 | 252.0 MiB/s | **289.3 MiB/s** | 51.6 MiB/s | Rust |

### `logs` (600,225 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| bword_the | `\bthe\b` | 260 | 27.05 GiB/s | **28.30 GiB/s** | 76.7 MiB/s | Rust |
| alpha_ascii | `[A-Za-z]+` | 67,976 | 331.5 MiB/s | **377.9 MiB/s** | 40.8 MiB/s | Rust |
| digits | `\d+` | 59,966 | **526.1 MiB/s** | 455.6 MiB/s | 47.4 MiB/s | ezi_gex |
| words_perl | `\w+` | 117,413 | 265.0 MiB/s | **339.8 MiB/s** | 29.5 MiB/s | Rust |
| word_boundary | `\b\w+\b` | 117,413 | 227.5 MiB/s | **388.6 MiB/s** | 25.4 MiB/s | Rust |
| ipv4 | `(?:\d{1,3}\.){3}\d{1,3}` | 3,153 | 387.0 MiB/s | **698.9 MiB/s** | 48.7 MiB/s | Rust |
| date_iso | `\d{4}-\d{2}-\d{2}` | 1,248 | **9.27 GiB/s** | 6.28 GiB/s | 58.9 MiB/s | ezi_gex |
| email | `[\w.+-]+@[\w-]+\.[\w.-]+` | 1,248 | **9.09 GiB/s** | 6.78 GiB/s | 44.2 MiB/s | ezi_gex |
| uri | `https?://[^\s"]+` | 2,902 | 1.96 GiB/s | **2.13 GiB/s** | 267.4 MiB/s | Rust |
| log_line | `(?m)^(\S+) \S+ \S+ \[([^\]]+)\] "(\w+)…` | 1,905 | 1013.5 MiB/s | **1.30 GiB/s** | 71.0 MiB/s | Rust |

### `subtitles-zh` (613,427 bytes)

| pattern | regex | matches | ezi_gex | Rust | Go | fastest |
|---|---|---|---|---|---|---|
| letters_uni | `\p{L}+` | 46,847 | 292.2 MiB/s | **372.1 MiB/s** | 55.4 MiB/s | Rust |
| numbers_uni | `\p{N}+` | 6,811 | 771.2 MiB/s | **1023.2 MiB/s** | 95.6 MiB/s | Rust |
| script_han | `\p{Han}+` | 26,657 | 376.6 MiB/s | **446.7 MiB/s** | 78.2 MiB/s | Rust |

## Compile time (median — lower is better)

Time to build the matcher object from the pattern string (engine construction; for ezi_gex this includes the eager-DFA determinization). Corpus-independent.

| pattern | regex | ezi_gex | Rust | Go |
|---|---|---|---|---|
| lit_sherlock | `Sherlock` | 834 ns | 1.62 µs | 500 ns |
| lit_the | `the` | 750 ns | 1.12 µs | 333 ns |
| lit_phrase | `Sherlock Holmes` | 1.00 µs | 2.12 µs | 667 ns |
| alt_names | `Sherlock\|Holmes\|Watson\|Mycroft\|Lestrad…` | 1.67 µs | 20.71 µs | 1.83 µs |
| ci_the | `(?i)the` | 27.25 µs | 14.00 µs | 333 ns |
| ci_phrase | `(?i)sherlock holmes` | 149.83 µs | 61.75 µs | 625 ns |
| ci_ru | `(?i)что` | 36.21 µs | 32.50 µs | 375 ns |
| bword_the | `\bthe\b` | 4.33 µs | 5.67 µs | 416 ns |
| letters_uni | `\p{L}+` | 930.42 µs | 120.54 µs | 2.75 µs |
| numbers_uni | `\p{N}+` | 205.67 µs | 37.96 µs | 750 ns |
| cap_word | `\p{Lu}\p{Ll}+` | 733.25 µs | 151.29 µs | 4.75 µs |
| alpha_ascii | `[A-Za-z]+` | 2.58 µs | 3.62 µs | 250 ns |
| digits | `\d+` | 63.21 µs | 25.08 µs | 209 ns |
| words_perl | `\w+` | 1.21 ms | 135.38 µs | 250 ns |
| word_boundary | `\b\w+\b` | 1.62 ms | 175.50 µs | 417 ns |
| script_cyrillic | `\p{Cyrillic}+` | 22.67 µs | 16.83 µs | 333 ns |
| script_han | `\p{Han}+` | 52.54 µs | 21.62 µs | 375 ns |
| near | `Holmes.{0,30}Watson\|Watson.{0,30}Holmes` | 239.08 µs | 126.29 µs | 5.25 µs |
| the_word | `the\s+\p{L}+` | 569.21 µs | 121.79 µs | 3.04 µs |
| ipv4 | `(?:\d{1,3}\.){3}\d{1,3}` | 777.04 µs | 148.79 µs | 1.08 µs |
| date_iso | `\d{4}-\d{2}-\d{2}` | 576.79 µs | 128.38 µs | 833 ns |
| email | `[\w.+-]+@[\w-]+\.[\w.-]+` | 779.88 µs | 480.77 µs | 958 ns |
| uri | `https?://[^\s"]+` | 44.62 µs | 20.75 µs | 750 ns |
| log_line | `(?m)^(\S+) \S+ \S+ \[([^\]]+)\] "(\w+)…` | 1.08 ms | 278.96 µs | 2.42 µs |

## Summary

Search speed relative to **ezi_gex** (geometric mean over all shared cells; `>1.0` means the engine is faster than ezi_gex, `<1.0` means slower):

| engine | geomean speed vs ezi_gex | cells fastest |
|---|--:|--:|
| ezi_gex | 1.00× | 10 / 32 |
| Rust | 0.99× | 22 / 32 |
| Go | 0.05× | 0 / 32 |

> Throughput drifts run-to-run with thermal/background load; read these as directional, not to 3 sig figs. The match-count cross-check above is exact.

