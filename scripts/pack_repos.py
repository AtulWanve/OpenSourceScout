#!/usr/bin/env python3
"""OpenSourceScout PACK stage — clone each repo once, store a compressed, commit-pinned pack.

    python scripts/pack_repos.py --limit 20         # pack 20 unpacked notes
    python scripts/pack_repos.py --owner AppFlowy-IO # only that account
    python scripts/pack_repos.py --dry-run           # list what would be packed

The middle stage of `fetch -> pack -> judge`. Packing is NOT optional: the corpus is meant to
be READY TO USE, so every repo carries its source snapshot from the moment it enters. Regen is
not a fallback — the repo can change or vanish, and a fresh clone can't reproduce the commit a
verdict was judged against. So we pack once, permanently, pinned to the exact SHA (see scout.pack).

Independent + resumable like the other stages: a note that already has a pack file is skipped, so
a rate-limited or interrupted run just resumes. Cloning is network-bound; there is no LLM here.

Zero third-party dependencies — stdlib only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scout  # noqa: E402  — reuse the packer + paths (no LLM, no network beyond git)
from build_index import parse_fm  # noqa: E402

REPOS = scout.REPOS
PACKS = scout.PACKS


def _set_key(head: str, key: str, value: str) -> str:
    """Replace a top-level `key: ...` line in the front-matter, preserving its comment."""
    pat = re.compile(rf"^({re.escape(key)}:)([^\n#]*)(#[^\n]*)?$", re.M)
    if pat.search(head):
        return pat.sub(lambda m: f"{m.group(1)} {value}" + (f"  {m.group(3)}" if m.group(3) else ""),
                       head, count=1)
    return head


def has_pack(slug: str) -> bool:
    return (PACKS / f"{slug}.md.gz").exists() or (PACKS / f"{slug}.md").exists()


def target_filters(args) -> tuple[str | None, str | None]:
    """-> (exact_slug, owner_prefix) from an optional positional target or --owner."""
    tgt = re.sub(r"\.git$", "", re.sub(r"^https?://(www\.)?github\.com/", "",
                 (getattr(args, "target", None) or "")).strip("/"))
    if tgt and "/" in tgt:
        return tgt.replace("/", "__"), None
    return None, (tgt or args.owner)


def select(args) -> list[tuple[Path, str, str]]:
    """-> [(note_path, owner, name)] for notes that still need a pack."""
    exact, owner = target_filters(args)
    out = []
    for p in sorted(REPOS.glob("*.md")):
        if p.stem.startswith("_"):
            continue
        if exact and p.stem != exact:
            continue
        if owner and not p.stem.startswith(f"{owner}__"):
            continue
        if not args.force and has_pack(p.stem):
            continue
        fm = parse_fm(p.read_text(encoding="utf-8", errors="replace"))
        cand = fm.get("candidate") or ""
        if fm.get("type") == "idea" or "/" not in cand:       # ideas have no repo to clone
            continue
        repo_owner, _, name = cand.partition("/")
        out.append((p, repo_owner, name))
    return out[: args.limit] if args.limit else out


def record_pack(path: Path, rel_pack: str, sha: str) -> None:
    """Write the pack path + pinned SHA into the note's FACTS — never touches the verdict."""
    text = path.read_text(encoding="utf-8", errors="replace")
    fm_end = text.find("\n---", text.find("---") + 3)
    if fm_end == -1:
        return
    fm, body = text[:fm_end], text[fm_end:]
    fm = _set_key(fm, "pack", f'"{rel_pack}"')
    if re.search(r"^packed_sha:", fm, re.M):
        fm = _set_key(fm, "packed_sha", sha or "null")
    else:                                                 # old-schema note: no packed_sha line yet
        fm = re.sub(r"^(pack:[^\n]*)$", rf"\1\npacked_sha: {sha or 'null'}",
                    fm, count=1, flags=re.M)
    path.write_text(fm + body, encoding="utf-8")


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description="Pack unpacked notes (fetch -> PACK -> judge).")
    ap.add_argument("target", nargs="?", help="owner/repo (one) or owner (account); omit for whole corpus")
    ap.add_argument("--owner", help="only notes for this account (slug prefix)")
    ap.add_argument("--limit", type=int, default=0, metavar="N", help="at most N repos this run")
    ap.add_argument("--force", action="store_true", help="re-pack even if a pack exists")
    ap.add_argument("--dry-run", action="store_true", help="list what would be packed")
    args = ap.parse_args()

    todo = select(args)
    if not todo:
        sys.exit("Nothing to pack — every selected note already has a pack.")
    print(f"{len(todo)} repo(s) to pack.")

    if args.dry_run:
        for _, owner, name in todo:
            print(f"  would pack {owner}/{name}")
        return

    packed = failed = 0
    for i, (path, owner, name) in enumerate(todo, 1):
        print(f"[{i}/{len(todo)}] {owner}/{name}")
        result = scout.pack(owner, name)
        if not result:
            failed += 1
            continue
        pack_path, sha = result
        record_pack(path, pack_path.relative_to(scout.ROOT).as_posix(), sha)
        packed += 1

    tail = " Re-run to resume; packs persist." if failed else "."
    print(f"\n{packed} packed, {failed} failed{tail}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\n! interrupted — packs already written are kept; re-run to resume.")
