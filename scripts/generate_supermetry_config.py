#!/usr/bin/env python3
"""Write credential-free diagnostic metadata for fork builds."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generated_config():
    return {"diagnostics": {"sessionPings": False}}


def write_config(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # O_TRUNC replaces metadata on every build, including credential-free builds.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(generated_config(), stream, separators=(",", ":"))
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "config/supermetry-app.generated.json")
    write_config(parser.parse_args().output)
