//! Rust runner for the three-engine regex benchmark.
//!
//! Implements the SAME measurement protocol as the Go and Zig runners (see
//! README.md): compile once, warm up, then collect per-iteration search timings
//! until both a minimum sample count and a minimum wall-clock are reached (capped
//! by a maximum), reporting median / min / p90. Compile time is measured
//! separately. Results are written as TSV to <root>/results/rust.tsv.
//!
//! Operation: count all non-overlapping leftmost matches over the whole haystack
//! (`re.find_iter(text).count()` — allocation-free).

use std::env;
use std::fs;
use std::hint::black_box;
use std::time::Instant;

struct Cfg {
    warmup: usize,
    s_min_samples: usize,
    s_min_ms: u128,
    s_max_ms: u128,
    c_min_samples: usize,
    c_min_ms: u128,
    c_max_ms: u128,
}

fn env_usize(name: &str, def: usize) -> usize {
    env::var(name).ok().and_then(|v| v.parse().ok()).unwrap_or(def)
}

fn load_cfg() -> Cfg {
    Cfg {
        warmup: env_usize("RB_WARMUP", 5),
        s_min_samples: env_usize("RB_SEARCH_MIN_SAMPLES", 40),
        s_min_ms: env_usize("RB_SEARCH_MIN_MS", 600) as u128,
        s_max_ms: env_usize("RB_SEARCH_MAX_MS", 3000) as u128,
        c_min_samples: env_usize("RB_COMPILE_MIN_SAMPLES", 50),
        c_min_ms: env_usize("RB_COMPILE_MIN_MS", 300) as u128,
        c_max_ms: env_usize("RB_COMPILE_MAX_MS", 2000) as u128,
    }
}

struct Case {
    name: String,
    corpora: Vec<String>,
    pattern: String, // resolved to the Rust-specific pattern
}

fn parse_cases(text: &str) -> Vec<Case> {
    let mut out = Vec::new();
    for raw in text.lines() {
        let line = raw.trim_end();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let f: Vec<&str> = line.split('\t').collect();
        if f.len() < 3 {
            continue;
        }
        let mut pattern = f[2].to_string();
        for ov in &f[3..] {
            if let Some(rest) = ov.strip_prefix("rust:") {
                pattern = rest.to_string();
            }
        }
        out.push(Case {
            name: f[0].to_string(),
            corpora: f[1].split(',').map(|s| s.to_string()).collect(),
            pattern,
        });
    }
    out
}

fn median(s: &[u64]) -> u64 {
    let n = s.len();
    if n == 0 {
        return 0;
    }
    if n % 2 == 1 {
        s[n / 2]
    } else {
        (s[n / 2 - 1] + s[n / 2]) / 2
    }
}

fn percentile(s: &[u64], p: f64) -> u64 {
    if s.is_empty() {
        return 0;
    }
    s[(p * (s.len() - 1) as f64) as usize]
}

fn human_ns(ns: u64) -> String {
    let f = ns as f64;
    if f < 1e3 {
        format!("{f:.0} ns")
    } else if f < 1e6 {
        format!("{:.2} us", f / 1e3)
    } else if f < 1e9 {
        format!("{:.2} ms", f / 1e6)
    } else {
        format!("{:.2} s", f / 1e9)
    }
}

fn main() {
    let root = match env::args().nth(1) {
        Some(r) => r,
        None => {
            eprintln!("usage: rust-runner <bench-root>");
            std::process::exit(2);
        }
    };
    let cfg = load_cfg();

    let cases_raw = fs::read_to_string(format!("{root}/cases.tsv")).expect("read cases.tsv");
    let cases = parse_cases(&cases_raw);

    let mut corpus_cache: std::collections::HashMap<String, Option<String>> =
        std::collections::HashMap::new();

    let mut out = String::new();
    out.push_str("engine\tcase\tcorpus\tcorpus_bytes\tmatches\tsearch_samples\tsearch_min_ns\tsearch_median_ns\tsearch_p90_ns\tcompile_samples\tcompile_min_ns\tcompile_median_ns\n");

    for bc in &cases {
        // ── compile-time measurement (per case) ──
        if regex::Regex::new(&bc.pattern).is_err() {
            eprintln!("  rust: skip /{}/ (compile error)", bc.name);
            continue;
        }
        let mut c_samples: Vec<u64> = Vec::new();
        let c_start = Instant::now();
        loop {
            let t0 = Instant::now();
            let re = regex::Regex::new(&bc.pattern).unwrap();
            let d = t0.elapsed().as_nanos() as u64;
            black_box(&re);
            c_samples.push(d);
            let el = c_start.elapsed().as_millis();
            if (c_samples.len() >= cfg.c_min_samples && el >= cfg.c_min_ms) || el >= cfg.c_max_ms {
                break;
            }
        }
        c_samples.sort_unstable();
        let (c_min, c_med) = (c_samples[0], median(&c_samples));

        let re = regex::Regex::new(&bc.pattern).unwrap();

        for corpus in &bc.corpora {
            let entry = corpus_cache.entry(corpus.clone()).or_insert_with(|| {
                match fs::read_to_string(format!("{root}/corpus/{corpus}.txt")) {
                    Ok(s) => Some(s),
                    Err(e) => {
                        eprintln!("  WARN: corpus {corpus} unavailable: {e}");
                        None
                    }
                }
            });
            let text = match entry {
                Some(t) => t.as_str(),
                None => continue,
            };

            for _ in 0..cfg.warmup {
                black_box(re.find_iter(text).count());
            }
            let reference = re.find_iter(text).count();

            let mut s_samples: Vec<u64> = Vec::new();
            let s_start = Instant::now();
            loop {
                let t0 = Instant::now();
                let m = re.find_iter(text).count();
                let d = t0.elapsed().as_nanos() as u64;
                black_box(m);
                if m != reference {
                    eprintln!("  rust: UNSTABLE count {}/{}: {} vs {}", bc.name, corpus, m, reference);
                }
                s_samples.push(d);
                let el = s_start.elapsed().as_millis();
                if (s_samples.len() >= cfg.s_min_samples && el >= cfg.s_min_ms) || el >= cfg.s_max_ms {
                    break;
                }
            }
            s_samples.sort_unstable();

            out.push_str(&format!(
                "rust\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n",
                bc.name,
                corpus,
                text.len(),
                reference,
                s_samples.len(),
                s_samples[0],
                median(&s_samples),
                percentile(&s_samples, 0.90),
                c_samples.len(),
                c_min,
                c_med,
            ));
            eprintln!(
                "  rust {:<16} {:<14} matches={:<8} median={}",
                bc.name,
                corpus,
                reference,
                human_ns(median(&s_samples))
            );
        }
    }

    fs::write(format!("{root}/results/rust.tsv"), out).expect("write results");
    eprintln!("rust: wrote {root}/results/rust.tsv");
}
