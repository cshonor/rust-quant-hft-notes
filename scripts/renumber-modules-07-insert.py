#!/usr/bin/env python3
"""Renumber repo module paths after inserting 07-system-low-level-hands-on."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Apply in order: highest old number first to avoid double-replace
REPLACEMENTS = [
    ("12-Rust-Quant-Trading-Guide", "13-Rust-Quant-Trading-Guide"),
    ("11-HFT-Low-Latency-Practice", "12-HFT-Low-Latency-Practice"),
    ("10-DPDK-Low-Latency-Network", "11-DPDK-Low-Latency-Network"),
    ("09-Linux-Kernel-Networking", "10-Linux-Kernel-Networking"),
    ("08-UNP-Vol1", "09-UNP-Vol1"),
    ("07-TCP-IP-Illustrated-Vol1", "08-TCP-IP-Illustrated-Vol1"),
]

TEXT_REPLACEMENTS = [
    ("`07`–`10`", "`08`–`11`"),
    ("07–10", "08–11"),
    ("`07`→`10`", "`08`→`11`"),
    ("07→08→09→10", "08→09→10→11"),
    ("07 → 08 → 09 → 10", "08 → 09 → 10 → 11"),
    ("07 → 08 → 09", "08 → 09 → 10"),
    ("`05`–`10`", "`05`–`11`"),
    ("05–10", "05–11"),
    ("`11` HFT", "`12` HFT"),
    ("`12` Rust", "`13` Rust"),
    ("文件夹 11", "文件夹 12"),
    ("文件夹 12", "文件夹 13"),
    ("文件夹 `11`", "文件夹 `12`"),
    ("文件夹 `12`", "文件夹 `13`"),
    ("`11`/`12`", "`12`/`13`"),
    ("11-HFT", "12-HFT"),
    ("12-Rust", "13-Rust"),
    ("`00`–`12`", "`00`–`13`"),
    ("00`–`12`", "00`–`13`"),
    ("`00-` ~ `12-`", "`00-` ~ `13-`"),
    ("00-` ~ `12-", "00-` ~ `13-"),
    ("封顶（`00`–`12`）", "封顶（`00`–`13`）"),
    ("`10` DPDK", "`11` DPDK"),
    ("`10` 文件夹", "`11` 文件夹"),
    ("与 `10` 映射", "与 `12` 映射"),
    ("与 11 映射", "与 12 映射"),
    ("与 10 映射", "与 12 映射"),
    ("L5  10-HFT + 11-Rust", "L5  12-HFT + 13-Rust"),
    ("11  HFT Practice", "12  HFT Practice"),
    ("12  Rust Guide", "13  Rust Guide"),
    ("→ 11 HFT", "→ 12 HFT"),
    ("→ 12 Rust", "→ 13 Rust"),
]

SKIP_DIRS = {".git", "node_modules", ".cursor"}


def should_process(path: Path) -> bool:
    if any(p in path.parts for p in SKIP_DIRS):
        return False
    return path.suffix in {".md", ".mdc", ".py", ".txt"}


def main():
    changed = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or not should_process(path):
            continue
        if path.name == Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8")
        orig = text
        for old, new in REPLACEMENTS:
            text = text.replace(old, new)
        for old, new in TEXT_REPLACEMENTS:
            text = text.replace(old, new)
        if text != orig:
            path.write_text(text, encoding="utf-8")
            changed += 1
            print(path.relative_to(ROOT))
    print(f"Updated {changed} files")


if __name__ == "__main__":
    main()
