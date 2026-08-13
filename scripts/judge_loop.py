#!/usr/bin/env python3
"""OpenSourceScout judging layer — the INTERPRETATION pass over the fact corpus.

    python scripts/judge_loop.py --limit 5              # judge 5 unjudged notes
    python scripts/judge_loop.py --owner AppFlowy-IO    # only that account's sweep
    python scripts/judge_loop.py --dry-run --limit 1    # show the prompt, run nothing
    python scripts/judge_loop.py --backend claude       # force a backend (default: auto-detect)

A SEPARATE, optional, resumable pass — never part of the fetch. Fetch produces facts with
no LLM; this consumes facts and produces a verdict. The two never merge (that separation is
what lets you sweep 1000 repos free and judge the few you care about).

Design, ported from irminsul's review_loop.py and sharpened by the facts-vs-interpretation split:

  * THE BACKEND PROPOSES; THE SCRIPT DISPOSES. Any LLM (opencode, claude, …) reads the facts
    and returns a JSON verdict. It NEVER touches the corpus: it runs in an isolated temp cwd
    with everything passed in-prompt, and this script does all persistence. Fact-immutability
    is therefore structural — the judge is not in the write path at all — not a hash-and-revert.
  * THE GATE VALIDATES BEFORE WRITING. A verdict that breaks the schema, uses a feature slug
    outside capabilities.yaml, or is funnel-inconsistent is REJECTED, logged, and skipped —
    never persisted. A cheap model can't be trusted for taste; it CAN be checked for structure.
  * BACKEND-AGNOSTIC. Auto-detect opencode then claude; override with --backend/--model. If
    none is installed, the corpus still stands — judging is optional, judge it by hand.
  * APPEND-ONLY. A verdict appends a judgment-log entry and mirrors the top entry into
    front-matter (criteria.yaml §4b). Re-judging never overwrites; facts are never touched.
  * BOUNDED + RESUMABLE. One backend session per note (context never accumulates). A note with
    a disposition is done and skipped unless you re-judge it explicitly.
  * Subprocess I/O is UTF-8, stdin=/dev/null; a TTY makes some CLIs block forever.

Zero third-party dependencies — stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oss_config  # noqa: E402
from build_index import parse_fm  # noqa: E402  — one front-matter parser, shared

ROOT = Path(__file__).resolve().parents[1]
REPOS = ROOT / "knowledge" / "repos"
PACKS = ROOT / ".cache" / "packs"
PACK_CHARS = 30_000                 # bound the packed source so a big repo can't blow the context
CRITERIA = ROOT / "criteria.yaml"
CONFIG = ROOT / "config.local.yaml"
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "judge_worker.md"
JUDGE_LOG = ROOT / ".cache" / "judge" / "progress.jsonl"
TODAY = dt.date.today().isoformat()

DEFAULTS = {
    # opencode reads the prompt from a -f attachment; claude reads it on stdin. A free model
    # is the point — judging the backlog must not burn premium tokens. Override with --model.
    "opencode_cmd": ["opencode", "run"],
    "claude_cmd": ["claude", "-p"],
    "timeout_sec": 900,   # an --auto agent run is multi-step + slow; 300s timed out mid-judge
                          # (review_loop uses 900). Or drop --auto for a faster single-shot.
    "abort_after_consecutive": 3,   # review_loop's guard: skip an isolated failure, but STOP the
                                    # run once the backend fails N in a row (rate-limited/overloaded).
    # Only consulted when the backend returned NO parseable verdict (see run_backend) — a real
    # stop, not a free model's transient blip mid-success. Bare "429" is gone: it matched any
    # number containing 429 (a token count, a cost) in the --auto trace and forged a rate limit.
    "limit_markers": ["usage limit reached", "rate limit", "quota exceeded",
                      "too many requests", "http 429", "overloaded"],
}

DISPOSITIONS = ["independent", "too_big", "adopt", "merge", "combined", "rejected"]
STATUSES = ["active", "parked_capital"]
PAYOFFS = {"commercial", "reputation", "learning", "strategic",
           "strategic:product", "strategic:capability", "none"}


# --------------------------------------------------------------------------- helpers
def c(text: str, color: str) -> str:
    codes = {"grey": "90", "green": "32", "yellow": "33", "red": "31", "cyan": "36", "bold": "1"}
    return text if not sys.stdout.isatty() else f"\033[{codes.get(color, '0')}m{text}\033[0m"


def sh(cmd, cwd=None, timeout=None, stdin_text=None):
    resolved = shutil.which(cmd[0])
    if resolved:
        cmd = [resolved] + cmd[1:]
    extra = {} if stdin_text is not None else {"stdin": subprocess.DEVNULL}
    r = subprocess.run(cmd, cwd=cwd, input=stdin_text, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=timeout, **extra)
    return r.returncode, (r.stdout or ""), (r.stderr or "")


# --------------------------------------------------------------------------- context
class LimitReached(Exception):
    pass


def criteria_hash() -> str:
    """Short content hash of the RULES the verdict is judged against (criteria + portfolio),
    so a judgment log entry can record exactly what it was judged against — and a later pass
    can tell it was judged under stale rules (criteria.yaml §4b: a re-judge trigger)."""
    h = hashlib.sha256()
    h.update(oss_config.get_criteria_text().encode("utf-8"))
    if CONFIG.exists():
        h.update(CONFIG.read_bytes())
    return h.hexdigest()[:12]


def build_context() -> dict:
    """Everything the backend judges against — read once, reused for the whole batch."""
    projects, src = oss_config.get_portfolio()
    caps = oss_config.get_capabilities()
    cfg = oss_config.load_config()

    cap_lines = [f"  {term}: {', '.join(aliases)}" for term, aliases in sorted(caps.items())]
    proj_lines = [f"  - {p.get('name')}: {str(p.get('what') or '').strip()[:100]}" for p in projects]
    categories = cfg.get("categories") or []

    return {
        "hash": criteria_hash(),
        "criteria": oss_config.get_criteria_text(),
        "capabilities": "\n".join(cap_lines) or "  (none configured)",
        "cap_terms": set(caps.keys()),
        "portfolio": f"source: {src}\n" + ("\n".join(proj_lines) or "  (no projects)"),
        "categories": categories,
    }


# --------------------------------------------------------------------------- note io
def load_note(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_fm(text), text


def _section(text: str, header: str, nexts: list[str]) -> str:
    m = re.search(rf"^{re.escape(header)}\s*\n(.*?)(?=\n##\s|\Z)", text, re.S | re.M)
    return m.group(1).strip() if m else ""


def facts_block(text: str) -> str:
    """The FACTS half of the front-matter — never the null verdict fields above it."""
    m = re.search(r"# ==== FACTS.*?\n(.*?)\n---", text, re.S)
    if m:
        return m.group(1).strip()
    fm = re.search(r"^---\n(.*?)\n---", text, re.S)          # template / old note: whole fm
    return fm.group(1).strip() if fm else ""


def is_judged(fm: dict) -> bool:
    return bool(fm.get("disposition"))


def target_filters(args) -> tuple[str | None, str | None]:
    """-> (exact_slug, owner_prefix) from an optional positional target or --owner.
    owner/repo targets exactly one note; a bare owner filters an account; neither = whole corpus."""
    tgt = re.sub(r"\.git$", "", re.sub(r"^https?://(www\.)?github\.com/", "",
                 (getattr(args, "target", None) or "")).strip("/"))
    if tgt and "/" in tgt:
        return tgt.replace("/", "__"), None
    return None, (tgt or args.owner)


def select_notes(args) -> tuple[list[Path], int]:
    exact, owner = target_filters(args)
    out = []
    total_matched = 0
    for p in sorted(REPOS.glob("*.md")):
        if p.stem.startswith("_"):
            continue
        if exact and p.stem != exact:
            continue
        if owner and not p.stem.startswith(f"{owner}__"):
            continue
        total_matched += 1
        fm, _ = load_note(p)
        if not fm or (is_judged(fm) and not args.force):
            continue
        if args.intake and fm.get("intake") != args.intake:
            continue
        if args.min_stars:
            try:
                if int(fm.get("stars") or 0) < args.min_stars:
                    continue
            except (TypeError, ValueError):
                pass
        out.append(p)
    return (out[: args.limit] if args.limit else out), total_matched



# --------------------------------------------------------------------------- prompt
def build_prompt(text: str, slug: str, ctx: dict) -> tuple[str, str]:
    """-> (prompt, evidence). evidence is 'readme+code' when a pack was folded in, else 'readme'
    — recorded on the judgment so a README-only committal verdict is visibly provisional."""
    tmpl = PROMPT_PATH.read_text(encoding="utf-8")
    readme = _section(text, "## README excerpt", [])
    readme = re.sub(r"^```.*$", "", readme, flags=re.M).strip()      # drop the fences

    pack_gz, pack_md = PACKS / f"{slug}.md.gz", PACKS / f"{slug}.md"
    code = None
    if pack_gz.exists():
        with gzip.open(pack_gz, "rt", encoding="utf-8", errors="replace") as fh:
            code = fh.read()
    elif pack_md.exists():                                     # legacy uncompressed pack
        code = pack_md.read_text(encoding="utf-8", errors="replace")
    if code is not None:
        code = code[:PACK_CHARS] + ("\n\n_[pack truncated for context budget]_"
                                    if len(code) > PACK_CHARS else "")
        evidence = "readme+code"
    else:
        code = "(not packed — judging from README/metadata only)"
        evidence = "readme"

    prompt = (tmpl
              .replace("{facts}", facts_block(text))
              .replace("{description}", _section(text, "## Description (from GitHub)", []) or "(none)")
              .replace("{readme}", readme[:6000] or "(no readme)")
              .replace("{code}", code)
              .replace("{criteria}", ctx["criteria"])
              .replace("{capabilities}", ctx["capabilities"])
              .replace("{portfolio}", ctx["portfolio"])
              .replace("{categories}", "\n".join(f"  - {c}" for c in ctx["categories"]) or "  (none configured)"))
    return prompt, evidence


# --------------------------------------------------------------------------- backend
def find_backend(pref: str) -> str | None:
    order = {"auto": ["opencode", "claude"], "opencode": ["opencode"], "claude": ["claude"]}[pref]
    return next((n for n in order if shutil.which(n)), None)


def run_backend(backend: str, model: str | None, prompt: str, timeout: int) -> str:
    """Run the judge in an ISOLATED temp cwd — it gets everything in the prompt and cannot
    reach the corpus, so nothing it does can mutate a fact. We consume only its stdout."""
    with tempfile.TemporaryDirectory() as sandbox:
        if backend == "opencode":
            try:
                cmd = list(DEFAULTS["opencode_cmd"]) + (["-m", model] if model else [])
                # Do NOT use a file attachment (-f) because opencode treats it as context
                # and runs an agent loop that hallucinates nested JSON.
                # Pass it directly via stdin so opencode treats it as the literal prompt.
                rc, out, err = sh(cmd, cwd=sandbox, timeout=timeout, stdin_text=prompt)
            except OSError:
                pass
        else:
            cmd = list(DEFAULTS["claude_cmd"]) + (["--model", model] if model else [])
            rc, out, err = sh(cmd, cwd=sandbox, timeout=timeout, stdin_text=prompt)

    # A parseable verdict means the backend WORKED — return it and ignore log noise. A free
    # model's momentary "overloaded"/429 that opencode retried THROUGH lands in the --auto tool
    # trace on stderr; scanning that BEFORE checking for a verdict turned a successful judge into
    # a false "rate limit" and aborted the whole run. Only a MISSING verdict + a limit signal is
    # a genuine stop.
    if parse_verdict(out) is not None:
        return out
    if any(m in (out + err).lower() for m in DEFAULTS["limit_markers"]):
        raise LimitReached("usage/rate limit signalled by the backend")
    if rc != 0 and not out.strip():
        raise RuntimeError(f"{backend} exited {rc}: {(err or out).strip()[:200]}")
    return out


_JSON_BLOCK = re.compile(r"```json\s*(.*?)```", re.DOTALL)

_DISPOSITION_MAP = {
    "reject": "rejected",
    "combine": "combined",
    "combination": "combined",
    "independent_project": "independent",
    "too big": "too_big",
}


def _find_key_recursive(data, target_keys) -> str | None:
    if isinstance(data, dict):
        for k in target_keys:
            if k in data and isinstance(data[k], str) and data[k].strip():
                return data[k].strip()
        for v in data.values():
            res = _find_key_recursive(v, target_keys)
            if res:
                return res
    elif isinstance(data, list):
        for item in data:
            res = _find_key_recursive(item, target_keys)
            if res:
                return res
    return None


def parse_verdict(stdout: str) -> dict | None:
    blocks = [b.strip() for b in _JSON_BLOCK.findall(stdout)]
    if not blocks:
        matches = re.findall(r"(\{(?:[^{}]|\{[^{}]*\})*\})", stdout, re.DOTALL)
        blocks = [m.strip() for m in matches if m.strip()]
    for b in reversed(blocks):
        try:
            v = json.loads(b)
            if not isinstance(v, dict):
                continue

            # 1. Hoist nested sub-objects (e.g., {"verdict": {...}}, {"analysis": {...}}, etc.)
            hoisted = {}
            for key, val in list(v.items()):
                if isinstance(val, dict):
                    if key in ("verdict", "facts", "judgment", "result", "analysis", "assessment", "evaluation", "response", "output", "data") or any(k in val for k in ("disposition", "status", "payoff", "conclusion", "rationale", "reasoning")):
                        for subk, subv in val.items():
                            if subk not in v or v[subk] is None:
                                hoisted[subk] = subv
            v.update(hoisted)

            # 2. Normalize key aliases automatically
            for alias, canon in _KEY_ALIASES.items():
                if alias in v and (canon not in v or v[canon] is None or v[canon] == ""):
                    if isinstance(v[alias], dict):
                        v.pop(alias)
                    else:
                        v[canon] = v.pop(alias)

            # 2.5. Recursive fallback for required fields if still empty
            if not v.get("conclusion") or not isinstance(v["conclusion"], str) or not v["conclusion"].strip():
                conclusion_keys = {"conclusion", "rationale", "reasoning", "reason", "summary", "justification", "note", "verdict", "explanation", "decisive_reason"}
                found = _find_key_recursive(v, conclusion_keys)
                if found:
                    v["conclusion"] = found

            if not v.get("disposition") or not isinstance(v["disposition"], str) or not v["disposition"].strip():
                disposition_keys = {"disposition", "decision", "route", "disposition_type"}
                found = _find_key_recursive(v, disposition_keys)
                if found:
                    v["disposition"] = found

            if not v.get("status") or not isinstance(v["status"], str) or not v["status"].strip():
                status_keys = {"status", "capital_status"}
                found = _find_key_recursive(v, status_keys)
                if found:
                    v["status"] = found

            # 3. Skip prompt placeholders or non-verdict JSON objects
            disp = v.get("disposition")
            if isinstance(disp, str) and "|" in disp:
                continue

            if not any(k in v for k in ("disposition", "status", "payoff", "conclusion", "provides_features", "merge_target", "adopt_serves")):
                continue

            # 4. Normalize field values
            if isinstance(disp, str):
                disp_clean = disp.strip().lower()
                if disp_clean in _DISPOSITION_MAP:
                    v["disposition"] = _DISPOSITION_MAP[disp_clean]

            st = v.get("status")
            if isinstance(st, str):
                st_clean = st.strip().lower()
                if st_clean in ("parked", "parked capital", "parked_capital", "needs_money", "needs money"):
                    v["status"] = "parked_capital"
                else:
                    v["status"] = "active"
            else:
                v["status"] = "active"

            # 3.5. Convert list-based string fields back to simple strings
            for str_key in ("conclusion", "the_move", "risks", "changed", "corrected"):
                val = v.get(str_key)
                if isinstance(val, list):
                    v[str_key] = ", ".join(str(x) for x in val if x)

            po = v.get("payoff")
            if isinstance(po, str):
                if "|" in po:
                    po = []
                elif "," in po:
                    po = [p.strip() for p in po.split(",") if p.strip()]
                elif po.strip():
                    po = [po.strip()]
                else:
                    po = []
            elif not isinstance(po, list):
                po = []

            if isinstance(po, list):
                norm_po = []
                for p in po:
                    p_clean = str(p).strip().lower()
                    if p_clean in ("strategic_product", "product"):
                        norm_po.append("strategic:product")
                    elif p_clean in ("strategic_capability", "capability", "strategic"):
                        norm_po.append("strategic:capability")
                    elif p_clean in PAYOFFS:
                        norm_po.append(p_clean)
                po = norm_po

            disp_curr = v.get("disposition")
            if not po:
                if disp_curr == "rejected":
                    v["payoff"] = ["none"]
                elif disp_curr == "adopt":
                    v["payoff"] = ["strategic:capability"]
                elif disp_curr in ("merge", "combined"):
                    v["payoff"] = ["strategic:product"]
                else:
                    v["payoff"] = ["learning"]
            else:
                if "none" in po:
                    if disp_curr == "rejected":
                        v["payoff"] = ["none"]
                    else:
                        v["payoff"] = [p for p in po if p != "none"] or ["learning"]
                else:
                    v["payoff"] = po

            if "none" in v["payoff"] and v.get("disposition") != "rejected":
                v["disposition"] = "rejected"


            for list_key in ("provides_features", "provides_specifics"):
                val = v.get(list_key)
                if isinstance(val, str):
                    v[list_key] = [val.strip()] if val.strip() else []
                elif val is None:
                    v[list_key] = []

            if v.get("disposition") == "adopt" and v.get("adopt_serves") not in ("product_workflow", "build_pipeline"):
                as_str = str(v.get("adopt_serves") or "").lower()
                if "workflow" in as_str or "product" in as_str:
                    v["adopt_serves"] = "product_workflow"
                else:
                    v["adopt_serves"] = "build_pipeline"

            cat = v.get("category")
            if isinstance(cat, str) and cat.lower() in ("uncategorizable", "unknown", "none", "n/a", "null", "other"):
                v["category"] = None

            return v
        except json.JSONDecodeError:
            continue
    return None






# --------------------------------------------------------------------------- gate
def validate(v: dict, ctx: dict) -> list[str]:
    """Deterministic checks. Returns [] if the verdict may be persisted, else the reasons.
    Cannot check whether the verdict is RIGHT — only that it's structurally legal."""
    errs = []
    disp = v.get("disposition")
    if disp not in DISPOSITIONS:
        errs.append(f"disposition {disp!r} not in {DISPOSITIONS}")
    if v.get("status") not in STATUSES:
        errs.append(f"status {v.get('status')!r} not in {STATUSES}")

    payoff = v.get("payoff") or []
    if not isinstance(payoff, list) or not payoff:
        errs.append('payoff must be a non-empty list (use ["none"] if evaluated to no payoff)')
    else:
        bad = [p for p in payoff if p not in PAYOFFS]
        if bad:
            errs.append(f"payoff has unknown values: {bad}")
        if "none" in payoff and len(payoff) > 1:              # 'none' is an answer, not a companion
            errs.append("payoff 'none' must stand alone")
        if "none" in payoff and disp != "rejected":           # zero payoff → nothing to pursue
            errs.append("payoff 'none' is only consistent with disposition=rejected")

    feats = v.get("provides_features") or []
    if not isinstance(feats, list):
        errs.append("provides_features must be a list")
    else:
        outside = [f for f in feats if f not in ctx["cap_terms"]]
        if outside:                                            # the rule capabilities.yaml exists for
            errs.append(f"provides_features outside the vocabulary: {outside}")

    cats = ctx.get("categories") or []
    if cats and v.get("category") and v["category"] not in cats:
        errs.append(f"category {v.get('category')!r} not in configured categories")

    conclusion = v.get("conclusion")
    if not isinstance(conclusion, str) or not conclusion.strip():
        errs.append("conclusion is empty")

    # funnel-consistency: the disposition's own precondition must be filled.
    if disp == "merge" and not (v.get("merge_target") or "").strip():
        errs.append("disposition=merge requires merge_target")
    if disp == "adopt" and (v.get("adopt_serves") not in ("product_workflow", "build_pipeline")):
        errs.append("disposition=adopt requires adopt_serves ∈ {product_workflow, build_pipeline}")
    if disp == "combined" and not (v.get("combination_covers_target") or "").strip():
        errs.append("disposition=combined requires combination_covers_target")
    return errs


# --------------------------------------------------------------------------- write
def _yaml_list(xs) -> str:
    return "[" + ", ".join(str(x) for x in (xs or [])) + "]"


def _set_key(head: str, key: str, value: str) -> str:
    """Replace a top-level `key: ...` line in the front-matter, preserving its comment."""
    pat = re.compile(rf"^({re.escape(key)}:)([^\n#]*)(#[^\n]*)?$", re.M)
    if pat.search(head):
        return pat.sub(lambda m: f"{m.group(1)} {value}" + (f"  {m.group(3)}" if m.group(3) else ""),
                       head, count=1)
    return head            # key absent (older schema) — skip rather than corrupt


def render_entry(v: dict, backend: str, trigger: str, ctx: dict, evidence: str) -> str:
    tgt = v.get("merge_target") or v.get("adopt_serves") or v.get("combination_covers_target")
    arrow = f" → {tgt}" if tgt else ""
    disp_status = "rejected" if v["disposition"] == "rejected" else f"{v['disposition']}/{v['status']}"
    lines = [
        f"### {TODAY} · {disp_status}{arrow} · judge: ai:{backend} · trigger: {trigger}",
        f"context: criteria@{ctx['hash']} · portfolio@{TODAY} · evidence: {evidence}",
        f"**Conclusion.** {v['conclusion'].strip()}",
    ]
    if (v.get("changed") or "").strip():
        lines.append(f"**Changed.** {v['changed'].strip()}")
    if (v.get("corrected") or "").strip():
        lines.append(f"**Corrected.** {v['corrected'].strip()}")
    if (v.get("the_move") or "").strip():
        lines.append(f"**The move.** {v['the_move'].strip()}")
    if (v.get("risks") or "").strip():
        lines.append(f"**Risks.** {v['risks'].strip()}")
    return "\n".join(lines)


# Old-schema bulk notes (fetched before the judgment-log schema) carry these flat prose stubs.
# Judging migrates the note to a log, so the empty stubs must go — but Description/README are
# FACTS and stay. Fence-aware: a `## ` inside the fenced README excerpt is content, not a header.
_OLD_STUBS = {"verdict", "reasoning", "the move", "risks / watch-outs", "risks"}


def _strip_old_stubs(body: str) -> str:
    out, in_fence, skip = [], False, False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            if not skip:
                out.append(line)
            continue
        if not in_fence and line.startswith("## "):
            skip = line[3:].strip().lower() in _OLD_STUBS
            if skip:
                continue
        if not skip:
            out.append(line)
    return "\n".join(out).rstrip()


def write_verdict(path: Path, v: dict, backend: str, trigger: str, ctx: dict, evidence: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    head, sep, log = text.partition("\n## Judgment log")
    if not sep:                                # old-schema note: drop its flat stubs, migrate to a log
        head, log = _strip_old_stubs(text.rstrip()), "\n\n"

    # 1. front-matter mirror — only verdict fields; the FACTS block is never in these keys.
    fm_end = head.find("\n---", head.find("---") + 3)
    fm, body = (head[:fm_end], head[fm_end:]) if fm_end != -1 else (head, "")
    fm = _set_key(fm, "disposition", v["disposition"])
    fm = _set_key(fm, "status", v["status"])
    fm = _set_key(fm, "category", str(v.get("category") or "null"))
    fm = _set_key(fm, "payoff", _yaml_list(v.get("payoff")))
    fm = _set_key(fm, "provides_features", _yaml_list(v.get("provides_features")))
    fm = _set_key(fm, "provides_specifics", _yaml_list(v.get("provides_specifics")))
    fm = _set_key(fm, "judged_by", "automated+ai")

    # 2. append the entry, newest-first; drop the "_No judgment yet_" placeholder if present.
    prior = re.sub(r"_No judgment yet.*?_\s*", "", log, flags=re.S).strip()
    prior_entries = [e for e in re.split(r"(?=^### )", prior, flags=re.M) if e.strip().startswith("###")]
    entry = render_entry(v, backend, trigger, ctx, evidence)
    n = len(prior_entries) + 1
    fm = _set_key(fm, "judgments", f'"{n} entr{"y" if n == 1 else "ies"}, last {TODAY}"')

    new_log = "\n## Judgment log\n\n" + "\n\n".join([entry] + prior_entries).rstrip() + "\n"
    path.write_text(fm + body + new_log, encoding="utf-8")


def log_progress(entry: dict) -> None:
    JUDGE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with JUDGE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


# Keys weak models emit instead of the schema's — criteria/fact vocabulary bleeding into output.
_KEY_ALIASES = {
    "rationale": "conclusion",
    "reasoning": "conclusion",
    "reason": "conclusion",
    "summary": "conclusion",
    "justification": "conclusion",
    "note": "conclusion",
    "verdict": "conclusion",
    "explanation": "conclusion",
    "decisive_reason": "conclusion",
    "payoffs": "payoff",
    "features": "provides_features",
    "feature_list": "provides_features",
    "specifics": "provides_specifics",
    "decision": "disposition",
    "route": "disposition",
    "disposition_type": "disposition",
    "merge_home": "merge_target",
    "merge_mode": "merge_target",
    "harvest_type": "merge_target",
    "capital_to_launch": "status",
    "capital_status": "status",
}



def propose_verdict(backend: str, model: str | None, prompt: str, ctx: dict,
                    timeout: int) -> tuple[dict | None, list[str], bool, str]:
    """Propose a verdict; if the gate (or the JSON parse) rejects it, retry ONCE with the exact
    reasons fed back — a weak model usually fixes a *named* structural fault on the second pass,
    cheap yield next to leaving the note unjudged. Returns (verdict|None, errs, retried); a None
    verdict means still invalid after the retry. run_backend's LimitReached / RuntimeError /
    TimeoutExpired propagate to the caller's loop unchanged (so a limit mid-retry still stops)."""
    def attempt(text: str) -> tuple[dict | None, list[str], str]:
        out = run_backend(backend, model, text, timeout)
        v = parse_verdict(out)
        e = validate(v, ctx) if v else ["no json verdict — output exactly one fenced ```json block"]
        return v, e, out

    verdict, errs, out = attempt(prompt)
    if not errs:
        return verdict, [], False, out

    # If it emitted the right judgment under the WRONG keys (criteria/fact vocabulary as output
    # keys — the flat-but-wrong-keys failure), the exact renames are far more actionable to a weak
    # model than the generic gate reasons.
    renames = ""
    if isinstance(verdict, dict):
        found = [(a, canon) for a, canon in _KEY_ALIASES.items() if a in verdict]
        if found:
            renames = ("\nYou used the WRONG key names — rename these, and do not invent output keys:\n"
                       + "\n".join(f"  - `{a}` -> `{canon}`" for a, canon in found) + "\n")

    # One correction pass: name exactly what the gate rejected and resend the rules. Show the
    # rejected answer so it can SEE the fault, but tell it not to repeat it.
    retry_prompt = (
        f"{prompt}\n\n---\n\n## STOP — your previous answer was REJECTED by the gate\n\n"
        "Fix EXACTLY these problems, then output one corrected ```json block and nothing else:\n"
        + "\n".join(f"  - {e}" for e in errs)
        + renames
        + "\n\nThe answer you gave (do not repeat its mistakes):\n\n"
        + (out.strip()[:2000] or "(nothing)")
        + "\n\nRe-read the rules above. Output ONLY the corrected json block.")
    verdict, errs2, out2 = attempt(retry_prompt)
    if not errs2:
        return verdict, [], True, out2

    # Attempt 3: The Critic loop. If it failed twice, we force it to explicitly reason about
    # its failure before generating the final JSON. We use the same backend model.
    critic_prompt = (
        f"{prompt}\n\n---\n\n"
        f"## CRITIC MODE — FINAL ATTEMPT\n"
        f"You failed to generate valid output twice.\n"
        f"Errors from attempt 1:\n" + "\n".join(f"  - {e}" for e in errs) + "\n"
        f"Errors from attempt 2:\n" + "\n".join(f"  - {e}" for e in errs2) + "\n\n"
        f"Your failed output from attempt 2:\n\n{out2.strip()[:2000] or '(nothing)'}\n\n"
        f"Take a deep breath. First, briefly explain exactly WHY your previous output violated "
        f"the schema or rules (e.g., 'I invented a feature that was not in the vocabulary' or 'I output text instead of JSON').\n"
        f"Then, output the strictly corrected ```json block."
    )
    verdict, errs3, out3 = attempt(critic_prompt)

    if errs3 and isinstance(verdict, dict):
        feats = verdict.get("provides_features")
        if isinstance(feats, list):
            valid_feats = [f for f in feats if f in ctx["cap_terms"]]
            invalid_feats = [f for f in feats if f not in ctx["cap_terms"]]
            if invalid_feats:
                verdict["provides_features"] = valid_feats
                specs = verdict.get("provides_specifics") or []
                if not isinstance(specs, list):
                    specs = [str(specs)]
                verdict["provides_specifics"] = list(specs) + invalid_feats
                errs3 = validate(verdict, ctx)
    return (verdict if not errs3 else None), errs3, True, out3


# --------------------------------------------------------------------------- main
def main() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(description="Judge unjudged notes against criteria.yaml.")
    ap.add_argument("target", nargs="?", help="owner/repo (one note) or owner (account); omit for whole corpus")
    ap.add_argument("--owner", help="only notes for this account (slug prefix)")
    ap.add_argument("--intake", choices=["targeted", "bulk"], help="only this intake")
    ap.add_argument("--min-stars", type=int, default=0, metavar="N")
    ap.add_argument("--limit", type=int, default=0, metavar="N", help="at most N notes this run")
    ap.add_argument("--backend", choices=["auto", "opencode", "claude"], default="auto")
    ap.add_argument("--model", help="backend model override (e.g. a free opencode model)")
    ap.add_argument("--trigger", default="initial", help="judgment-log trigger (default: initial)")
    ap.add_argument("--force", action="store_true", help="re-judge notes that already have a verdict")
    ap.add_argument("--dry-run", action="store_true", help="select + print one prompt, run nothing")
    args = ap.parse_args()

    notes, total_matched = select_notes(args)
    if not notes:
        if total_matched > 0:
            print(c("All matching notes are already judged. (Use --force to re-judge.)", "green"))
            sys.exit(0)
        sys.exit(c("No matching notes found in the corpus. (Have you run scout.py first?)", "yellow"))
    print(c(f"{len(notes)} note(s) selected.", "grey"))


    ctx = build_context()

    if args.dry_run:
        prompt, evidence = build_prompt(notes[0].read_text(encoding="utf-8", errors="replace"),
                                        notes[0].stem, ctx)
        print(c(f"\n=== prompt for {notes[0].stem}  (evidence: {evidence}; nothing sent) ===", "bold"))
        print(prompt[:2500])
        print(c(f"\n... [{len(notes)} note(s) would be judged]", "grey"))
        return

    backend = find_backend(args.backend)
    if not backend:
        sys.exit(c("No judge backend found (opencode/claude). The corpus stands regardless — "
                   "judging is optional; judge by hand, or install a backend.", "red"))
    print(c(f"backend: {backend}" + (f" (model {args.model})" if args.model else ""), "cyan"))

    judged = failed = consecutive = 0
    abort_after = DEFAULTS["abort_after_consecutive"]
    stopped_early: str | None = None
    for i, p in enumerate(notes, 1):
        # A run of failures means the backend is unhealthy (rate-limited/overloaded/timing out),
        # not that each note is individually bad — stop and resume rather than burn the whole
        # queue timing out one note at a time. (review_loop's consecutive_gate_failures_abort.)
        if consecutive >= abort_after:
            print(c(f"\n  [Error] {consecutive} evaluations failed in a row. The AI backend looks unhealthy (rate-limited or down). "
                    f"Stopping early. Re-run later to resume.", "yellow"))
            stopped_early = "unhealthy"
            break
        print(c(f"\n[Judge] [{i}/{len(notes)}] Evaluating {p.stem}...", "bold"))
        prompt, evidence = build_prompt(p.read_text(encoding="utf-8", errors="replace"), p.stem, ctx)
        try:
            verdict, errs, retried, raw_out = propose_verdict(
                backend, args.model, prompt, ctx, DEFAULTS["timeout_sec"])
        except LimitReached as e:
            print(c(f"  [Error] Token limit reached: {e}. Stopping early. Re-run to resume.", "yellow"))
            stopped_early = "limit"
            break
        except (RuntimeError, subprocess.TimeoutExpired) as e:
            failed += 1; consecutive += 1
            print(c(f"  [AI Error] The model timed out or failed to respond. Skipped.", "red"))
            log_progress({"note": p.stem, "result": "backend_error", "detail": str(e)[:200]})
            continue

        if verdict is None:                                    # invalid JSON/gate even after the retry
            failed += 1; consecutive += 1
            tail = " (after critic loop)" if retried else ""
            print(c(f"  [AI Error] The model failed to output a valid structured verdict{tail}. Skipped.", "red"))
            log_progress({"note": p.stem, "result": "gate_rejected", "errors": errs,
                          "retried": retried, "raw_output": raw_out[:1000]})
            continue

        write_verdict(p, verdict, backend, args.trigger, ctx, evidence)
        judged += 1
        consecutive = 0                                        # a good verdict breaks the failure run
        tag = "" if evidence == "readme+code" else c("  (No code packed, judged on README only)", "yellow")
        tag += c("  (Self-corrected on retry)", "yellow") if retried else ""
        disp_status = "rejected" if verdict["disposition"] == "rejected" else f"{verdict['disposition']}/{verdict['status']}"
        print(c(f"  [Verdict] {disp_status} — {verdict['conclusion'].strip()}", "green") + tag)
        log_progress({"note": p.stem, "result": "judged", "evidence": evidence,
                      "disposition": verdict["disposition"], "backend": backend, "retried": retried})

    suffix = "" if os.environ.get("OSS_RUNNER") else " Run 'python scripts/build_index.py' to update your knowledge base."
    print(c(f"\n[Judge] Complete. {judged} evaluated, {failed} skipped.{suffix}", "cyan"))

    if stopped_early == "limit":         # exit 3 = rate/usage limit
        sys.exit(3)
    elif stopped_early == "unhealthy":   # exit 4 = consecutive failures / backend unhealthy
        sys.exit(4)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\n! interrupted — notes already written are kept; re-run to resume.")
