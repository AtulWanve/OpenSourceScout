#!/usr/bin/env python3
"""OpenSourceScout entrypoint — the AUTOMATED half of `judging.repo: automated_then_ai`.

    python scripts/scout.py owner/repo                 -> fact-prefilled note, ready for an AI verdict
    python scripts/scout.py https://github.com/owner   -> a note for EVERY repo + an inbox digest index
    python scripts/scout.py owner --min-stars 10       -> ...only repos with >=10 stars (forks/archived off)
    python scripts/scout.py owner/repo --pack          -> also pack the source (native, no deps)
    python scripts/scout.py owner/repo --force         -> overwrite an existing note

Why this exists: the mechanical work (fetch / normalise / write) must NOT happen inside an
AI session — that is what burns tokens on every fresh session and fills context until the
model drifts. This script does the facts; the AI only fills the verdict.

There are TWO bottlenecks and they are not the same one:

    fetch + write notes   the SCRIPT does it   ~free (api calls, not tokens)
    read + judge notes    the AI does it       expensive; fills context

Only the second needs rationing. Notes cost nothing until something reads them, so an account
link sweeps EVERY repo into real notes and lets the AI judge whichever ones it chooses — that
is the point of giving an account link instead of a repo link. Every note records `intake:` —
`targeted` (you asked for this one) or `bulk` (swept in, nobody has triaged it). Both are
"facts, no verdict"; the difference is whether a human ever considered it, which is what a
planner needs to weigh an absence.

Auth: set GITHUB_TOKEN for 5000 req/hr (unauthenticated is 60/hr). The token may live in the
process environment OR in a .env file at the repo root — both work, and neither is required:
with no token at all the script runs anonymously. See load_dotenv().
Zero third-party dependencies — stdlib only.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import gzip
import http.client
import time
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOS = ROOT / "knowledge" / "repos"
DAILY = ROOT / "knowledge" / "daily"
INBOX = ROOT / "inbox"
PACKS = ROOT / ".cache" / "packs"
API = "https://api.github.com"
TODAY = dt.date.today().isoformat()


# ---------------------------------------------------------------- env
def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Fold a .env file into the environment, if one exists. Stdlib only — no python-dotenv.

    Preserves BOTH flows on purpose:
      - no .env, or a blank GITHUB_TOKEN=  -> nothing set -> anonymous (60/hr). Still works.
      - GITHUB_TOKEN=ghp_...               -> loaded    -> authenticated (5000/hr).

    A real exported env var always WINS over the file (`key not in os.environ`), so a shell
    `export GITHUB_TOKEN=...` is never silently overridden by a stale .env. Empty values are
    skipped, so `GITHUB_TOKEN=` leaves you anonymous rather than sending an empty Bearer token
    (which GitHub 401s). No .env is not an error — it IS the without-token flow.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and val and key not in os.environ:
            os.environ[key] = val


# ---------------------------------------------------------------- github api
class GHError(Exception):
    """A github failure the CALLER must classify.

    This is not ceremony. `gh` used to sys.exit on every error and callers caught SystemExit
    to mean "404, try something else" — so a rate-limit 403 became "no repos found for
    <account>", and a rate-limited readme became "" -> `license: none`. Silent wrong FACTS,
    which is the one thing this script exists to prevent. Only 404 is ever a normal outcome;
    everything else must reach the human.
    """

    def __init__(self, code: int, url: str, *, rate_limited: bool = False, reset: int = 0, body: str = ""):
        self.code, self.url, self.rate_limited, self.reset, self.body = code, url, rate_limited, reset, body
        super().__init__(f"github {code}: {url}")

    @property
    def is_tos_blocked(self) -> bool:
        if self.code == 403 and self.body:
            try:
                data = json.loads(self.body)
                return data.get("message") == "Repository access blocked" and data.get("block", {}).get("reason") == "tos"
            except Exception:
                pass
        return False

    def explain(self) -> str:
        if self.rate_limited:
            when = dt.datetime.fromtimestamp(self.reset).strftime("%H:%M:%S") if self.reset else "?"
            return (f"! github rate limit exhausted (resets {when}).\n"
                    f"  anonymous is 60/hr — set GITHUB_TOKEN for 5000/hr.")
        if self.code == 404:
            return f"! not found: {self.url}"
        if self.code == 451:
            return f"! unavailable for legal reasons (HTTP 451): {self.url}"
        if self.is_tos_blocked:
            return f"! repository access blocked by GitHub for TOS violation (HTTP 403): {self.url}"
        if self.code == 0:
            return f"! network error reaching {self.url}"
        return f"! github error {self.code}: {self.url}"


def gh(path: str) -> dict | list:
    url = path if path.startswith("http") else f"{API}{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "OpenSourceScout")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # 403/429 with no quota left is a rate limit; a 403 WITH quota left is a real
            # permission error and must not be mislabelled.
            body = e.read().decode("utf-8", "replace") if hasattr(e, "read") else ""
            remaining = e.headers.get("X-RateLimit-Remaining")
            reset = int(e.headers.get("X-RateLimit-Reset") or 0)
            limited = e.code in (403, 429) and remaining == "0"
            raise GHError(e.code, url, rate_limited=limited, reset=reset, body=body) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead) as e:
            if attempt < 2:
                time.sleep(1)
                continue
            raise GHError(0, url) from None


def rate_budget() -> tuple[int, int]:
    """-> (remaining, reset_epoch), or (-1, 0) if unknown. /rate_limit doesn't cost quota."""
    try:
        core = gh("/rate_limit")["resources"]["core"]  # type: ignore[index]
        return int(core["remaining"]), int(core["reset"])
    except (GHError, KeyError, TypeError):
        return -1, 0


def parse_target(raw: str) -> tuple[str, str, str | None]:
    """-> ('repo'|'account', owner, name|None)"""
    s = raw.strip().rstrip("/")
    s = re.sub(r"^https?://(www\.)?github\.com/", "", s)
    s = re.sub(r"\.git$", "", s)
    parts = [p for p in s.split("/") if p]
    if len(parts) >= 2:
        return "repo", parts[0], parts[1]
    if len(parts) == 1:
        return "account", parts[0], None
    sys.exit(f"! cannot parse target: {raw}")


def fetch_readme(owner: str, name: str, limit: int = 200_000) -> str:
    """Return the FULL readme (render_note truncates for display).

    Do NOT truncate here: licence declarations live near the END of a readme
    ("## 8. License"). A 3000-char cap silently broke detect_license and made it
    report `none` for a repo whose readme plainly grants MIT.

    Only 404 may become "". Anything else MUST raise: a rate-limited readme returning ""
    makes detect_license write `license: none` — indistinguishable from a real absence, and
    across an account sweep it would forge that fact for every repo after the limit hit.
    """
    try:
        data = gh(f"/repos/{owner}/{name}/readme")
    except GHError as e:
        if e.code == 404:
            return ""      # genuinely has no readme
        raise
    try:
        text = base64.b64decode(data.get("content", "")).decode("utf-8", "replace")
    except Exception:
        return ""
    return text[:limit]


def fetch_account_repos(owner: str) -> list[dict]:
    """An account is a user OR an org — we don't know which, so we try both.

    ONLY a 404 means "wrong kind, try the other". Any other error propagates: reporting a
    rate limit as an empty account is a lie about the world, and it reads exactly like the
    truthful "this account has no repos".
    """
    missing = 0
    for kind in ("users", "orgs"):
        repos: list[dict] = []
        page = 1
        while True:
            try:
                batch = gh(f"/{kind}/{owner}/repos?per_page=100&page={page}&type=owner")
            except GHError as e:
                if e.code == 404:
                    missing += 1
                    break          # not a {kind} — fall through to the next kind
                raise
            if not isinstance(batch, list) or not batch:
                break
            repos.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        if repos:
            repos.sort(key=lambda r: r.get("stargazers_count", 0), reverse=True)
            return repos
    if missing == 2:
        raise GHError(404, f"{API}/users/{owner}")   # neither a user nor an org: no such account
    return []                                        # exists, genuinely has no public repos


# ---------------------------------------------------------------- repomix
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
             ".next", ".nuxt", "target", "vendor", ".idea", ".vscode", ".mypy_cache"}
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf", ".zip",
            ".gz", ".tar", ".7z", ".mp4", ".mp3", ".wav", ".woff", ".woff2", ".ttf",
            ".eot", ".so", ".dll", ".dylib", ".exe", ".bin", ".lock", ".pyc", ".class",
            ".jar", ".wasm", ".parquet", ".db", ".sqlite"}
MAX_FILE_BYTES = 200_000
MAX_TOTAL_CHARS = 4_000_000


def _is_text(p: Path) -> bool:
    try:
        return b"\x00" not in p.open("rb").read(2048)
    except OSError:
        return False


def pack(owner: str, name: str) -> tuple[Path, str] | None:
    """Pack a remote repo into ONE compressed, commit-pinned evidence file. Stdlib only.

    This is a BLUEPRINT of repomix's approach (clone -> filter -> concat -> count),
    reimplemented rather than depended on, so that: we own the filtering rules, scout
    stays zero-dependency, and there is NO installer for an agent to run at all
    (install_risk = none by construction, not by discipline).

    The pack is a DURABLE EVIDENCE SNAPSHOT, not a throwaway cache: a verdict is judged
    against the code AS IT WAS, and the repo may later change or vanish — so regeneration
    can't reproduce it. We pin the exact commit and keep the pack permanently, gzipped
    (~3.6x). `git clone --depth 1` gives .gitignore-respecting selection for free.
    -> (path, commit_sha), or None on failure.
    """
    PACKS.mkdir(parents=True, exist_ok=True)
    out = PACKS / f"{owner}__{name}.md.gz"
    with tempfile.TemporaryDirectory() as tmp:
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", "--quiet",
                 f"https://github.com/{owner}/{name}.git", tmp],
                check=True, capture_output=True, timeout=300,
                # Skip Git LFS smudge: the pack wants SOURCE, and LFS holds exactly the big
                # binaries it discards anyway (a 21 MB .sqlite is already in SKIP_EXT). Fetching
                # them wastes bandwidth and — when the LFS quota/host is down — fails the clone
                # outright, costing the code evidence over a file we never keep. LFS files stay
                # as tiny pointer text, which the pack skips just the same.
                env={**os.environ, "GIT_LFS_SKIP_SMUDGE": "1", "GIT_TERMINAL_PROMPT": "0"},
            )
        except FileNotFoundError:
            print("  ! git not found — cannot pack")
            return None
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode('utf-8', 'replace')
            if "Clone succeeded, but checkout failed" in err_msg:
                print(f"  ! clone checkout warning (proceeding): {err_msg[:160].strip()}")
            else:
                print(f"  ! clone failed: {err_msg[:160].strip()}")
                return None
        except subprocess.TimeoutExpired:                      # huge repo: degrade, don't crash
            print("  ! clone timed out (>300s) — too large to pack; judging README-only")
            return None

        try:
            sha = subprocess.run(["git", "-C", tmp, "rev-parse", "HEAD"],
                                 check=True, capture_output=True, timeout=30
                                 ).stdout.decode("utf-8", "replace").strip()
        except (subprocess.SubprocessError, OSError):
            sha = ""

        root = Path(tmp)
        files = []
        for p in sorted(root.rglob("*")):
            rel = p.relative_to(root)
            if not p.is_file() or set(rel.parts[:-1]) & SKIP_DIRS:
                continue
            if p.suffix.lower() in SKIP_EXT or p.stat().st_size > MAX_FILE_BYTES:
                continue
            if _is_text(p):
                files.append(p)

        tree = "\n".join(p.relative_to(root).as_posix() for p in files)
        parts = [f"# Repository pack: {owner}/{name}", "",
                 f"_Packed {TODAY} by OpenSourceScout — {len(files)} text files · "
                 f"commit {sha[:12] or '?'}._", "",
                 "## File tree", "", "```", tree, "```", ""]
        total = 0
        for p in files:
            body = p.read_text(encoding="utf-8", errors="replace").rstrip()
            if total + len(body) > MAX_TOTAL_CHARS:
                parts.append("\n_[truncated — total size cap reached]_\n")
                break
            total += len(body)
            parts += [f"## {p.relative_to(root).as_posix()}", "",
                      "```" + (p.suffix.lstrip(".") or ""), body, "```", ""]
        text = "\n".join(parts)
        with gzip.open(out, "wt", encoding="utf-8") as fh:      # permanent, compressed
            fh.write(text)

    print(f"  packed -> {out.relative_to(ROOT)}  ({len(files)} files, commit {sha[:8] or '?'})")
    return out, sha


LICENSE_DECL = re.compile(
    r"licen[sc]ed\s+under\s+(?:the\s+)?[`*\"']*([A-Za-z0-9.\-+ ]{2,40}?)[`*\"']*\s*licen[sc]e",
    re.I,
)


def detect_license(r: dict, readme: str) -> tuple[str, str, list[str]]:
    """-> (name, state, declared_in)   state: file | declared_only | none

    The GitHub API only reports a license when it detects a LICENSE *file*. A README
    saying "licensed under the MIT License" IS an express grant by the copyright holder —
    weaker than a file, but NOT all-rights-reserved. Conflating the two wrongly rejects
    usable projects; it did exactly that to AndersonBY/python-repomix. Never infer
    "no license" from the API alone.

    TODO: also read package metadata (pyproject.toml / package.json) — criteria.yaml
    lists it as a valid `declared_in` source; we only cover LICENSE file + README so far.
    """
    spdx = (r.get("license") or {}).get("spdx_id")
    if spdx and spdx not in ("NONE",):
        # NOASSERTION = a LICENSE file exists but wasn't recognised — still a file.
        return spdx, "file", ["LICENSE file"]
    m = LICENSE_DECL.search(readme or "")
    if m:
        return m.group(1).strip(), "declared_only", ["README"]
    return "null", "none", []


NOTE_LIC = re.compile(
    r"^license:[ \t]*\n[ \t]+name:[ \t]*([^\n#]+?)[ \t]*(?:#[^\n]*)?\n[ \t]+state:[ \t]*(\w+)", re.M)


def license_from_note(p: Path) -> tuple[str, str, list[str]] | None:
    """Recover a licence already on disk, so re-running a sweep costs no quota per kept note.

    Returns None for notes written before `license.state` existed — the caller then falls
    back to the api field, which is honest (`?` = unchecked) rather than wrong.
    """
    m = NOTE_LIC.search(p.read_text(encoding="utf-8", errors="replace"))
    return (m.group(1).strip(), m.group(2).strip(), []) if m else None


# ---------------------------------------------------------------- rendering
def render_note(r: dict, readme: str, pack_path: Path | None, intake: str = "targeted",
                pack_sha: str | None = None) -> str:
    owner = r["owner"]["login"]
    name = r["name"]
    lic_name, lic_state, lic_where = detect_license(r, readme)
    topics = r.get("topics") or []
    desc = (r.get("description") or "").replace('"', "'")
    pushed = (r.get("pushed_at") or "")[:10]
    if pack_path:
        packline = (f'pack: "{pack_path.relative_to(ROOT).as_posix()}"\n'
                    f"packed_sha: {pack_sha or 'null'}       # commit the pack is pinned to (evidence snapshot)")
    else:
        packline = "pack: null\npacked_sha: null"
    return f"""---
candidate: "{owner}/{name}"
type: repo
url: "{r.get('html_url', '')}"
evaluated: {TODAY}
judged_by: automated          # this note is FACTS ONLY until a judge fills the verdict below.
                              # a judge is whoever routes it: a human, or any AI a consumer points
                              # at it -> then automated+human | automated+ai. Fetch needs no LLM.
intake: {intake}              # targeted = deliberately scouted | bulk = account sweep, nobody has triaged it

# ==== VERDICT — filled by a judge (you, or any AI consumer). Everything below is pre-filled facts. ====
disposition: null           # independent | too_big | adopt | merge | combined | rejected  (mirrors top log entry)
status: null                # active | parked_capital
judgments: none             # none | "<N> entries, last <date>" — set when first judged; mirrors the log
provides_features: []
provides_specifics: []      # free-text nuance the vocabulary loses
category: null              # the judge picks one from config.local.yaml categories (interpretation, not a fact)
payoff: []                  # commercial | reputation | learning | strategic(:product|:capability) | none
                            # (always present; none = evaluated → no payoff, stands alone, forces rejected)
liability_risk: null
capital_to_launch: null     # zero | needs_money
paid_dependencies: []
install_risk: null          # none | manual_review | agent_forbidden  (REQUIRED for adopt)
step1_independent: {{ worth_doing: null, solo_ai_scope: null }}
adopt: {{ serves: null }}
merge: {{ target: null, mode: null, harvest_type: null }}
combination: {{ covers_target: null, members: [] }}

# ==== FACTS — fetched {TODAY}, do not hand-edit (a judge never writes below this line) ====
stars: {r.get('stargazers_count', 0)}
forks: {r.get('forks_count', 0)}
open_issues: {r.get('open_issues_count', 0)}
language: {r.get('language') or 'null'}
pushed_at: {pushed or 'null'}
archived: {str(r.get('archived', False)).lower()}
is_fork: {str(r.get('fork', False)).lower()}
license:
  name: {lic_name}
  state: {lic_state}        # file | declared_only | none  (declared_only is a REAL grant)
  declared_in: [{', '.join(lic_where)}]
  attribution_required: null
  copyleft: null
  commercial_ok: null
ai_at_build: null
ai_at_run: null
emerging_class: false
{packline}
tags: [{', '.join(topics[:10])}]
---

## Description (from GitHub)

{desc or '_none_'}

## README excerpt

```
{readme.strip()[:2000] or '(no readme)'}
```

## Judgment log

_No judgment yet — facts only (intake: {intake}). A review APPENDS the first entry here
(trigger: initial) and fills the current-verdict fields above. Newest entry is always the active
verdict; see knowledge/repos/_TEMPLATE.md for the entry shape (Conclusion / Changed / Corrected /
The move / Risks). Record the outcome, not the discussion._
"""


def digest(owner: str, repos: list[dict], licenses: dict[str, tuple], skipped: int = 0,
           unavailable: list[str] | None = None, empty: list[str] | None = None) -> str:
    """Render the account digest — the index over notes the sweep just wrote.

    Licence comes from `licenses` (detected against the real readme). A repo is absent only
    when its note predates `license.state`; then we fall back to the api's spdx, and `?` for
    "not checked" — NEVER "none", which the api reports for any repo lacking a LICENSE *file*
    even when its readme grants one. Printing that false "none" is the bug that wrongly
    rejected AndersonBY/python-repomix; the honest word for unknown is `?`.

    `unavailable` repos (HTTP 451 — legal takedown) have NO note, so they are kept out of the
    table (no broken `[[wikilink]]`, and "every repo below has a note" stays true) and named
    in a footnote instead — the account listing saw them, but they couldn't be scouted.
    `empty` repos (no readme AND no code) are similarly skipped to prevent AI hallucination.
    """
    gone = set((unavailable or []) + (empty or []))
    rows = []
    for r in repos:
        name = r["name"]
        if name in gone:
            continue
        if name in licenses:
            lic_name, state, _ = licenses[name]
            lic = "none" if state == "none" else (
                lic_name if state == "file" else f"{lic_name} (readme)")
        else:
            spdx = (r.get("license") or {}).get("spdx_id")
            lic = spdx if spdx and spdx != "NONE" else "?"
        flags = " ".join(f for f, on in (
            ("`archived`", r.get("archived")), ("`fork`", r.get("fork"))) if on)
        d = (r.get("description") or "").replace("|", "/")[:90]
        rows.append(
            f"| [[{owner}__{name}]] | {r.get('stargazers_count',0)} | {r.get('language') or '-'} | "
            f"{lic} | {(r.get('pushed_at') or '')[:10]} | {flags or '-'} | {d} |"
        )

    kept = (f"\n\n_{skipped} already had notes and were left untouched (verdicts preserved)._"
            if skipped else "")
    blocked = (f"\n\n_{len(unavailable)} unavailable for legal/TOS reasons, no note: "
               f"{', '.join(sorted(unavailable))}._" if unavailable else "")
    skipped_empty = (f"\n\n_{len(empty)} skipped as empty (no README, no code packed), no note: "
                     f"{', '.join(sorted(empty))}._" if empty else "")

    return f"""# Inbox digest — {owner}

Fetched {TODAY} · {len(repos)} repos · sorted by stars.

**Every repo below has a note** (`intake: bulk`) — facts fetched, verdict pending. Open one
and judge it; nothing here has been triaged by a human.{kept}{blocked}{skipped_empty}

| repo | ★ | lang | license | pushed | flags | description |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}
"""


def log_daily(line: str) -> None:
    DAILY.mkdir(parents=True, exist_ok=True)
    f = DAILY / f"{TODAY}.md"
    if not f.exists():
        f.write_text(f"# {TODAY}\n\n", encoding="utf-8")
    with f.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# ---------------------------------------------------------------- main
def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser(description="Scout a GitHub repo or account.")
    ap.add_argument("target", help="owner/repo, owner, or a github.com URL")
    ap.add_argument("--pack", action="store_true", help="also pack source (repo mode)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing note")
    ap.add_argument("--min-stars", type=int, default=0, metavar="N",
                    help="account mode: skip repos under N stars")
    ap.add_argument("--include-forks", action="store_true", help="account mode: keep forks")
    ap.add_argument("--include-archived", action="store_true", help="account mode: keep archived")
    args = ap.parse_args()

    kind, owner, name = parse_target(args.target)
    print("[Scout] Using Auth: token (5000/hr)" if os.environ.get("GITHUB_TOKEN")
          else "[Scout] Using Auth: anonymous (60/hr — add GITHUB_TOKEN to .env for 5000/hr)")

    if kind == "account":
        repos = fetch_account_repos(owner)
        if not repos:
            sys.exit(f"[Error] {owner} has no public repos")

        kept = [r for r in repos
                if r.get("stargazers_count", 0) >= args.min_stars
                and (args.include_forks or not r.get("fork"))
                and (args.include_archived or not r.get("archived"))]
        if len(kept) < len(repos):
            print(f"[Scout] {len(repos) - len(kept)} filtered out "
                  f"(min-stars={args.min_stars}, forks/archived excluded by default)")
        if not kept:
            sys.exit("[Error] Every repo was filtered out — loosen --min-stars/--include-*")

        # An account link means "process every repo" — that's why an account URL was given
        # instead of a repo URL. So account mode always sweeps into real notes; the digest is
        # the index over them, not a substitute for them.
        REPOS.mkdir(parents=True, exist_ok=True)
        todo = [r for r in kept
                if args.force or not (REPOS / f"{owner}__{r['name']}.md").exists()]
        # Check the budget BEFORE writing anything: a sweep that dies halfway leaves a
        # half-swept account, and the digest would then describe a state that isn't real.
        remaining, reset = rate_budget()
        if 0 <= remaining < len(todo):
            when = dt.datetime.fromtimestamp(reset).strftime("%H:%M:%S") if reset else "?"
            sys.exit(f"[Error] Sweeping {owner} needs ~{len(todo)} api calls, {remaining} left "
                     f"(resets {when}).\n"
                     f"  add GITHUB_TOKEN to .env for 5000/hr, or narrow with --min-stars N.\n"
                     f"  notes already written are kept — re-running resumes where it stopped.")
        licenses: dict[str, tuple] = {}
        unavailable: list[str] = []
        empty_repos: list[str] = []
        skipped = written = 0
        for i, r in enumerate(kept, 1):
            nm = r["name"]
            note = REPOS / f"{owner}__{nm}.md"
            if note.exists() and not args.force:
                # Read the licence back off disk rather than re-fetching: keeps the digest
                # correct AND makes a resumed sweep cost quota only for what's missing.
                cached = license_from_note(note)
                if cached:
                    licenses[nm] = cached
                skipped += 1
                print(f"[Scout] [{i}/{len(kept)}] {nm} — note exists, kept")
                continue
            # A 451 is a permanent, unambiguous per-repo terminal state (DMCA/legal block) —
            # like 404, it forges no fact, so it skips THIS repo instead of aborting the sweep
            # (and poisoning every resume). No note is written; the repo is honestly recorded
            # as unavailable in the digest, and a later run picks it up if it's reinstated.
            try:
                readme = fetch_readme(owner, nm)
            except GHError as e:
                if e.code == 451 or e.is_tos_blocked:
                    reason_str = "legal reasons (HTTP 451)" if e.code == 451 else "TOS violation (HTTP 403)"
                    print(f"[Scout] [{i}/{len(kept)}] {nm} — unavailable for {reason_str}; skipping")
                    unavailable.append(nm)
                    continue
                raise

            packed = pack(owner, nm) if args.pack else None
            p, sha = packed if packed else (None, None)

            if not readme.strip() and not p:
                print(f"[Scout] [{i}/{len(kept)}] {nm} — skipped: no evidence (empty README and no code packed)")
                empty_repos.append(nm)
                continue

            licenses[nm] = detect_license(r, readme)
            note.write_text(render_note(r, readme, p, intake="bulk", pack_sha=sha), encoding="utf-8")
            written += 1
            print(f"[Scout] [{i}/{len(kept)}] {nm} -> created note")
        tail = f", {len(unavailable)} unavailable (legal/TOS)" if unavailable else ""
        tail += f", {len(empty_repos)} empty" if empty_repos else ""
        print(f"[Scout] Done. {written} notes written, {skipped} preserved{tail}")
        log_daily(f"- SWEPT {owner} -> {written} notes (intake: bulk), {skipped} preserved{tail}")

        INBOX.mkdir(parents=True, exist_ok=True)
        out = INBOX / f"{owner}.md"
        out.write_text(digest(owner, kept, licenses, skipped, unavailable, empty_repos), encoding="utf-8")
        print(f"[Scout] Digest created -> {out.relative_to(ROOT)} ({len(kept)} repos)")
        return

    REPOS.mkdir(parents=True, exist_ok=True)
    note = REPOS / f"{owner}__{name}.md"
    if note.exists() and not args.force:
        sys.exit(f"[Error] Note exists (verdict preserved): {note.relative_to(ROOT)}\n  use --force to refetch facts")

    try:
        r = gh(f"/repos/{owner}/{name}")
        readme = fetch_readme(owner, name)
    except GHError as e:
        if e.code == 451:
            sys.exit(f"[Error] {owner}/{name} unavailable for legal reasons (HTTP 451); Nothing to scout.")
        if e.is_tos_blocked:
            sys.exit(f"[Error] {owner}/{name} unavailable for TOS violation (HTTP 403); Nothing to scout.")
        raise
    packed = pack(owner, name) if args.pack else None
    p, sha = packed if packed else (None, None)

    if not readme.strip() and not p:
        sys.exit(f"[Error] {owner}/{name} has no README and no code was packed. Skipping to prevent zero-evidence hallucination.")

    note.write_text(render_note(r, readme, p, pack_sha=sha), encoding="utf-8")
    print(f"[Scout] Success -> {note.relative_to(ROOT)} (facts filled; verdict pending)")
    log_daily(f"- SCOUTED {owner}/{name} -> facts pending verdict ({r.get('stargazers_count',0)}*, "
              f"{r.get('language') or '-'}, {(r.get('license') or {}).get('spdx_id') or 'none'})")


if __name__ == "__main__":
    try:
        main()
    except GHError as e:
        sys.exit(e.explain())
    except KeyboardInterrupt:
        sys.exit("\n! interrupted — notes already written are kept; re-run to resume.")
