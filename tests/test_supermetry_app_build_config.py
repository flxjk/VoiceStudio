"""Verify that every packaging path ignores external reporting configuration."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("intake_build", ROOT / "scripts/generate_supermetry_config.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def node_config(env):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for Electron build configuration")
    result = subprocess.run([node, "--input-type=module", "-e", "import {generatedSupermetryConfig} from './config/supermetry-app.mjs';process.stdout.write(JSON.stringify(generatedSupermetryConfig()));"],
        cwd=ROOT, env={**os.environ, **env}, capture_output=True, text=True, check=True)
    assert not result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("host", ["https://collector.example", "http://127.0.0.1:7777", ""])
def test_build_metadata_ignores_external_intake_environment(host, monkeypatch):
    env = {
        "SUPERMETRY_APP_ID": "fixtureapp123",
        "SUPERMETRY_INGEST_KEY": "smk_" + "a" * 39,
        "SUPERMETRY_APP_HOST": host,
        "SUPERMETRY_DIAGNOSTICS_SESSION_PINGS": "1",
    }
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    assert build.generated_config() == node_config(env) == {"diagnostics": {"sessionPings": False}}


def test_cli_never_prints_key_and_credential_free_rebuild_erases_old_metadata(tmp_path):
    output = tmp_path / "supermetry-app.generated.json"
    env = {key: value for key, value in os.environ.items() if not key.startswith("SUPERMETRY_")}
    key = "smk_" + "b" * 39
    build.write_config(output)
    output.write_text(json.dumps({"ingest_key": key}), encoding="utf-8")
    with_key = subprocess.run([shutil.which("python3") or "python", str(ROOT / "scripts/generate_supermetry_config.py"), "--output", str(output)], env={**env, "SUPERMETRY_APP_ID": "fixtureapp123", "SUPERMETRY_INGEST_KEY": key}, capture_output=True, text=True, check=True)
    assert not with_key.stdout and not with_key.stderr
    assert json.loads(output.read_text(encoding="utf-8")) == {"diagnostics": {"sessionPings": False}}
    if os.name != "nt":
        assert output.stat().st_mode & 0o777 == 0o600


def test_generated_config_is_git_ignored_and_excluded_from_web_and_preload_defines():
    ignored = subprocess.run(["git", "check-ignore", "config/supermetry-app.generated.json"], cwd=ROOT, capture_output=True, text=True)
    assert ignored.returncode == 0
    assert "config/supermetry-app.generated.json" in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    source = (ROOT / "electron/electron.vite.config.ts").read_text(encoding="utf-8")
    shared = source.split("const define = {", 1)[1].split("};", 1)[0]
    assert "SUPERMETRY" not in shared
    assert "__SUPERMETRY_APP_CONFIG__" in source.split("main: {", 1)[1].split("preload: {", 1)[0]


def test_workflows_never_supply_external_reporting_configuration():
    for workflow in (ROOT / ".github/workflows").glob("*.yml"):
        source = workflow.read_text(encoding="utf-8")
        assert "SUPERMETRY_" not in source, workflow.name
