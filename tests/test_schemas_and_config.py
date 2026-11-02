#!/usr/bin/env python3
"""Validation tests for configuration templates, schemas, and controlled vocabulary."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import oss_config  # noqa: E402


def test_capabilities_schema():
    """Verify capabilities.yaml loads properly and contains expected core features."""
    caps = oss_config.get_capabilities()
    assert isinstance(caps, dict), "capabilities must load as a dict"
    assert len(caps) > 50, f"expected >50 capabilities, got {len(caps)}"
    for key in ["ci-integration", "code-review", "release-automation", "static-analysis"]:
        assert key in caps, f"missing expected capability: {key}"


def test_disposition_options():
    """Verify all 8 documented dispositions are returned."""
    expected = [
        "independent",
        "too_big",
        "adopt",
        "merge",
        "upstream_pr",
        "simplify_fork",
        "combined",
        "rejected",
    ]
    disps = oss_config.get_dispositions()
    for disp in expected:
        assert disp in disps, f"expected {disp} in dispositions: {disps}"


def test_config_example_template():
    """Verify config.example.yaml can be parsed cleanly by the stdlib parser."""
    cfg = oss_config.load_file(oss_config.EXAMPLE)
    assert isinstance(cfg, dict), "config.example.yaml must parse as a dict"
    assert "categories" in cfg, "config.example.yaml must define categories"


def test_criteria_schema():
    """Verify criteria.yaml parses cleanly."""
    crit = oss_config.load_file(oss_config.CRITERIA)
    assert isinstance(crit, dict), "criteria.yaml must parse as a dict"
    assert "worthiness" in crit or "standards" in crit or "funnel" in crit, (
        "criteria.yaml must contain core framework sections"
    )
