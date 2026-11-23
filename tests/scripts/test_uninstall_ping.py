"""Uninstalling an upgraded installation never sends analytics."""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SH = os.path.join(REPO, "scripts", "uninstall.sh")
PS1 = os.path.join(REPO, "scripts", "uninstall.ps1")

pytestmark = pytest.mark.skipif(
    sys.platform.startswith("win"), reason="bash script is macOS/Linux-only"
)


def _run(tmp_path, *args, consented=True, with_info=True):
    """Run uninstall.sh in a throwaway HOME with a curl shim on PATH."""
    home = tmp_path / "home"
    data = tmp_path / "data"
    data.mkdir(parents=True)
    home.mkdir(parents=True)
    (data / "prefs.json").write_text(
        json.dumps({"analytics_enabled": bool(consented), "analytics_prompted": True})
    )
    if with_info:
        (data / "analytics_info.json").write_text(
            json.dumps(
                {
                    "site": "testsite12345",
                    "host": "https://app.supermetry.com",
                    "appUrl": "https://app.voicestudio.sh",
                    "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 VoiceStudio/1.0",
                    "policy": "opt-in",
                    "profile_id": "install_11111111222233334444555555555555",
                    "app_version": "0.3.23",
                    "platform": "macos",
                },
                indent=2,
            )
        )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl_log = tmp_path / "curl_args.txt"
    shim = bin_dir / "curl"
    shim.write_text(f'#!/bin/sh\nprintf \'%s\\n\' "$@" >> "{curl_log}"\nexit 0\n')
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC)

    env = dict(os.environ)
    env.update(
        {
            "HOME": str(home),
            "OMNIVOICE_DATA_DIR": str(data),
            # Keep the shared-model-cache branch inert and inside the sandbox.
            "OMNIVOICE_CACHE_DIR": str(tmp_path / "models-nonexistent"),
            "PATH": f"{bin_dir}:{env.get('PATH', '')}",
        }
    )
    proc = subprocess.run(
        ["bash", SH, *args], capture_output=True, text=True, env=env, timeout=60
    )
    curl_args = curl_log.read_text(encoding="utf-8") if curl_log.exists() else ""
    return proc, curl_args


def test_bash_syntax_is_valid():
    subprocess.run(["bash", "-n", SH], check=True)


def test_consented_delete_ignores_saved_analytics_and_removes_data(tmp_path):
    proc, curl = _run(tmp_path, "--yes")
    assert proc.returncode == 0, proc.stderr
    assert not (tmp_path / "data").exists()
    assert curl == ""
    assert "uninstall ping" not in proc.stdout.lower()


def test_not_consented_sends_nothing_and_prints_nothing(tmp_path):
    proc, curl = _run(tmp_path, "--yes", consented=False)
    assert proc.returncode == 0, proc.stderr
    assert curl == ""
    assert "uninstall ping" not in proc.stdout.lower()


def test_missing_info_file_sends_nothing_even_if_prefs_claim_consent(tmp_path):
    """analytics_info.json only exists while the backend had consent AND a
    token — a hand-edited prefs.json alone must not produce a ping (there is
    no destination to send to)."""
    proc, curl = _run(tmp_path, "--yes", consented=True, with_info=False)
    assert proc.returncode == 0, proc.stderr
    assert curl == ""
    assert "uninstall ping" not in proc.stdout.lower()


def test_dry_run_never_pings_even_when_consented(tmp_path):
    proc, curl = _run(tmp_path)  # no --yes
    assert proc.returncode == 0, proc.stderr
    assert "DRY RUN" in proc.stdout
    assert curl == ""
    assert "uninstall ping" not in proc.stdout.lower()


def test_data_is_still_deleted_after_the_ping(tmp_path):
    _run(tmp_path, "--yes")
    assert not (tmp_path / "data").exists()


# ── uninstall.ps1: static contract checks (PowerShell isn't runnable here) ──


def _ps1_source() -> str:
    with open(PS1, encoding="utf-8") as f:
        return f.read()


def test_power_shell_has_no_uninstall_reporting():
    with open(PS1, encoding="utf-8") as f:
        source = f.read()
    assert "analytics_info.json" not in source
    assert "app_uninstalled" not in source
