#!/usr/bin/env python3
"""Rebuild names.json and index.html from the raw VLKK dataset.

Usage:
    python build.py path/to/vardai.jsonl   rebuild the dataset, then the page
    python build.py                        rebuild only the page from names.json
    python build.py --check                verify index.html matches template.html

The raw file is the newline-delimited JSON export of "Vardų lingvistiniai
duomenys" (dataset 2664) from https://data.gov.lt — one JSON object per
registered name entry. It is not committed here; download it yourself. Editing
template.html needs no raw data: run the script with no argument to re-inline
the committed names.json into index.html.

Output:
    names.json   compact dataset (one row per distinct given name)
    index.html   self-contained page with that dataset inlined
"""
import collections
import json
import pathlib
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent
GENDER = {"Moteris": 1, "Vyras": 2}
VERDICT = {"Teiktinas": 1, "Vengtinas": 2, "Neteiktinas": 3}
GROUP = {"Baltiška kilmė": 1, "Svetima kilmė": 2}


def load(raw_path):
    """Split multi-name entries into distinct given names.

    Entries with vardu_sk == 1 are single names and carry the full catalogue
    data. Entries with 2-4 names are combinations; any name appearing only
    inside a combination has no catalogue data of its own, so its gender is
    inferred from the combinations it appears in.
    """
    singles, tokens = {}, collections.Counter()
    combo_gender = collections.defaultdict(collections.Counter)

    with open(raw_path, encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            full = (rec.get("pilnas_vardas") or "").strip()
            if not full:
                continue
            parts = full.split()
            for part in parts:
                tokens[part] += 1
                if rec.get("lytis"):
                    combo_gender[part][rec["lytis"]] += 1
            if rec.get("vardu_sk") == 1 and len(parts) == 1:
                singles[full] = rec
    return singles, tokens, combo_gender


def build_rows(singles, tokens, combo_gender):
    subgroups, subsections = set(), set()
    for rec in singles.values():
        for i in range(1, 6):
            for field, bucket in (("kilmes_pogrupis", subgroups),
                                  ("kilmes_poskyris", subsections)):
                value = rec.get(f"{field}_{i}")
                if value:
                    bucket.add(value)
    subgroups, subsections = sorted(subgroups), sorted(subsections)
    sub_i = {v: i for i, v in enumerate(subgroups)}
    sec_i = {v: i for i, v in enumerate(subsections)}

    rows = []
    for name in sorted(tokens, key=lambda s: unicodedata.normalize("NFKD", s.lower())):
        rec = singles.get(name)
        if rec is None:
            counts = combo_gender.get(name)
            gender = GENDER.get(counts.most_common(1)[0][0], 0) if counts else 0
            rows.append([name, gender, 0, 0, [], [], [], 0, 0])
            continue

        groups, subs, secs = set(), set(), set()
        for i in range(1, 6):
            value = rec.get(f"kilmes_grupe_{i}")
            if value in GROUP:
                groups.add(GROUP[value])
            value = rec.get(f"kilmes_pogrupis_{i}")
            if value:
                subs.add(sub_i[value])
            value = rec.get(f"kilmes_poskyris_{i}")
            if value:
                secs.add(sec_i[value])

        rows.append([
            name,
            GENDER.get(rec.get("lytis"), 0),
            VERDICT.get(rec.get("normiskumas"), 0),
            1 if rec.get("ar_sventojo_vardas") else 0,
            sorted(groups),
            sorted(subs),
            sorted(secs),
            rec.get("paiesku_sk") or 0,
            1,
        ])
    return {"pogr": subgroups, "posk": subsections, "rows": rows}


def render(payload, count):
    """Inline the dataset into template.html and return the finished page."""
    template = (ROOT / "template.html").read_text(encoding="utf-8")
    page = template.replace("of 8,954 names", f"of {count:,} names")
    return page.replace("/*__DATA__*/", payload.replace("</", "<\\/"))


def emit(payload, count):
    (ROOT / "index.html").write_text(render(payload, count), encoding="utf-8")


def main():
    if len(sys.argv) > 2:
        sys.exit(__doc__)

    names_json = ROOT / "names.json"
    if len(sys.argv) == 2 and sys.argv[1] == "--check":
        payload = names_json.read_text(encoding="utf-8")
        count = len(json.loads(payload)["rows"])
        if render(payload, count) != (ROOT / "index.html").read_text(encoding="utf-8"):
            sys.exit("index.html is stale — run: python build.py")
        print("index.html matches template.html")
        return

    if len(sys.argv) == 2:
        dataset = build_rows(*load(sys.argv[1]))
        payload = json.dumps(dataset, ensure_ascii=False, separators=(",", ":"))
        names_json.write_text(payload, encoding="utf-8")
        count = len(dataset["rows"])
        emit(payload, count)
        print(f"{count:,} names -> names.json, index.html")
        return

    payload = names_json.read_text(encoding="utf-8")
    count = len(json.loads(payload)["rows"])
    emit(payload, count)
    print(f"{count:,} names -> index.html")


if __name__ == "__main__":
    main()
