#!/usr/bin/env python3
"""Generate the human+AI navigable indexes from note front-matter.

    python scripts/build_index.py

Reads every knowledge/repos/*.md and emits three Obsidian-native maps-of-content:

    knowledge/INDEX.md            the hub — counts + every ACTIONABLE candidate
    knowledge/INDEX-inventory.md  the rejected parts-bin, grouped by category
    knowledge/INDEX-features.md   provides_features -> candidates (the set-cover index)

Notes stay FLAT and keep `disposition` in front-matter (a candidate's route can change,
so we never shuffle files between folders). Navigation comes from these generated maps.
Plain markdown + [[wikilinks]] + tags => renders in Obsidian, greppable by an agent.

Zero third-party dependencies — stdlib only.
"""
from __future__ import annotations

import datetime as dt
import re
import os
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import concurrent.futures

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oss_config

ROOT = Path(__file__).resolve().parents[1]
REPOS = ROOT / "knowledge" / "repos"
KNOW = ROOT / "knowledge"
TARGETS = KNOW / "targets"
TODAY = dt.date.today().isoformat()


class _ActionableDispositions(Sequence):
    """Dynamic container delegating to oss_config.get_dispositions() excluding rejected."""

    def _items(self) -> list[str]:
        return [d for d in oss_config.get_dispositions() if d != "rejected"]

    def __iter__(self):
        return iter(self._items())

    def __contains__(self, item: object) -> bool:
        return item in self._items()

    def __len__(self) -> int:
        return len(self._items())

    def __getitem__(self, index):
        return self._items()[index]

    def __add__(self, other):
        if isinstance(other, list):
            return self._items() + other
        if hasattr(other, "__iter__"):
            return self._items() + list(other)
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, list):
            return other + self._items()
        if hasattr(other, "__iter__"):
            return list(other) + self._items()
        return NotImplemented

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (list, tuple, _ActionableDispositions)):
            return self._items() == list(other)
        return False

    def __repr__(self) -> str:
        return repr(self._items())


ACTIONABLE = _ActionableDispositions()

def actionable_order() -> list[str]:
    """Configured ACTIONABLE dispositions, in config order."""
    return list(ACTIONABLE)


@dataclass(slots=True)
class NoteMeta:
    _slug: str
    _verdict: str
    disposition: str | None
    category: str | None
    license: str | dict | None
    status: str | None
    stars: str | int | None
    language: str | None
    pushed_at: str | None
    intake: str | None
    provides_features: list[str] | None

    @classmethod
    def from_dict(cls, data: dict) -> NoteMeta:
        return cls(
            _slug=data.get("_slug", ""),
            _verdict=data.get("_verdict", ""),
            disposition=data.get("disposition"),
            category=data.get("category"),
            license=data.get("license"),
            status=data.get("status"),
            stars=data.get("stars"),
            language=data.get("language"),
            pushed_at=data.get("pushed_at"),
            intake=data.get("intake"),
            provides_features=data.get("provides_features"),
        )


# ---------------------------------------------------------------- tiny yaml
def _strip_comment(s: str) -> str:
    out, quote, i = [], None, 0
    while i < len(s):
        c = s[i]
        if quote:
            out.append(c)
            if c == quote:
                quote = None
        elif c in "\"'":
            quote = c
            out.append(c)
        elif c == "#" and (i == 0 or s[i - 1] in " \t"):
            break
        else:
            out.append(c)
        i += 1
    return "".join(out).rstrip()


def _scalar(v: str):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [x.strip().strip("\"'") for x in inner.split(",") if x.strip()] if inner else []
    if v.startswith("{"):
        return {}
    if v in ("null", "~", ""):
        return None
    if v in ("true", "false"):
        return v == "true"
    return v.strip("\"'")


def parse_fm(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    data: dict = {}
    cur = None
    for raw in text[4:end].splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        s = line.strip()
        if indent == 0:
            if ":" not in s:
                continue
            k, v = s.split(":", 1)
            k, cur = k.strip(), k.strip()
            data[k] = [] if v.strip() == "" else _scalar(v)
        else:
            if not cur:
                continue
            if s.startswith("- "):
                if not isinstance(data.get(cur), list):
                    data[cur] = []
                data[cur].append(_scalar(s[2:]))
            elif ":" in s:
                if not isinstance(data.get(cur), dict):
                    if data.get(cur) in ([], None):
                        data[cur] = {}
                    else:
                        continue
                k2, v2 = s.split(":", 1)
                data[cur][k2.strip()] = _scalar(v2)
    return data


def verdict_line(text: str) -> str:
    m = re.search(r"^\*\*Conclusion\.\*\*\s*(.+?)$", text, re.M)
    if not m:
        m = re.search(r"^## Verdict\s*\n+(.+?)$", text, re.M)
    if not m:
        return ""
    line = re.sub(r"[*_`]", "", m.group(1)).strip()
    line = re.sub(r"^_?(TO JUDGE|No judgment yet).*", "**pending verdict**", line)
    return line[:160]

def parse_file(path_str: str) -> dict | None:
    """Parses a single file using bounded reading."""
    path = Path(path_str)

    # Bounded read for front-matter (incremental, max 32KB)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            head = ""
            chunk_size = 4096
            max_read = 32768

            # Read first chunk to check if it's even a front-matter file
            chunk = f.read(chunk_size)
            if not chunk.startswith("---"):
                return None

            head += chunk
            # Keep reading until we find the end of front-matter or hit limit
            while len(head) < max_read and "\n---" not in head[3:]:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                head += chunk
    except OSError as exc:
        raise RuntimeError(f"cannot read {path}: {exc}") from exc

    fm = parse_fm(head)
    if "\n---" not in head[3:] and len(head) >= max_read:
        raise RuntimeError(
            f"front-matter in {path} exceeds the {max_read}-byte read window "
            "without a closing '---' delimiter"
        )
    if not fm:
        return None

    # We might need the full file for the verdict string if it's at the bottom.
    # The verdict could be beyond the initial bounded head, so inspect a bounded
    # tail window first and fall back to a full read only when still unresolved.
    verdict = verdict_line(head)
    if not verdict:
        try:
            with open(path, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                tail_size = min(size, max_read)
                f.seek(max(0, size - tail_size))
                tail = f.read(tail_size).decode("utf-8", errors="replace")
                verdict = verdict_line(tail)
        except OSError as exc:
            raise RuntimeError(f"cannot read {path}: {exc}") from exc
    if not verdict:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                verdict = verdict_line(f.read())
        except OSError as exc:
            raise RuntimeError(f"cannot read {path}: {exc}") from exc

    fm["_slug"] = path.stem
    fm["_verdict"] = verdict
    return fm


def fmt(v) -> str:
    if isinstance(v, list):
        return ", ".join(str(x) for x in v) or "-"
    return str(v) if v not in (None, "") else "-"


def lic_of(n: NoteMeta) -> str:
    lic = n.license
    if isinstance(lic, dict):
        return fmt(lic.get("name"))
    return fmt(lic)

def process_chunk(entries: list[str]) -> list[NoteMeta]:
    """Worker process function"""
    results = []
    for path in entries:
        parsed = parse_file(path)
        if parsed:
            results.append(NoteMeta.from_dict(parsed))
    return results

# ---------------------------------------------------------------- load
def load() -> list[NoteMeta]:
    # 1. Discover using os.scandir
    entries = []
    try:
        with os.scandir(REPOS) as it:
            for entry in it:
                try:
                    if entry.is_file() and entry.name.endswith(".md") and not entry.name.startswith("_"):
                        entries.append(entry.path)
                except OSError:
                    raise
    except FileNotFoundError:
        return []
    except OSError:
        raise

    to_parse = entries
    out = []

    if to_parse:
        # 2. Parse concurrently
        workers = min(os.cpu_count() or 4, 8)
        chunksize = max(1, len(to_parse) // (workers * 4))

        # Split into chunks
        chunks = [to_parse[i:i + chunksize] for i in range(0, len(to_parse), chunksize)]

        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
            for result_chunk in executor.map(process_chunk, chunks):
                out.extend(result_chunk)

    return out


# ---------------------------------------------------------------- render
def hub(notes: list[NoteMeta]) -> str:
    by = defaultdict(list)
    for n in notes:
        by[n.disposition or "unjudged"].append(n)

    judged = [n for n in notes if n.disposition]
    queue = [n for n in by["unjudged"] if n.intake != "bulk"]
    swept = [n for n in by["unjudged"] if n.intake == "bulk"]
    actionable = actionable_order()
    unknown = sorted({
        str(d) for d in by if str(d) not in actionable and str(d) not in ("rejected", "unjudged")
    })
    other = [n for name in unknown for k, v in by.items() if str(k) == name for n in v]

    head = f"**{len(judged)} judged candidates.**"
    if queue or swept:
        head += (f" {len(queue) + len(swept)} more have facts but no verdict"
                 f" ({len(swept)} swept in bulk, {len(queue)} scouted deliberately).")

    lines = [
        "# OpenSourceScout — Index",
        "",
        f"_Generated {TODAY} by `scripts/build_index.py` — do not hand-edit._",
        "",
        head,
        "Notes are flat in `knowledge/repos/`; `disposition` lives in front-matter (a route can",
        "change, so files never move). This is the map.",
        "",
        "- [[INDEX-inventory]] — the rejected parts-bin",
        "- [[INDEX-features]] — provides_features -> candidates (set-cover)",
    ] + [f"- [[{p.stem}]] — target" for p in sorted(TARGETS.glob("*.md"))
         if not p.stem.startswith("_")] + [
        "",
        "## Counts",
        "",
        "| disposition | n |",
        "|---|---|",
    ]
    for d in actionable + ["rejected"]:
        if by.get(d):
            lines.append(f"| {d} | {len(by[d])} |")
    if other:
        names = ", ".join(unknown)
        lines.append(f"| _other_ ({names}) | {len(other)} |")
    if queue:
        lines.append(f"| _unjudged (queue)_ | {len(queue)} |")
    if swept:
        lines.append(f"| _unjudged (swept)_ | {len(swept)} |")
    lines.append("")

    for d in actionable:
        group = by.get(d)
        if not group:
            continue
        lines += [f"## {d}  ({len(group)})", "",
                  "| candidate | category | license | status | verdict |", "|---|---|---|---|---|"]
        for n in sorted(group, key=lambda x: x._slug):
            lines.append(
                f"| [[{n._slug}]] | {fmt(n.category)} | {lic_of(n)} | "
                f"{fmt(n.status)} | {n._verdict or '-'} |"
            )
        lines.append("")

    if other:
        lines += [f"## other dispositions  ({len(other)})", "",
                  "Values outside the configured disposition vocabulary are grouped here.", "",
                  "| candidate | disposition | category | license | status | verdict |",
                  "|---|---|---|---|---|---|"]
        for n in sorted(other, key=lambda x: x._slug):
            lines.append(
                f"| [[{n._slug}]] | {fmt(n.disposition)} | {fmt(n.category)} | "
                f"{lic_of(n)} | {fmt(n.status)} | {n._verdict or '-'} |"
            )
        lines.append("")

    if queue:
        lines += [f"## unjudged — the queue  ({len(queue)})", "",
                  "Deliberately scouted, verdict pending. **This is the work list.**", "",
                  "| candidate | license | facts |", "|---|---|---|"]
        for n in sorted(queue, key=lambda x: x._slug):
            lines.append(f"| [[{n._slug}]] | {lic_of(n)} | "
                         f"{fmt(n.stars)}* · {fmt(n.language)} · {fmt(n.pushed_at)} |")
        lines.append("")

    if swept:
        owners = defaultdict(list)
        for n in swept:
            owners[n._slug.split("__")[0]].append(n)
        lines += [f"## swept — not yet triaged  ({len(swept)})", "",
                  "Account sweeps (`intake: bulk`). Facts on disk, **nobody has looked**. Listed by",
                  "owner rather than one-by-one: this is supply, not a queue — pull from it via the",
                  "digest, don't work down it. Absence of a verdict here is *unexamined*, not *rejected*.",
                  "", "| owner | n | digest |", "|---|---|---|"]
        for o in sorted(owners):
            lines.append(f"| {o} | {len(owners[o])} | [[{o}]] |")
        lines.append("")

    if by.get("rejected"):
        lines += [f"## rejected  ({len(by['rejected'])})", "",
                  "Retained as feature-tagged inventory — see [[INDEX-inventory]].", ""]
    return "\n".join(lines)


def inventory(notes: list[NoteMeta]) -> str:
    rej = [n for n in notes if n.disposition == "rejected"]
    by = defaultdict(list)
    for n in rej:
        by[fmt(n.category)].append(n)
    lines = [
        "# Inventory — the parts bin",
        "",
        f"_Generated {TODAY}._  ·  **{len(rej)} rejected candidates**, grouped by category.",
        "",
        "Not a graveyard: these are SUPPLY (fill a target's gaps) and INSPIRATION (a part can seed",
        "a target). A reject is **provisional** — see `criteria.yaml: revalidation`. Back to [[INDEX]].",
        "",
    ]
    for cat in sorted(by):
        lines += [f"## {cat}  ({len(by[cat])})", ""]
        for n in sorted(by[cat], key=lambda x: x._slug):
            feats = fmt(n.provides_features)
            lines.append(f"- [[{n._slug}]] — {n._verdict or '-'}"
                         + (f"  ·  _features:_ {feats}" if feats != "-" else ""))
        lines.append("")
    return "\n".join(lines)


def features(notes: list[NoteMeta]) -> str:
    idx = defaultdict(list)
    for n in notes:
        for f in n.provides_features or []:
            idx[str(f)].append(n)
    lines = [
        "# Features -> candidates",
        "",
        f"_Generated {TODAY}._  ·  **{len(idx)} features** across {len(notes)} candidates.",
        "",
        "The parts-bin index. Match a target's `needs_features` against this to assemble a",
        "build-kit (set-cover). Candidates are ordered vertically by disposition (Actionable > Unjudged > Rejected) for optimal AI discovery. Back to [[INDEX]].",
        "",
    ]
    actionable_names = actionable_order()
    for f in sorted(idx):
        lines.extend([f"## {f}", ""])
        actionable, unjudged, rejected, other = [], [], [], []
        for n in sorted(idx[f], key=lambda x: x._slug):
            if not n.disposition or n.disposition == "unjudged":
                unjudged.append(n)
            elif n.disposition == "rejected":
                rejected.append(n)
            elif n.disposition in actionable_names:
                actionable.append(n)
            else:
                other.append(n)

        if actionable:
            lines.extend(["### Actionable"] + [f"- [[{n._slug}]]" for n in actionable] + [""])
        if unjudged:
            lines.extend(["### Unjudged"] + [f"- [[{n._slug}]]" for n in unjudged] + [""])
        if rejected:
            lines.extend(["### Rejected"] + [f"- [[{n._slug}]]" for n in rejected] + [""])
        if other:
            lines.extend(["### Other dispositions"]
                         + [f"- [[{n._slug}]] - {n.disposition}" for n in other] + [""])
    return "\n".join(lines)


def main() -> None:
    notes = load()
    if not notes:
        raise SystemExit("! no notes found in knowledge/repos/")
    for name, body in (
        ("INDEX.md", hub(notes)),
        ("INDEX-inventory.md", inventory(notes)),
        ("INDEX-features.md", features(notes)),
    ):
        (KNOW / name).write_text(body + "\n", encoding="utf-8")
        print(f"[Index] Rendered -> knowledge/{name}")
    judged = sum(1 for n in notes if n.disposition)
    print(f"[Index] Done. {judged} judged · {len(notes) - judged} awaiting verdict · {len(notes)} total notes.")


if __name__ == "__main__":
    main()
