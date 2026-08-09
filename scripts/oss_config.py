#!/usr/bin/env python3
"""Shared config loading for OpenSourceScout. Stdlib only.

Holds a MINIMAL YAML-subset reader (enough for our own files — not a general parser)
plus the loaders that resolve `portfolio_source`, so the portfolio has ONE source of
truth and the two readers can never drift.

Supported YAML subset: nested maps, block lists of scalars, block lists of maps,
inline lists `[a, b]`, quoted scalars, and folded blocks (`>`). That covers
config.local.yaml and capabilities.yaml. Anything fancier is out of scope by design.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.local.yaml"
EXAMPLE = ROOT / "config.example.yaml"
CAPABILITIES = ROOT / "capabilities.yaml"


# ---------------------------------------------------------------- minimal yaml
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
    if v in ("null", "~", ""):
        return None
    if v in ("true", "false"):
        return v == "true"
    if v in (">", "|", ">-", "|-"):
        return "__FOLD__"
    return v.strip("\"'")


def _rows(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        s = _strip_comment(raw)
        if s.strip():
            out.append((len(s) - len(s.lstrip()), s.strip()))
    return out


def _block(rows: list[tuple[int, str]], i: int, indent: int):
    """-> (value, next_index) for the block starting at rows[i] with the given indent."""
    if rows[i][1].startswith("- "):
        items = []
        while i < len(rows) and rows[i][0] == indent and rows[i][1].startswith("- "):
            body = rows[i][1][2:].strip()
            i += 1
            if ":" in body and not body.startswith(("[", '"', "'")):
                k, v = body.split(":", 1)
                item = {}
                val = _scalar(v)
                if val == "__FOLD__" or (v.strip() == "" and i < len(rows) and rows[i][0] > indent):
                    sub, i = _block(rows, i, rows[i][0]) if i < len(rows) else (None, i)
                    item[k.strip()] = sub
                else:
                    item[k.strip()] = val
                while i < len(rows) and rows[i][0] > indent and not rows[i][1].startswith("- "):
                    k2, _, v2 = rows[i][1].partition(":")
                    i += 1
                    val2 = _scalar(v2)
                    if val2 == "__FOLD__":
                        buf, ind = [], None
                        while i < len(rows) and (ind is None or rows[i][0] >= ind):
                            if rows[i][0] <= indent + 2 and ":" in rows[i][1]:
                                break
                            ind = ind or rows[i][0]
                            buf.append(rows[i][1])
                            i += 1
                        val2 = " ".join(buf)
                    item[k2.strip()] = val2
                items.append(item)
            else:
                items.append(_scalar(body))
        return items, i

    data: dict = {}
    while i < len(rows) and rows[i][0] == indent:
        k, _, v = rows[i][1].partition(":")
        k = k.strip()
        i += 1
        val = _scalar(v)
        if val == "__FOLD__":
            buf = []
            while i < len(rows) and rows[i][0] > indent:
                buf.append(rows[i][1])
                i += 1
            data[k] = " ".join(buf)
        elif v.strip() == "" and i < len(rows) and rows[i][0] > indent:
            data[k], i = _block(rows, i, rows[i][0])
        else:
            data[k] = val
    return data, i


def loads(text: str) -> dict:
    rows = _rows(text)
    if not rows:
        return {}
    val, _ = _block(rows, 0, rows[0][0])
    return val if isinstance(val, dict) else {}


def load_file(p: Path) -> dict:
    return loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# ---------------------------------------------------------------- loaders
def load_config() -> dict:
    if not CONFIG.exists():
        raise SystemExit(
            f"! no config.local.yaml — copy the example and edit it:\n"
            f"    cp {EXAMPLE.name} {CONFIG.name}"
        )
    return load_file(CONFIG)


def get_portfolio() -> tuple[list[dict], str]:
    """-> (projects, source_description)

    ONE store, possibly two readers. `portfolio_source: local` uses existing_projects
    here; a path reads an external registry (e.g. ../irminsul/projects/) so the two can
    never drift. Auto-detection is deliberately not a default — a tool silently judging
    against a portfolio you didn't know it picked up is how surprises happen.
    """
    cfg = load_config()
    src = (cfg.get("portfolio_source") or "local").strip()

    if src == "local":
        return cfg.get("existing_projects") or [], "local (config.local.yaml)"

    ext = (ROOT / src).resolve() if not Path(src).is_absolute() else Path(src)
    if not ext.exists():
        raise SystemExit(f"! portfolio_source points at a missing path: {ext}")

    projects: list[dict] = []
    if ext.is_dir():
        for p in sorted(ext.glob("*.y*ml")):
            d = load_file(p)
            d.setdefault("name", p.stem)
            projects.append(d)
    else:
        d = load_file(ext)
        projects = d.get("existing_projects") or d.get("projects") or []
    return projects, f"external ({ext})"


def get_capabilities() -> dict[str, list[str]]:
    """The controlled vocabulary for provides_features: {term: [aliases]}."""
    return (load_file(CAPABILITIES) or {}).get("capabilities") or {}


if __name__ == "__main__":
    projects, src = get_portfolio()
    print(f"portfolio_source: {src}")
    print(f"{len(projects)} project(s):")
    for p in projects:
        print(f"  - {p.get('name')}: {str(p.get('what'))[:70]}")
    caps = get_capabilities()
    print(f"\ncapabilities vocabulary: {len(caps)} controlled terms")
