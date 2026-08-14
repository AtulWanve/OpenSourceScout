#!/usr/bin/env python3
"""OpenSourceScout PROMPT OPTIMIZER — The auto-healing prompt loop (Idea 2).

Reads the `.cache/judge/progress.jsonl` log to find instances where the LLM failed
the validation gate. It extracts the structural errors and the raw hallucinated output,
then uses the LLM to rewrite `prompts/judge_worker.md` to prevent those specific mistakes.

Usage:
    python scripts/optimize_prompt.py
    python scripts/optimize_prompt.py --backend claude
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Reuse backend infrastructure from judge_loop
sys.path.insert(0, str(Path(__file__).resolve().parent))
import judge_loop
from judge_loop import c

ROOT = Path(__file__).resolve().parents[1]
PROGRESS_LOG = ROOT / ".cache" / "judge" / "progress.jsonl"
PROMPT_PATH = ROOT / "prompts" / "judge_worker.md"
OUTPUT_PATH = ROOT / "prompts" / "judge_worker.suggested.md"


def load_failures(limit: int = 15) -> list[dict]:
    """Load the most recent distinct failures that include raw output."""
    if not PROGRESS_LOG.exists():
        return []

    failures = []
    seen_raw = set()

    # Read backwards to get the most recent errors
    try:
        lines = PROGRESS_LOG.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if entry.get("result") == "gate_rejected" and "raw_output" in entry:
            raw = entry["raw_output"].strip()
            if not raw or raw in seen_raw:
                continue

            seen_raw.add(raw)
            failures.append({
                "note": entry.get("note", "unknown"),
                "errors": entry.get("errors", []),
                "raw_output": raw
            })

            if len(failures) >= limit:
                break

    return failures


def build_optimizer_prompt(current_prompt: str, failures: list[dict]) -> str:
    log_text = ""
    for i, f in enumerate(failures, 1):
        errs = "\n".join(f"    - {e}" for e in f["errors"])
        log_text += f"### Failure {i} (Repo: {f['note']})\n"
        log_text += f"**Validation Errors Thrown:**\n{errs}\n"
        log_text += f"**Raw Output from LLM:**\n```\n{f['raw_output'][:800]}\n```\n\n"

    return f"""I need help rewriting a prompt template for my application.

## Background
We have a system where an LLM evaluates GitHub repositories and outputs a strict JSON verdict.
However, it frequently fails validation. We have logged its raw output and the resulting Python validation errors.

## The Current Prompt
```markdown
{current_prompt}
```

## Failure Logs (Recent Mistakes)
{log_text}

## Instructions
1. **Analyze the failures.**
   - Is it wrapping the keys in a made-up parent object (like `"facts": {{...}}`)?
   - Is it outputting conversational text instead of just JSON?
   - Is the API truncating the output because it's too long, meaning we need to ask for less data or force a more concise structure?
2. **Critique the methodology.** Briefly write down why the current prompt allows or encourages these mistakes.
3. **Rewrite the prompt.** Provide an updated, highly robust version of the Current Prompt. Add strict formatting rules, bold warnings, or layout changes specifically designed to defeat the failure modes seen above.

IMPORTANT: Ensure you wrap your complete rewritten prompt inside a SINGLE ```markdown block. Do not split it across multiple blocks.

Output your response in two parts:
1. A `<critique>` block explaining your analysis of the failures.
2. The complete rewritten prompt inside a ```markdown block.
"""


def main():
    ap = argparse.ArgumentParser(description="Optimize the judge prompt based on failure logs.")
    ap.add_argument("--backend", choices=["auto", "opencode", "claude"], default="auto")
    ap.add_argument("--model", type=str, help="Model override")
    args = ap.parse_args()

    print(c("OpenSourceScout Prompt Optimizer", "bold"))
    print(c("Scanning progress.jsonl for AI failure logs...", "grey"))

    failures = load_failures(limit=10)
    if not failures:
        sys.exit(c("No failures with 'raw_output' found in the logs. Nothing to optimize!", "green"))

    print(c(f"Found {len(failures)} distinct failure patterns.", "cyan"))

    current_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    meta_prompt = build_optimizer_prompt(current_prompt, failures)

    backend = judge_loop.find_backend(args.backend)
    if not backend:
        sys.exit(c("No backend found.", "red"))

    print(c(f"Running optimizer via {backend}... (this may take a minute)", "yellow"))

    import tempfile
    import os
    import subprocess
    import shutil

    # Run the backend directly without judge_loop's hardcoded "output JSON verdict" wrapper
    with tempfile.TemporaryDirectory() as sandbox:
        if backend == "opencode":
            fd, pf = tempfile.mkstemp(prefix="oss_opt_", suffix=".md")
            os.close(fd)
            Path(pf).write_text(meta_prompt, encoding="utf-8")
            try:
                cmd = ["opencode", "run", "--auto"] + (["-m", args.model] if args.model else [])
                cmd += ["Write a rewritten prompt template for the application described in the attached file. Output your critique in a <critique> block, and the new prompt in a markdown block.", "-f", pf]

                resolved = shutil.which(cmd[0])
                if resolved:
                    cmd[0] = resolved

                r = subprocess.run(cmd, cwd=sandbox, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
                result = r.stdout
            finally:
                try:
                    os.remove(pf)
                except OSError:
                    pass
        else:
            cmd = ["claude", "-p"] + (["--model", args.model] if args.model else [])

            resolved = shutil.which(cmd[0])
            if resolved:
                cmd[0] = resolved

            r = subprocess.run(cmd, cwd=sandbox, input=meta_prompt, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
            result = r.stdout

    if not result.strip():
        sys.exit(c("LLM returned empty output.", "red"))

    # Extract the markdown block containing the new prompt
    new_prompt = ""
    if "```markdown" in result:
        new_prompt = result.split("```markdown", 1)[1].rpartition("```")[0].strip()
    elif "```" in result:
        new_prompt = result.split("```", 1)[1].rpartition("```")[0].strip()

    print("\n" + "="*50)
    print(c("ANALYSIS COMPLETE", "bold"))
    print("="*50)

    critique = result.split("<critique>")[1].split("</critique>")[0].strip() if "<critique>" in result else "No critique block provided."
    print(c(critique, "cyan"))
    print("="*50 + "\n")

    if new_prompt:
        OUTPUT_PATH.write_text(new_prompt, encoding="utf-8")
        print(c(f"SUCCESS: Optimized prompt saved to -> {OUTPUT_PATH.relative_to(ROOT)}", "green"))
        print(c("Review the file, and if you like the changes, overwrite prompts/judge_worker.md with it.", "grey"))
    else:
        print(c("Failed to extract the rewritten markdown prompt from the LLM response.", "red"))
        print("Raw output:")
        print(result)


if __name__ == "__main__":
    main()
