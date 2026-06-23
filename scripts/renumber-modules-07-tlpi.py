#!/usr/bin/env python3
"""Insert 07-The-Linux-Programming-Interface; shift 07-14 to 08-15."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REPLACEMENTS = [
    ("14-Rust-Quant-Trading-Guide", "15-Rust-Quant-Trading-Guide"),
    ("13-HFT-Low-Latency-Practice", "14-HFT-Low-Latency-Practice"),
    ("12-DPDK-Low-Latency-Network", "13-DPDK-Low-Latency-Network"),
    ("11-Linux-Kernel-Networking", "12-Linux-Kernel-Networking"),
    ("10-TCP-IP-Illustrated-Vol1", "11-TCP-IP-Illustrated-Vol1"),
    ("09-UNP-Vol1", "10-UNP-Vol1"),
    ("08-Practical-Network-Programming", "09-Practical-Network-Programming"),
    ("07-system-low-level-hands-on", "08-system-low-level-hands-on"),
]

SKIP = {".git", "node_modules", ".cursor", "07-The-Linux-Programming-Interface"}


def main():
    n = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".mdc", ".py"}:
            continue
        if any(p in path.parts for p in SKIP):
            continue
        if "renumber-modules" in path.name:
            continue
        text = path.read_text(encoding="utf-8")
        orig = text
        for old, new in REPLACEMENTS:
            text = text.replace(old, new)
        if text != orig:
            path.write_text(text, encoding="utf-8")
            n += 1
    print(f"Updated {n} files")


if __name__ == "__main__":
    main()
