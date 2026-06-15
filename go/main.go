// Go runner for the three-engine regex benchmark.
//
// Implements the SAME measurement protocol as the Rust and Zig runners (see
// README.md): compile once, warm up, then collect per-iteration search timings
// until both a minimum sample count and a minimum wall-clock are reached (capped
// by a maximum), reporting median / min / p90. Compile time is measured
// separately. Results are written as TSV to <root>/results/go.tsv.
//
// Operation: count all non-overlapping leftmost matches over the whole haystack.
// Go's stdlib regexp has no allocation-free counting iterator, so the count
// materializes match positions via FindAllIndex — a real, unavoidable cost of
// Go's API, reported honestly.
package main

import (
	"fmt"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

type cfg struct {
	warmup                                       int
	sMinSamples, cMinSamples                     int
	sMinMs, sMaxMs, cMinMs, cMaxMs               int64
}

func envInt(name string, def int) int {
	if v := os.Getenv(name); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}

func loadCfg() cfg {
	return cfg{
		warmup:      envInt("RB_WARMUP", 5),
		sMinSamples: envInt("RB_SEARCH_MIN_SAMPLES", 40),
		sMinMs:      int64(envInt("RB_SEARCH_MIN_MS", 600)),
		sMaxMs:      int64(envInt("RB_SEARCH_MAX_MS", 3000)),
		cMinSamples: envInt("RB_COMPILE_MIN_SAMPLES", 50),
		cMinMs:      int64(envInt("RB_COMPILE_MIN_MS", 300)),
		cMaxMs:      int64(envInt("RB_COMPILE_MAX_MS", 2000)),
	}
}

type benchCase struct {
	name    string
	corpora []string
	pattern string // already resolved to the Go-specific pattern
}

func parseCases(text string) []benchCase {
	var out []benchCase
	for _, raw := range strings.Split(text, "\n") {
		line := strings.TrimRight(raw, " \r\t")
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		f := strings.Split(line, "\t")
		if len(f) < 3 {
			continue
		}
		pat := f[2]
		for _, ov := range f[3:] { // engine:pattern overrides
			if strings.HasPrefix(ov, "go:") {
				pat = ov[len("go:"):]
			}
		}
		out = append(out, benchCase{
			name:    f[0],
			corpora: strings.Split(f[1], ","),
			pattern: pat,
		})
	}
	return out
}

// count all non-overlapping leftmost matches over the full haystack.
func countMatches(re *regexp.Regexp, text []byte) int {
	return len(re.FindAllIndex(text, -1))
}

func median(s []int64) int64 {
	n := len(s)
	if n == 0 {
		return 0
	}
	if n%2 == 1 {
		return s[n/2]
	}
	return (s[n/2-1] + s[n/2]) / 2
}

func percentile(s []int64, p float64) int64 {
	if len(s) == 0 {
		return 0
	}
	idx := int(p * float64(len(s)-1))
	return s[idx]
}

var sink int // defeat dead-code elimination

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: go-runner <bench-root>")
		os.Exit(2)
	}
	root := os.Args[1]
	c := loadCfg()

	casesRaw, err := os.ReadFile(root + "/cases.tsv")
	if err != nil {
		fmt.Fprintln(os.Stderr, "read cases.tsv:", err)
		os.Exit(1)
	}
	cases := parseCases(string(casesRaw))

	corpusCache := map[string][]byte{}
	loadCorpus := func(name string) ([]byte, bool) {
		if b, ok := corpusCache[name]; ok {
			return b, b != nil
		}
		b, err := os.ReadFile(root + "/corpus/" + name + ".txt")
		if err != nil {
			fmt.Fprintf(os.Stderr, "  WARN: corpus %s unavailable: %v\n", name, err)
			corpusCache[name] = nil
			return nil, false
		}
		corpusCache[name] = b
		return b, true
	}

	var out strings.Builder
	out.WriteString("engine\tcase\tcorpus\tcorpus_bytes\tmatches\tsearch_samples\tsearch_min_ns\tsearch_median_ns\tsearch_p90_ns\tcompile_samples\tcompile_min_ns\tcompile_median_ns\n")

	for _, bc := range cases {
		// ── compile-time measurement (per case) ──
		if _, e := regexp.Compile(bc.pattern); e != nil {
			fmt.Fprintf(os.Stderr, "  go: skip /%s/ (compile error: %v)\n", bc.name, e)
			continue
		}
		var cSamples []int64
		cStart := time.Now()
		for {
			t0 := time.Now()
			re, _ := regexp.Compile(bc.pattern)
			d := time.Since(t0).Nanoseconds()
			sink += re.NumSubexp()
			cSamples = append(cSamples, d)
			el := time.Since(cStart).Milliseconds()
			if len(cSamples) >= c.cMinSamples && el >= c.cMinMs {
				break
			}
			if el >= c.cMaxMs {
				break
			}
		}
		sort.Slice(cSamples, func(i, j int) bool { return cSamples[i] < cSamples[j] })
		cMin, cMed := cSamples[0], median(cSamples)

		re := regexp.MustCompile(bc.pattern)

		for _, corpus := range bc.corpora {
			text, ok := loadCorpus(corpus)
			if !ok {
				continue
			}
			for i := 0; i < c.warmup; i++ {
				sink += countMatches(re, text)
			}
			ref := countMatches(re, text)

			var sSamples []int64
			sStart := time.Now()
			for {
				t0 := time.Now()
				m := countMatches(re, text)
				d := time.Since(t0).Nanoseconds()
				sink += m
				if m != ref {
					fmt.Fprintf(os.Stderr, "  go: UNSTABLE count %s/%s: %d vs %d\n", bc.name, corpus, m, ref)
				}
				sSamples = append(sSamples, d)
				el := time.Since(sStart).Milliseconds()
				if len(sSamples) >= c.sMinSamples && el >= c.sMinMs {
					break
				}
				if el >= c.sMaxMs {
					break
				}
			}
			sort.Slice(sSamples, func(i, j int) bool { return sSamples[i] < sSamples[j] })

			out.WriteString(fmt.Sprintf("go\t%s\t%s\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\t%d\n",
				bc.name, corpus, len(text), ref,
				len(sSamples), sSamples[0], median(sSamples), percentile(sSamples, 0.90),
				len(cSamples), cMin, cMed))
			fmt.Fprintf(os.Stderr, "  go  %-16s %-14s matches=%-8d median=%s\n",
				bc.name, corpus, ref, humanNs(median(sSamples)))
		}
	}

	if err := os.WriteFile(root+"/results/go.tsv", []byte(out.String()), 0o644); err != nil {
		fmt.Fprintln(os.Stderr, "write results:", err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "go: wrote %s/results/go.tsv (sink=%d)\n", root, sink)
}

func humanNs(ns int64) string {
	f := float64(ns)
	switch {
	case f < 1e3:
		return fmt.Sprintf("%.0f ns", f)
	case f < 1e6:
		return fmt.Sprintf("%.2f us", f/1e3)
	case f < 1e9:
		return fmt.Sprintf("%.2f ms", f/1e6)
	default:
		return fmt.Sprintf("%.2f s", f/1e9)
	}
}
