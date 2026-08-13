#!/usr/bin/env python3
"""OpenSourceScout convenience flow — one command for the whole pipeline.

    python scripts/run.py owner/repo        # fetch -> pack -> judge, one repo
    python scripts/run.py owner             # fetch account -> pack all -> judge all
    python scripts/run.py owner --no-judge  # ingest only (fetch + pack), judge later
    python scripts/run.py owner/repo --backend claude --model ...

This is ONLY an orchestrator. It runs the same three independent stages you can run by hand —
scout.py (fetch), pack_repos.py (pack), judge_loop.py (judge) — back to back on the SAME target,
and touches none of them. Everything the stages guarantee (LLM-free fetch, the gate, resume, the
append-only log, commit-pinned packs) holds unchanged; this just saves typing three commands.

Pipeline: a repo/account enters the corpus, gets its facts, gets its permanent evidence pack,
then gets judged against it. Re-run any time — each stage skips work already done.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable


def stage(script: str, *stage_args: str) -> int:
    print(f"\n\033[36m$ {script} {' '.join(stage_args)}\033[0m")
    import os
    env = os.environ.copy()
    env["OSS_RUNNER"] = "1"
    return subprocess.run([PY, str(HERE / script), *stage_args], env=env).returncode



def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch -> pack -> judge in one command.")
    ap.add_argument("target", help="owner/repo, owner, or a github.com URL")
    ap.add_argument("--no-pack", action="store_true", help="skip the pack stage (README-only judging)")
    ap.add_argument("--no-judge", action="store_true", help="ingest only (fetch + pack)")
    ap.add_argument("--force", action="store_true", help="pass through: overwrite / re-do")
    ap.add_argument("--min-stars", type=int, default=0, metavar="N")
    ap.add_argument("--backend", choices=["auto", "opencode", "claude"], default="auto")
    ap.add_argument("--model", help="judge backend model override")
    args = ap.parse_args()

    passthru = ["--force"] if args.force else []

    # 1. FETCH — always. LLM-free. An account link sweeps every repo by default.
    fetch = [args.target] + passthru + (["--min-stars", str(args.min_stars)] if args.min_stars else [])
    if stage("scout.py", *fetch) != 0:
        sys.exit("! fetch failed — stopping before pack/judge.")

    # 2. PACK — unless suppressed. Clones + stores the commit-pinned evidence snapshot.
    #    Same target: owner/repo packs one, owner packs the account. Resumable.
    if not args.no_pack:
        stage("pack_repos.py", args.target, *passthru)        # non-zero = some clones failed; press on

    # 3. JUDGE — unless suppressed. Uses the pack when present (evidence: readme+code).
    #    judge_loop exit codes: 0 = judged to completion · 3 = rate/usage limit · 4 = consecutive failures
    #    other = never judged (no backend installed / nothing selected).
    judge_rc = 0
    if not args.no_judge:
        judge = [args.target] + passthru
        judge += ["--backend", args.backend] if args.backend != "auto" else []
        judge += ["--model", args.model] if args.model else []
        judge_rc = stage("judge_loop.py", *judge)

    # 4. INDEX — only refresh the map when the judge completed (or was skipped with --no-judge).
    #    A judge that stopped early (rate limit or consecutive failures) or never ran leaves the
    #    pass unfinished; the resume re-run indexes then, so we don't publish a map over a half-finished run.
    if judge_rc == 0:
        stage("build_index.py")
        print("\n\033[36mdone.\033[0m")
    elif judge_rc == 3:
        print("\n\033[33mjudge stopped early (rate/usage limit) — notes still await a verdict; "
              "index NOT refreshed. Re-run to resume.\033[0m")
    elif judge_rc == 4:
        print("\n\033[33mjudge stopped early (consecutive failures / backend unhealthy) — notes still await a verdict; "
              "index NOT refreshed. Re-run to resume.\033[0m")
    else:
        print("\n\033[33m! judge did not run (no backend / nothing to judge) — index NOT "
              "refreshed. Re-run when a backend is available.\033[0m")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)

