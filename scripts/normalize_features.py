#!/usr/bin/env python3
"""Normalise `provides_features` onto the controlled vocabulary (capabilities.yaml).

    python scripts/normalize_features.py            # DRY RUN — report only
    python scripts/normalize_features.py --apply    # rewrite the notes

Why: measured on the live corpus — 1136 distinct feature slugs across 654 candidates,
95.6% of them used by exactly ONE candidate, and the most-shared ones were brand names
(`browserbase-api-wrapper`, `stagehand-sdk`). Set-cover matches provides_features against
a target's needs_features, so with no shared vocabulary it can never match anything: the
parts-bin has never actually worked.

This maps existing slugs onto controlled terms and PRESERVES the originals in
`provides_specifics`, so nuance is never lost. Writes are opt-in; unmapped slugs are
reported, never silently dropped.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from oss_config import ROOT, get_capabilities  # noqa: E402

REPOS = ROOT / "knowledge" / "repos"
MAX_TERMS_PER_SLUG = 3


def build_table(caps: dict[str, list[str]]) -> list[tuple[str, str]]:
    """-> [(needle, term)] sorted most-specific-first."""
    rows = []
    for term, aliases in caps.items():
        for n in {term, *(aliases or [])}:
            rows.append((n.lower().replace("_", "-"), term))
    rows.sort(key=lambda r: -len(r[0]))
    return rows


def match(slug: str, table: list[tuple[str, str]]) -> list[str]:
    """Match on whole hyphen-delimited tokens, so 'ci' can't match 'efficiency'."""
    s = "-" + slug.lower().replace("_", "-").strip("-") + "-"
    hits: list[str] = []
    for needle, term in table:
        if f"-{needle}-" in s and term not in hits:
            hits.append(term)
            if len(hits) >= MAX_TERMS_PER_SLUG:
                break
    return hits


def read_features(text: str) -> tuple[int, int, list[str]]:
    """-> (start_line, end_line, slugs) for the provides_features block, or (-1,-1,[])."""
    lines = text.split("\n")
    for i, l in enumerate(lines):
        if l.startswith("provides_features:"):
            inline = l.split(":", 1)[1].strip()
            if inline.startswith("[") and inline.endswith("]"):
                inner = inline[1:-1].strip()
                return i, i + 1, [x.strip() for x in inner.split(",") if x.strip()]
            j, slugs = i + 1, []
            while j < len(lines) and lines[j].startswith("  - "):
                slugs.append(lines[j][4:].split("#")[0].strip())
                j += 1
            return i, j, slugs
    return -1, -1, []


def rewrite(text: str, terms: list[str], originals: list[str]) -> str | None:
    i, j, _ = read_features(text)
    if i < 0:
        return None
    lines = text.split("\n")
    block = ["provides_features:        # controlled vocabulary — see capabilities.yaml"]
    block += [f"  - {t}" for t in terms] if terms else ["  []"]
    if originals:
        block.append("provides_specifics:      # free-text nuance the coarse terms lose")
        block += [f"  - {o}" for o in originals]
    return "\n".join(lines[:i] + block + lines[j:])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="rewrite notes (default: dry run)")
    args = ap.parse_args()

    caps = get_capabilities()
    if not caps:
        raise SystemExit("! capabilities.yaml has no `capabilities:` map")
    table = build_table(caps)

    notes = [p for p in sorted(REPOS.glob("*.md")) if not p.stem.startswith("_")]
    unmapped: Counter = Counter()
    per_term: Counter = Counter()
    touched = skipped = no_fm = 0

    for p in notes:
        text = p.read_text(encoding="utf-8", errors="replace")
        i, j, slugs = read_features(text)
        if i < 0:
            no_fm += 1
            continue
        if not slugs:
            skipped += 1
            continue
        terms: list[str] = []
        for s in slugs:
            hits = match(s, table)
            if not hits:
                unmapped[s] += 1
            for h in hits:
                if h not in terms:
                    terms.append(h)
        for t in terms:
            per_term[t] += 1
        if args.apply:
            new = rewrite(text, sorted(terms), slugs)
            if new:
                p.write_text(new, encoding="utf-8")
        touched += 1

    total_slugs = sum(per_term.values())
    print(f"notes with features : {touched}   (no front-matter: {no_fm}, empty: {skipped})")
    print(f"controlled terms hit: {len(per_term)} / {len(caps)}")
    print(f"unmapped slugs      : {len(unmapped)} distinct")
    print()
    print("=== coverage: candidates per controlled term (set-cover can match these) ===")
    for t, c in per_term.most_common(22):
        print(f"  {c:4d}  {t}")
    print()
    print("=== top UNMAPPED slugs (propose new terms, or accept as specifics-only) ===")
    for s, c in unmapped.most_common(18):
        print(f"  {c:4d}  {s}")
    print()
    print("APPLIED — notes rewritten." if args.apply else "DRY RUN — nothing written. Re-run with --apply.")


if __name__ == "__main__":
    main()
