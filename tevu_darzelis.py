#!/usr/bin/env python3
"""Map register names to their pages on tevu-darzelis.lt.

Usage:
    python tevu_darzelis.py                  crawl the site's A-Z name index, then map
    python tevu_darzelis.py --index FILE     map from a saved crawl instead of crawling
    python tevu_darzelis.py stats [MINUTES] [--out FILE]
                                             fetch births per year for mapped names

tevu-darzelis.lt addresses a name by its accent-free spelling, but when several
names fold to the same spelling the numbering (/ruta/, /ruta1/, /adelaide-1/)
follows the order the site added them, which can't be derived from the name.
Many register names have no page there at all. So the addresses are read from
the site's own alphabetical index rather than guessed.

The crawl honours the site's robots.txt crawl delay of 10 seconds, so a full
run over ~350 index pages takes about an hour. The raw crawl is saved to
tevu_darzelis_index.json (not committed) so the mapping can be redone offline.

Output, tevu_darzelis.json, which build.py inlines into index.html:
    fetched   date of the crawl
    slug      {name: address} for names whose address isn't their folded spelling
    absent    names with no page on the site
Every other register name lives at /vaiku-vardai/<folded spelling>/.

The stats command reads each mapped name's page for the chart the site draws
from Population Register figures: births per year from 1999, the site's trend
figure for the current year, and the name's yearly rank. It keeps the same
10-second pace, so all ~5,600 pages take about 16 hours; it resumes where it
left off, can stop itself after MINUTES, and fetches the most popular names
first. Output, tevu_darzelis_stats.json unless --out names another file:
    years     the chart's years
    names     {name: [births per year up to the last year, trend for the last
              year, ranks per year]}, or 0 when the
              site shows no births at all (fewer than 5 a year are not shown)
"""
import collections
import datetime
import html
import json
import pathlib
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
BASE = "https://www.tevu-darzelis.lt/vaiku-vardai/"
LETTERS = "ABCDEFGHIJKLMNOPRSTUVZ"
DELAY = 10  # robots.txt Crawl-delay
UA = {"User-Agent": "lietuviski_vardai link map (github.com/AivarasAukselis/lietuviski_vardai)"}
ROW = re.compile(r'<li><a (class="pink")?\s*href="/vaiku-vardai/([^/"]+)/">([^<]+)</a></li>')


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if not 0x300 <= ord(c) <= 0x36F).lower()


def fetch(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except OSError as e:
            print(f"  {e}; retrying", file=sys.stderr)
            time.sleep(DELAY * 2 ** (attempt + 1))
    sys.exit(f"giving up on {url}")


def crawl():
    """Return {slug: [name, 'f'|'m']} in the site's order (most popular first per letter)."""
    index = {}
    for letter in LETTERS:
        page, last = 1, 1
        while page <= last:
            text = fetch(f"{BASE}{letter}/?letter={letter}&page={page}")
            pages = re.findall(rf"letter={letter}&(?:amp;)?page=(\d+)", text)
            last = max([last, *map(int, pages)])
            for pink, slug, name in ROW.findall(text):
                index.setdefault(slug.strip(), [html.unescape(name).strip(), "f" if pink else "m"])
            print(f"{letter} {page}/{last}  {len(index):,} names", file=sys.stderr)
            page += 1
            time.sleep(DELAY)
    return index


def build(index, rows):
    by_name = collections.defaultdict(list)
    for slug, (name, sex) in index.items():
        by_name[name].append((slug.strip(), sex))  # the index has a stray "jorita "
    slug, absent = {}, []
    for row in rows:
        name, gender = row[0], {1: "f", 2: "m"}.get(row[1])
        found = by_name.get(name)
        if not found:
            absent.append(name)
            continue
        # A name listed twice is usually one boy's and one girl's entry.
        best = next((s for s, sex in found if sex == gender), found[0][0])
        if best != fold(name):
            slug[name] = best
    return {"fetched": datetime.date.today().isoformat(), "slug": slug, "absent": absent}


def page_stats(text):
    """Pull the chart series out of a name page: years, births, trend, ranks."""
    years = json.loads(re.search(r"categories: (\[[^\]]*\])", text).group(1))
    births, trend = (json.loads(d) for d in re.findall(r"data: (\[[^\]]*\])", text)[:2])
    tops = json.loads(re.search(r"var tops = (\{.*?\});", text).group(1))
    ranks = [int(tops[y]) if tops.get(y) else None for y in years]
    return years, births, trend[-1], ranks


def stats(minutes, out_path):
    stop = time.time() + minutes * 60 if minutes else None
    rows = json.loads((ROOT / "names.json").read_text(encoding="utf-8"))["rows"]
    links = json.loads((ROOT / "tevu_darzelis.json").read_text(encoding="utf-8"))
    absent = set(links["absent"])
    slug = {r[0]: links["slug"].get(r[0], fold(r[0])) for r in rows if r[0] not in absent}
    # Most popular first: the site's index lists each letter by popularity.
    raw = ROOT / "tevu_darzelis_index.json"
    rank = {}
    if raw.exists():
        per_letter = collections.Counter()
        for s, (name, _) in json.loads(raw.read_text(encoding="utf-8")).items():
            per_letter[s[:1]] += 1
            rank.setdefault(name, per_letter[s[:1]])
    order = sorted(slug, key=lambda n: (rank.get(n, 1e9), n))

    out = (json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists()
           else {"years": None, "names": {}})
    todo = [n for n in order if n not in out["names"]]
    print(f"{len(todo):,} of {len(order):,} names to fetch", file=sys.stderr)
    for i, name in enumerate(todo):
        if stop and time.time() > stop:
            break
        years, births, trend, ranks = page_stats(fetch(f"{BASE}{urllib.parse.quote(slug[name])}/"))
        if out["years"] is None:
            out["years"] = years
        elif years != out["years"]:
            sys.exit(f"{name}: chart years changed to {years[0]}-{years[-1]}; start a fresh file")
        births = births[:-1]  # the last year is only drawn as the trend
        out["names"][name] = [births, trend, ranks] if any(births) or trend else 0
        tmp = out_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        tmp.replace(out_path)
        if i % 50 == 0:
            print(f"{len(out['names']):,}/{len(order):,}  {name}", file=sys.stderr)
        time.sleep(DELAY)
    print(f"{len(out['names']):,} of {len(order):,} names -> {out_path.name}")


def main():
    args = sys.argv[1:]
    if args[:1] == ["stats"]:
        out_path = ROOT / "tevu_darzelis_stats.json"
        if "--out" in args:
            i = args.index("--out")
            out_path = pathlib.Path(args[i + 1])
            args = args[:i] + args[i + 2:]
        if len(args) > 2:
            sys.exit(__doc__)
        return stats(float(args[1]) if len(args) == 2 else 0, out_path)
    raw = ROOT / "tevu_darzelis_index.json"
    if args[:1] == ["--index"] and len(args) == 2:
        index = json.loads(pathlib.Path(args[1]).read_text(encoding="utf-8"))
    elif not args:
        index = crawl()
        raw.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    else:
        sys.exit(__doc__)
    rows = json.loads((ROOT / "names.json").read_text(encoding="utf-8"))["rows"]
    out = build(index, rows)
    (ROOT / "tevu_darzelis.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(rows) - len(out['absent']):,} of {len(rows):,} names have a page; "
          f"{len(out['slug'])} at a numbered address -> tevu_darzelis.json")


if __name__ == "__main__":
    main()
