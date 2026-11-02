#!/usr/bin/env python3
"""Self-check test for OpenCode CLI integration in judge_loop."""
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import judge_loop  # noqa: E402, F401
from judge_loop import DEFAULTS, LimitReached, build_context, run_backend  # noqa: E402


def test_defaults_structure():
    assert "--auto" not in DEFAULTS["opencode_cmd"], "opencode_cmd must not auto-approve permissions"
    assert isinstance(DEFAULTS.get("opencode_model"), str) and DEFAULTS.get("opencode_model").startswith("opencode/"), "opencode_model must be a valid opencode provider string"
    markers = DEFAULTS["limit_markers"]
    assert "insufficient account funds" in markers, "limit_markers must catch insufficient account funds"
    assert "insufficient funds" in markers, "limit_markers must catch insufficient funds"


def test_build_context_includes_model():
    ctx = build_context()
    assert "model" in ctx, "build_context() must expose model key from config"


def test_run_backend_opencode_explicit_model():
    with patch("judge_loop.sh") as mock_sh:
        mock_sh.return_value = (0, '```json\n{"conclusion": "test"}\n```', "")
        run_backend("opencode", None, "prompt text", timeout=10)

        cmd = mock_sh.call_args[0][0]
        assert "--auto" not in cmd, "Subprocess cmd must not auto-approve permissions"
        assert "--model" in cmd, "Subprocess cmd must pass --model"
        idx = cmd.index("--model")
        assert cmd[idx + 1] == DEFAULTS["opencode_model"], "Should fall back to default contributor model"


def test_run_backend_billing_limit_detection():
    with patch("judge_loop.sh") as mock_sh:
        mock_sh.return_value = (1, "", "Error: Upstream request failed: Insufficient account funds")
        try:
            run_backend("opencode", None, "prompt text", timeout=10)
            assert False, "Expected LimitReached exception on insufficient funds"
        except LimitReached as e:
            assert "limit" in str(e).lower()


if __name__ == "__main__":
    test_defaults_structure()
    test_build_context_includes_model()
    test_run_backend_opencode_explicit_model()
    test_run_backend_billing_limit_detection()
    print("ALL TESTS PASSED")
