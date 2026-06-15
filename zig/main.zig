//! ezi_gex runner for the three-engine regex benchmark.
//!
//! Implements the SAME measurement protocol as the Go and Rust runners (see
//! README.md): compile once, warm up, then collect per-iteration search timings
//! until both a minimum sample count and a minimum wall-clock are reached (capped
//! by a maximum), reporting median / min / p90. Compile time is measured
//! separately. Results are written as TSV to <root>/results/zig.tsv.
//!
//! Operation: count all non-overlapping leftmost matches over the whole haystack
//! (`re.count(&scratch, haystack)` — allocation-free).
//!
//! I/O note: this toolchain (Zig 0.17.0-dev) keeps `Dir`/`File` under the
//! `std.Io` interface and hands `main` a `std.process.Init` carrying `gpa`/`io`.
//! Corpora are read at runtime via `io` (so the same files every engine reads),
//! and tuning knobs arrive as CLI args (run.sh forwards them) to avoid the env API.

const std = @import("std");
const builtin = @import("builtin");
const gex = @import("ezi_gex");

/// Monotonic nanoseconds (std.time.Timer is not used in this dev build).
fn monotonicNanos() u128 {
    switch (builtin.os.tag) {
        .linux => {
            var ts: std.os.linux.timespec = undefined;
            const rc = std.os.linux.clock_gettime(.MONOTONIC, &ts);
            std.debug.assert(rc == 0);
            const sec: u128 = @intCast(@max(ts.sec, 0));
            const nsec: u128 = @intCast(@max(ts.nsec, 0));
            return sec * std.time.ns_per_s + nsec;
        },
        .macos, .ios, .tvos, .watchos, .visionos, .maccatalyst => {
            var info: std.c.mach_timebase_info_data = undefined;
            _ = std.c.mach_timebase_info(&info);
            const ticks = std.c.mach_absolute_time();
            return @as(u128, ticks) * @as(u128, info.numer) / @as(u128, info.denom);
        },
        else => @compileError("add monotonicNanos() for this OS"),
    }
}

const Cfg = struct {
    warmup: usize = 5,
    s_min_samples: usize = 40,
    s_min_ms: u128 = 600,
    s_max_ms: u128 = 3000,
    c_min_samples: usize = 50,
    c_min_ms: u128 = 300,
    c_max_ms: u128 = 2000,
};

const SAMP_CAP: usize = 200_000;

fn median(s: []const u64) u64 {
    const n = s.len;
    if (n == 0) return 0;
    if (n % 2 == 1) return s[n / 2];
    return (s[n / 2 - 1] + s[n / 2]) / 2;
}

fn pct(s: []const u64, p: f64) u64 {
    if (s.len == 0) return 0;
    const idx: usize = @intFromFloat(p * @as(f64, @floatFromInt(s.len - 1)));
    return s[idx];
}

fn humanNs(ns: u64, buf: []u8) []const u8 {
    const f: f64 = @floatFromInt(ns);
    if (f < 1e3) return std.fmt.bufPrint(buf, "{d:.0} ns", .{f}) catch "?";
    if (f < 1e6) return std.fmt.bufPrint(buf, "{d:.2} us", .{f / 1e3}) catch "?";
    if (f < 1e9) return std.fmt.bufPrint(buf, "{d:.2} ms", .{f / 1e6}) catch "?";
    return std.fmt.bufPrint(buf, "{d:.2} s", .{f / 1e9}) catch "?";
}

const Cache = struct {
    names: [16][]const u8 = undefined,
    datas: [16]?[]u8 = undefined,
    n: usize = 0,

    fn get(self: *Cache, io: std.Io, gpa: std.mem.Allocator, root: []const u8, name: []const u8) ?[]const u8 {
        var i: usize = 0;
        while (i < self.n) : (i += 1) {
            if (std.mem.eql(u8, self.names[i], name)) return self.datas[i];
        }
        const path = std.fmt.allocPrint(gpa, "{s}/corpus/{s}.txt", .{ root, name }) catch return null;
        defer gpa.free(path);
        const data: ?[]u8 = std.Io.Dir.cwd().readFileAlloc(io, path, gpa, .unlimited) catch |e| blk: {
            std.debug.print("# WARN: corpus {s} unavailable: {t}\n", .{ name, e });
            break :blk null;
        };
        if (self.n < self.names.len) {
            self.names[self.n] = name;
            self.datas[self.n] = data;
            self.n += 1;
        }
        return data;
    }
};

fn parseArg(args: []const [:0]const u8, idx: usize, default: usize) usize {
    if (args.len <= idx) return default;
    return std.fmt.parseInt(usize, args[idx], 10) catch default;
}

pub fn main(init: std.process.Init) !void {
    const gpa = init.gpa;
    const io = init.io;
    const arena = init.arena.allocator();

    const args = try init.minimal.args.toSlice(arena);
    if (args.len < 2) {
        std.debug.print("usage: zig-runner <bench-root> [warmup s_min_samples s_min_ms s_max_ms c_min_samples c_min_ms c_max_ms]\n", .{});
        return;
    }
    const root = args[1];
    const cfg = Cfg{
        .warmup = parseArg(args, 2, 5),
        .s_min_samples = parseArg(args, 3, 40),
        .s_min_ms = parseArg(args, 4, 600),
        .s_max_ms = parseArg(args, 5, 3000),
        .c_min_samples = parseArg(args, 6, 50),
        .c_min_ms = parseArg(args, 7, 300),
        .c_max_ms = parseArg(args, 8, 2000),
    };

    const cases_path = try std.fmt.allocPrint(gpa, "{s}/cases.tsv", .{root});
    const cases_raw = try std.Io.Dir.cwd().readFileAlloc(io, cases_path, gpa, .unlimited);

    const samp = try gpa.alloc(u64, SAMP_CAP);
    defer gpa.free(samp);

    var out: std.ArrayList(u8) = .empty;
    defer out.deinit(gpa);
    try out.appendSlice(gpa, "engine\tcase\tcorpus\tcorpus_bytes\tmatches\tsearch_samples\tsearch_min_ns\tsearch_median_ns\tsearch_p90_ns\tcompile_samples\tcompile_min_ns\tcompile_median_ns\n");

    var cache: Cache = .{};

    var lines = std.mem.splitScalar(u8, cases_raw, '\n');
    while (lines.next()) |raw| {
        const line = std.mem.trimEnd(u8, raw, " \r\t");
        if (line.len == 0 or line[0] == '#') continue;

        var fields: [16][]const u8 = undefined;
        var nf: usize = 0;
        var fit = std.mem.splitScalar(u8, line, '\t');
        while (fit.next()) |f| {
            if (nf < fields.len) {
                fields[nf] = f;
                nf += 1;
            }
        }
        if (nf < 3) continue;

        const name = fields[0];
        const corpora = fields[1];
        var pat = fields[2];
        var k: usize = 3;
        while (k < nf) : (k += 1) {
            if (std.mem.startsWith(u8, fields[k], "ezi:")) pat = fields[k][4..];
        }

        // ── verify it compiles (skip case if not) ──
        {
            var d0: gex.Diagnostic = .{};
            var re0 = gex.compileRuntimeWith(gex.backends.auto, gpa, pat, &d0, .{}) catch {
                std.debug.print("# ezi: skip {s} (compile error)\n", .{name});
                continue;
            };
            re0.deinit();
        }

        // ── compile-time measurement (per case) ──
        var c_n: usize = 0;
        const c_start = monotonicNanos();
        while (true) {
            const t0 = monotonicNanos();
            var dc: gex.Diagnostic = .{};
            var re_c = gex.compileRuntimeWith(gex.backends.auto, gpa, pat, &dc, .{}) catch break;
            const dt: u64 = @intCast(monotonicNanos() - t0);
            re_c.deinit();
            if (c_n < SAMP_CAP) {
                samp[c_n] = dt;
                c_n += 1;
            }
            const el = monotonicNanos() - c_start;
            if ((c_n >= cfg.c_min_samples and el >= cfg.c_min_ms * std.time.ns_per_ms) or
                el >= cfg.c_max_ms * std.time.ns_per_ms or c_n >= SAMP_CAP) break;
        }
        std.mem.sort(u64, samp[0..c_n], {}, std.sort.asc(u64));
        const c_min = if (c_n > 0) samp[0] else 0;
        const c_med = median(samp[0..c_n]);

        // ── search: one compiled regex, reused across this case's corpora ──
        var diag: gex.Diagnostic = .{};
        var re = gex.compileRuntimeWith(gex.backends.auto, gpa, pat, &diag, .{}) catch continue;
        defer re.deinit();
        var sc = @TypeOf(re).Scratch.init(gpa, &re.program) catch continue;
        defer sc.deinit(gpa);

        var cit = std.mem.splitScalar(u8, corpora, ',');
        while (cit.next()) |corpus| {
            const data = cache.get(io, gpa, root, corpus) orelse continue;

            var w: usize = 0;
            while (w < cfg.warmup) : (w += 1) _ = re.count(&sc, data);
            const ref = re.count(&sc, data);

            var s_n: usize = 0;
            const s_start = monotonicNanos();
            while (true) {
                const t0 = monotonicNanos();
                const m = re.count(&sc, data);
                const dt: u64 = @intCast(monotonicNanos() - t0);
                if (m != ref) std.debug.print("# ezi: UNSTABLE count {s}/{s}: {d} vs {d}\n", .{ name, corpus, m, ref });
                if (s_n < SAMP_CAP) {
                    samp[s_n] = dt;
                    s_n += 1;
                }
                const el = monotonicNanos() - s_start;
                if ((s_n >= cfg.s_min_samples and el >= cfg.s_min_ms * std.time.ns_per_ms) or
                    el >= cfg.s_max_ms * std.time.ns_per_ms or s_n >= SAMP_CAP) break;
            }
            std.mem.sort(u64, samp[0..s_n], {}, std.sort.asc(u64));

            const row = try std.fmt.allocPrint(gpa, "ezi_gex\t{s}\t{s}\t{d}\t{d}\t{d}\t{d}\t{d}\t{d}\t{d}\t{d}\t{d}\n", .{
                name,    corpus,               data.len,                ref, s_n,
                samp[0], median(samp[0..s_n]), pct(samp[0..s_n], 0.90), c_n, c_min,
                c_med,
            });
            defer gpa.free(row);
            try out.appendSlice(gpa, row);

            var hb: [32]u8 = undefined;
            std.debug.print("  ezi  {s: <16} {s: <14} matches={d: <8} median={s}\n", .{ name, corpus, ref, humanNs(median(samp[0..s_n]), &hb) });
        }
    }

    const out_path = try std.fmt.allocPrint(gpa, "{s}/results/zig.tsv", .{root});
    try std.Io.Dir.cwd().writeFile(io, .{ .sub_path = out_path, .data = out.items });
    std.debug.print("ezi_gex: wrote {s}\n", .{out_path});
}
