#!/usr/bin/env python3
"""Tests reproducing hardcoded drift between documentation/templates and script implementations."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import judge_loop  # noqa: E402
import scout  # noqa: E402


def test_scout_render_note_includes_all_template_funnel_blocks():
    """Test 1: Test that scout.render_note() includes all template funnel blocks present in _TEMPLATE.md.

    Specifically verifies step1b_too_big:, upstream_pr:, and simplify_fork:.
    """
    template_path = ROOT / "knowledge" / "repos" / "_TEMPLATE.md"
    assert template_path.exists(), f"Template not found at {template_path}"
    template_text = template_path.read_text(encoding="utf-8")

    # Extract funnel result block keys from _TEMPLATE.md
    funnel_part = template_text.split("# --- funnel results")[1].split("tags:")[0]
    template_funnel_blocks = [
        line.split(":")[0].strip() + ":"
        for line in funnel_part.splitlines()
        if line.strip() and not line.strip().startswith("#") and ":" in line and not line.startswith(" ")
    ]

    # Ensure the target funnel blocks are present in _TEMPLATE.md funnel results
    for required in ["step1b_too_big:", "upstream_pr:", "simplify_fork:"]:
        assert required in template_funnel_blocks, (
            f"Expected {required} to be defined in _TEMPLATE.md funnel results"
        )

    sample_repo = {
        "owner": {"login": "testowner"},
        "name": "testrepo",
        "html_url": "https://github.com/testowner/testrepo",
        "description": "Test repository",
        "pushed_at": "2026-01-01T00:00:00Z",
        "stargazers_count": 42,
        "forks_count": 5,
        "open_issues_count": 1,
        "language": "Python",
        "archived": False,
        "fork": False,
        "topics": ["test"],
        "license": {"spdx_id": "MIT"},
    }

    rendered_note = scout.render_note(sample_repo, "# Test README", None)

    missing_blocks = [block for block in template_funnel_blocks if block not in rendered_note]
    assert not missing_blocks, (
        f"scout.render_note() is missing template funnel blocks: {missing_blocks}"
    )


def test_validate_verdict_accepts_upstream_pr_and_simplify_fork():
    """Test 2: Test that judge_loop.validate_verdict() accepts verdicts with upstream_pr and simplify_fork.

    Verifies dispositions upstream_pr and simplify_fork are accepted and not rejected by DISPOSITIONS.
    """
    validate_verdict = getattr(judge_loop, "validate_verdict", getattr(judge_loop, "validate", None))
    assert validate_verdict is not None, "judge_loop must define validate_verdict or validate"

    ctx = judge_loop.build_context()

    dispositions = ["upstream_pr", "simplify_fork"]
    rejections = {}
    for disp in dispositions:
        verdict = {
            "disposition": disp,
            "status": "active",
            "payoff": ["strategic"],
            "provides_features": [],
            "category": None,
            "conclusion": f"Valid test conclusion for {disp}",
        }
        errs = validate_verdict(verdict, ctx)
        if errs:
            rejections[disp] = errs

    assert not rejections, (
        f"judge_loop.validate_verdict() rejected valid dispositions: {rejections}"
    )


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__]))
