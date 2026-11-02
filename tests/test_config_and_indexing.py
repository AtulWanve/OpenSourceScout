#!/usr/bin/env python3
"""Tests for configuration fallback and dynamic disposition indexing."""
import sys
from pathlib import Path

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
