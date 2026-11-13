#!/usr/bin/env python3
"""Tests for configuration fallback and dynamic disposition indexing."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_index  # noqa: E402
import oss_config  # noqa: E402


def test_load_config_falls_back_to_example_when_local_missing(monkeypatch, tmp_path):
    """Verify load_config() falls back to config.example.yaml when config.local.yaml is absent."""
    missing_config = tmp_path / "config.local.yaml"
    monkeypatch.setattr(oss_config, "CONFIG", missing_config)

    # Calling load_config() must not raise SystemExit; it must return parsed config.example.yaml
    cfg = oss_config.load_config()
    expected = oss_config.load_file(oss_config.EXAMPLE)
    assert cfg == expected
    assert isinstance(cfg, dict)
    assert "categories" in cfg


def test_load_config_prefers_local_when_present(monkeypatch, tmp_path):
    """Verify load_config() prioritizes config.local.yaml over config.example.yaml."""
    local_cfg = tmp_path / "config.local.yaml"
    local_cfg.write_text("categories: [custom_local_category]\n", encoding="utf-8")
    monkeypatch.setattr(oss_config, "CONFIG", local_cfg)

    cfg = oss_config.load_config()
    assert cfg == {"categories": ["custom_local_category"]}


def test_load_config_raises_system_exit_when_both_missing(monkeypatch, tmp_path):
    """Verify load_config() raises an informative SystemExit when both config files are absent."""
    missing_local = tmp_path / "missing_config.local.yaml"
    missing_example = tmp_path / "missing_config.example.yaml"
    monkeypatch.setattr(oss_config, "CONFIG", missing_local)
    monkeypatch.setattr(oss_config, "EXAMPLE", missing_example)

    with pytest.raises(SystemExit) as exc_info:
        oss_config.load_config()

    err = str(exc_info.value)
    assert "! no config.local.yaml - copy the example and edit it:" in err


def test_zero_config_environment_baseline_invariants():
    """Verify repository baseline invariants: config.example.yaml is tracked and valid."""
    assert oss_config.EXAMPLE.exists(), "config.example.yaml must exist as the baseline template"
    example_cfg = oss_config.load_file(oss_config.EXAMPLE)
    assert isinstance(example_cfg, dict), "config.example.yaml must parse to a dictionary"
    assert "categories" in example_cfg, "config.example.yaml must define categories"
    assert "portfolio_source" in example_cfg, "config.example.yaml must define portfolio_source"


def test_actionable_dispositions_derived_from_criteria(monkeypatch):
    """Verify build_index.ACTIONABLE dynamically reflects oss_config.get_dispositions()."""
    # 1. Dynamic check: If a new disposition is in oss_config.get_dispositions(),
    # build_index.ACTIONABLE must include it rather than being a static hardcoded list.
    new_disp = "custom_actionable"
    mock_dispositions = oss_config.get_dispositions() + [new_disp]
    monkeypatch.setattr(oss_config, "get_dispositions", lambda: mock_dispositions)

    assert new_disp in build_index.ACTIONABLE, (
        f"build_index.ACTIONABLE must dynamically include '{new_disp}' from oss_config.get_dispositions()"
    )
    assert list(build_index.ACTIONABLE) == [d for d in mock_dispositions if d != "rejected"]

    # 2. Revert monkeypatch and verify default criteria dispositions (excluding 'rejected')
    monkeypatch.undo()
    expected_default = [d for d in oss_config.get_dispositions() if d != "rejected"]
    assert list(build_index.ACTIONABLE) == expected_default
    assert "rejected" not in build_index.ACTIONABLE


def test_no_dead_topics_folder_references():
    """Verify dead references to non-existent knowledge/topics folder are removed."""
    repo_root = ROOT
    gitignore_text = (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert "knowledge/topics" not in gitignore_text

    criteria_text = (repo_root / "criteria.yaml").read_text(encoding="utf-8")
    assert "knowledge/topics" not in criteria_text

    template_text = (repo_root / "knowledge" / "repos" / "_TEMPLATE.md").read_text(encoding="utf-8")
    assert "knowledge/topics" not in template_text

    spec_text = (repo_root / "SPEC.md").read_text(encoding="utf-8")
    assert "topics" not in spec_text.split("knowledge/{")[1].split("}")[0] if "knowledge/{" in spec_text else True

    readme_text = (repo_root / "README.md").read_text(encoding="utf-8")
    assert "{topics," not in readme_text


def test_methodology_and_phantom_folders_invariants():
    """Verify Methodology is ignored and not falsely tracked as a repo room."""
    repo_root = ROOT
    gitignore_text = (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert "Methodology/" in gitignore_text, "Methodology/ must be ignored in .gitignore"
    assert "knowledge/combinations" not in gitignore_text, "phantom knowledge/combinations must not be in .gitignore"
    assert "\nindex/\n" not in gitignore_text, "phantom index/ must not be in .gitignore"

    claude_text = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
    assert "- /Methodology" not in claude_text, "Methodology must not be listed as a tracked room in CLAUDE.md"
    assert "├── /Methodology" not in claude_text, "Methodology must not be in Directory Map in CLAUDE.md"

    agents_text = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    assert "- /Methodology" not in agents_text, "Methodology must not be listed as a tracked room in AGENTS.md"

    refs_text = (repo_root / "REFERENCES.md").read_text(encoding="utf-8")
    assert "](Methodology/" not in refs_text, "REFERENCES.md must not link to private untracked files"


def test_plain_english_invariants():
    """Verify legacy jargon like 'Room', 'phase-gate', and 'Completion Gate' are eliminated."""
    repo_root = ROOT
    claude_text = (repo_root / "CLAUDE.md").read_text(encoding="utf-8")
    assert '"Room"' not in claude_text
    assert "Tooling Room" not in claude_text
    assert "Folder Structure (The Map)" not in claude_text

    agents_text = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
    assert '"Room"' not in agents_text

    issue_tpl = (repo_root / ".github" / "ISSUE_TEMPLATE.md").read_text(encoding="utf-8")
    assert "Completion Gate" not in issue_tpl
    assert "phase task" not in issue_tpl
    assert "phase-gate" not in issue_tpl

    pr_tpl = (repo_root / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    assert "phase-gate" not in pr_tpl
    assert "Acceptance Criteria Verification" in pr_tpl
    assert "resolves #<issue-number>" in pr_tpl
    assert pr_tpl.strip().endswith("resolves #<issue-number>")



