#!/usr/bin/env python3
"""Corpus provisioning for the three-engine regex benchmark.

Two kinds of haystack live under ./corpus/:

  REAL (downloaded once, byte-identical to BurntSushi/rebar — the reference
  cross-engine regex benchmark):
    - sherlock.txt        Project Gutenberg "The Adventures of Sherlock Holmes"
                          (594,933 B, English prose, effectively ASCII).
    - subtitles-ru.txt    OpenSubtitles Russian sample (Cyrillic, 86% non-ASCII).
    - subtitles-zh.txt    OpenSubtitles Chinese sample (Han, 76% non-ASCII).

  GENERATED (deterministic, pure ASCII — for the data-extraction patterns the
  prose corpora do not contain):
    - logs.txt            Realistic server logs: a mix of nginx-combined access
                          lines and application logfmt lines, carrying IPv4
                          addresses, ISO-8601 dates, emails and URLs.

All four are read byte-for-byte by every engine, so the comparison is
apples-to-apples. Run from anywhere:  python3 corpus.py
"""
import os
import sys
import random

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "corpus")

REBAR = "https://raw.githubusercontent.com/BurntSushi/rebar/master/benchmarks/haystacks"
DOWNLOADS = {
    "sherlock.txt": f"{REBAR}/sherlock.txt",
    "subtitles-ru.txt": f"{REBAR}/opensubtitles/ru-huge.txt",
    "subtitles-zh.txt": f"{REBAR}/opensubtitles/zh-huge.txt",
}

LOGS_CAP = 600_000  # bytes, comparable to the prose corpora


def ensure_downloads():
    """Fetch the real rebar haystacks if missing. Never re-download."""
    import urllib.request
    missing = []
    for name, url in DOWNLOADS.items():
        path = os.path.join(CORPUS, name)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        try:
            print(f"  downloading {name} ...", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "regex-bench/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            with open(path, "wb") as f:
                f.write(data)
            print(f"  wrote {name} ({len(data)} bytes)")
        except Exception as e:  # noqa: BLE001
            print(f"  WARNING: could not fetch {name}: {e}", file=sys.stderr)
            missing.append(name)
    return missing


# ─────────────────────────── logs.txt generator ────────────────────────────

IPS_OCTETS = lambda rng: f"{rng.randint(1,223)}.{rng.randint(0,255)}.{rng.randint(0,255)}.{rng.randint(1,254)}"  # noqa: E731
METHODS = ["GET", "GET", "GET", "GET", "POST", "POST", "PUT", "DELETE", "HEAD"]
PATHS = [
    "/", "/index.html", "/about", "/contact", "/login", "/logout",
    "/api/v1/users", "/api/v1/orders", "/api/v1/products", "/api/v2/search",
    "/static/css/main.css", "/static/js/app.js", "/images/logo.png",
    "/blog/2023/regex-performance", "/docs/getting-started", "/favicon.ico",
    "/assets/fonts/inter.woff2", "/health", "/metrics", "/api/v1/cart/items",
]
STATUSES = [200, 200, 200, 200, 200, 301, 302, 304, 400, 401, 403, 404, 500, 502]
REFERERS = [
    "-", "-",
    "https://www.google.com/",
    "https://example.com/blog/2023/regex-performance",
    "https://news.ycombinator.com/item?id=38000000",
    "https://duckduckgo.com/?q=regex+benchmark",
    "http://localhost:8080/dashboard",
]
UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
    "curl/8.4.0",
    "python-requests/2.31.0",
    "Googlebot/2.1 (+http://www.google.com/bot.html)",
]
USERS = ["-", "-", "alice", "bob", "carol", "dave", "eve"]
LEVELS = ["INFO", "INFO", "INFO", "WARN", "ERROR", "DEBUG"]
SERVICES = ["api", "auth", "billing", "gateway", "worker", "scheduler"]
FIRST = ["alice", "bob", "carol", "dave", "eve", "frank", "grace", "heidi", "ivan", "judy"]
DOMAINS = ["example.com", "test.org", "mail.co", "corp.example.net", "users.example.io"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
EVENTS = [
    "request completed", "cache miss", "db query slow", "token refreshed",
    "payment processed", "user signed in", "rate limit hit", "job enqueued",
    "the quick brown fox jumps", "retry scheduled for the next window",
]


def clf_date(rng):
    return (f"{rng.randint(1,28):02d}/{rng.choice(MONTHS)}/{rng.randint(2020,2024)}:"
            f"{rng.randint(0,23):02d}:{rng.randint(0,59):02d}:{rng.randint(0,59):02d} +0000")


def iso_dt(rng):
    return (f"{rng.randint(2020,2024)}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}T"
            f"{rng.randint(0,23):02d}:{rng.randint(0,59):02d}:{rng.randint(0,59):02d}Z")


def nginx_line(rng):
    ip = IPS_OCTETS(rng)
    user = rng.choice(USERS)
    path = rng.choice(PATHS)
    if rng.random() < 0.3:
        path += f"?id={rng.randint(1,99999)}&ref={rng.choice(['home','email','ads'])}"
    return (f'{ip} - {user} [{clf_date(rng)}] '
            f'"{rng.choice(METHODS)} {path} HTTP/1.1" '
            f'{rng.choice(STATUSES)} {rng.randint(0, 65535)} '
            f'"{rng.choice(REFERERS)}" "{rng.choice(UAS)}"')


def app_line(rng):
    email = f"{rng.choice(FIRST)}{rng.randint(1,99)}@{rng.choice(DOMAINS)}"
    url = f"https://{rng.choice(DOMAINS)}/api/v{rng.randint(1,3)}/{rng.choice(['users','orders','items'])}/{rng.randint(1,9999)}"
    return (f"{iso_dt(rng)} {rng.choice(LEVELS)} service={rng.choice(SERVICES)} "
            f"user={email} ip={IPS_OCTETS(rng)} path={rng.choice(PATHS)} "
            f"status={rng.choice(STATUSES)} latency_ms={rng.randint(1,5000)} "
            f'url={url} msg="{rng.choice(EVENTS)}"')


def gen_logs(rng):
    out, n = [], 0
    while n < LOGS_CAP:
        line = nginx_line(rng) if rng.random() < 0.6 else app_line(rng)
        out.append(line)
        n += len(line) + 1
    return "\n".join(out) + "\n"


def main():
    os.makedirs(CORPUS, exist_ok=True)
    print("provisioning corpora ->", CORPUS)
    missing = ensure_downloads()

    rng = random.Random(0x108_5EED)
    data = gen_logs(rng).encode("ascii")  # ascii() raises if anything non-ASCII slips in
    with open(os.path.join(CORPUS, "logs.txt"), "wb") as f:
        f.write(data)
    print(f"  wrote logs.txt ({len(data)} bytes, generated)")

    print("\ncorpus inventory:")
    for name in ("sherlock.txt", "subtitles-ru.txt", "subtitles-zh.txt", "logs.txt"):
        p = os.path.join(CORPUS, name)
        sz = os.path.getsize(p) if os.path.exists(p) else 0
        print(f"  {sz:>10}  {name}" + ("" if sz else "   <-- MISSING"))
    if missing:
        print(f"\nERROR: {len(missing)} real corpora missing (no network?): {missing}",
              file=sys.stderr)
        print("The benchmark will skip cases that need them.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
