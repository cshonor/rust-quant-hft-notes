#!/usr/bin/env python3
"""Insert 17-cpp-learning-notes at 08; shift 08-16 -> 09-17.

  17 cpp  -> 08
  08 PNP  -> 09
  09 UNP  -> 10
  10 TCP  -> 11
  11 Rosen-> 12
  12 DPDK -> 13
  13 SysPerf -> 14
  14 BPF  -> 15
  15 HFT  -> 16
  16 Rust -> 17

Run: py scripts/renumber-modules-17-to-08.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GIT_MV_TO_TMP = [
    ("16-Rust-Quant-Trading-Guide", "_tmp-i8-17-rust"),
    ("15-HFT-Low-Latency-Practice", "_tmp-i8-16-hft"),
    ("14-BPF-Performance-Tools", "_tmp-i8-15-bpf"),
    ("13-Systems-Performance-2nd", "_tmp-i8-14-sysperf"),
    ("12-DPDK-Low-Latency-Network", "_tmp-i8-13-dpdk"),
    ("11-Linux-Kernel-Networking", "_tmp-i8-12-rosen"),
    ("10-TCP-IP-Illustrated-Vol1", "_tmp-i8-11-tcpip"),
    ("09-UNP-Vol1", "_tmp-i8-10-unp"),
    ("08-Practical-Network-Programming", "_tmp-i8-09-pnp"),
    ("17-cpp-learning-notes", "_tmp-i8-08-cpp"),
]

GIT_MV_TO_FINAL = [
    ("_tmp-i8-08-cpp", "08-cpp-learning-notes"),
    ("_tmp-i8-09-pnp", "09-Practical-Network-Programming"),
    ("_tmp-i8-10-unp", "10-UNP-Vol1"),
    ("_tmp-i8-11-tcpip", "11-TCP-IP-Illustrated-Vol1"),
    ("_tmp-i8-12-rosen", "12-Linux-Kernel-Networking"),
    ("_tmp-i8-13-dpdk", "13-DPDK-Low-Latency-Network"),
    ("_tmp-i8-14-sysperf", "14-Systems-Performance-2nd"),
    ("_tmp-i8-15-bpf", "15-BPF-Performance-Tools"),
    ("_tmp-i8-16-hft", "16-HFT-Low-Latency-Practice"),
    ("_tmp-i8-17-rust", "17-Rust-Quant-Trading-Guide"),
]

PATH_SWAP = [
    ("16-Rust-Quant-Trading-Guide", "@@M17-RUST@@"),
    ("15-HFT-Low-Latency-Practice", "@@M16-HFT@@"),
    ("14-BPF-Performance-Tools", "@@M15-BPF@@"),
    ("13-Systems-Performance-2nd", "@@M14-SYSPERF@@"),
    ("12-DPDK-Low-Latency-Network", "@@M13-DPDK@@"),
    ("11-Linux-Kernel-Networking", "@@M12-ROSEN@@"),
    ("10-TCP-IP-Illustrated-Vol1", "@@M11-TCPIP@@"),
    ("09-UNP-Vol1", "@@M10-UNP@@"),
    ("08-Practical-Network-Programming", "@@M09-PNP@@"),
    ("17-cpp-learning-notes", "@@M08-CPP@@"),
]

PLACEHOLDER_TO_NEW = [
    ("@@M17-RUST@@", "17-Rust-Quant-Trading-Guide"),
    ("@@M16-HFT@@", "16-HFT-Low-Latency-Practice"),
    ("@@M15-BPF@@", "15-BPF-Performance-Tools"),
    ("@@M14-SYSPERF@@", "14-Systems-Performance-2nd"),
    ("@@M13-DPDK@@", "13-DPDK-Low-Latency-Network"),
    ("@@M12-ROSEN@@", "12-Linux-Kernel-Networking"),
    ("@@M11-TCPIP@@", "11-TCP-IP-Illustrated-Vol1"),
    ("@@M10-UNP@@", "10-UNP-Vol1"),
    ("@@M09-PNP@@", "09-Practical-Network-Programming"),
    ("@@M08-CPP@@", "08-cpp-learning-notes"),
]

PROSE_REPLACEMENTS = [
    ("00 → 01 → 02 → 03 → 04 → 05 → 06 → 07/01 → 17 → 08 → 09 → 01网络 → 10 → 11 → 12 → 13 → 14 → 15 → 16",
     "00 → 01 → 02 → 03 → 04 → 05 → 06 → 07/01 → 08 → 09 → 01网络 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17"),
    ("→ 07 MikanOS/30天OS → **17 C++（外部仓）** → 08 陈硕 PNP/muduo → 09 UNP",
     "→ 07 MikanOS/30天OS → **08 C++** → 09 陈硕 PNP/muduo → 10 UNP"),
    ("→ 10 TCP/IP → 11 Rosen → 12 DPDK",
     "→ 11 TCP/IP → 12 Rosen → 13 DPDK"),
    ("→ 13 SysPerf → 14 BPF",
     "→ 14 SysPerf → 15 BPF"),
    ("→ 15 HFT 工程 → 16 Rust 量化",
     "→ 16 HFT 工程 → 17 Rust 量化"),
    ("17  C++ · [cpp-learning-notes]", "08  C++ · [cpp-learning-notes]"),
    ("08  陈硕 PNP / muduo", "09  陈硕 PNP / muduo"),
    ("09  UNP", "10  UNP"),
    ("10  TCP/IP → 11 Rosen → 12 DPDK", "11  TCP/IP → 12 Rosen → 13 DPDK"),
    ("13  SysPerf → 14 BPF", "14  SysPerf → 15 BPF"),
    ("15  HFT Practice", "16  HFT Practice"),
    ("16  Rust Guide", "17  Rust Guide"),
    ("`17` C++", "`08` C++"),
    ("**17 C++（外部仓）**", "**08 C++**"),
    ("`17` C++（开 PNP 前）", "`08` C++（开 PNP 前）"),
    ("**17 C++（开 PNP 前）**", "**08 C++（开 PNP 前）**"),
    ("17-cpp-learning-notes", "08-cpp-learning-notes"),
    ("17-cpp", "08-cpp"),
    ("外部 C++ 索引 `17`", "C++ `08`"),
    ("+ 外部 C++ 索引 `17`", ""),
    ("`00`–`16` + 外部 C++ 索引 `17`", "`00`–`17`"),
    ("`00`–`16` = 物理编号", "`00`–`17` = 物理编号"),
    ("15–16      15–16", "16–17      16–17"),
    ("13–14      15–16", "14–15      16–17"),
    ("08–12    13–14      15–16", "09–13    14–15      16–17"),
    ("08–12 网络", "09–13 网络"),
    ("08–12 网络栈", "09–13 网络栈"),
    ("08–12 网络/DPDK", "09–13 网络/DPDK"),
    ("08 PNP → 09 UNP → 10–12", "09 PNP → 10 UNP → 11–13"),
    ("08 PNP / muduo", "09 PNP / muduo"),
    ("08 陈硕 PNP", "09 陈硕 PNP"),
    ("08-Practical-Network-Programming", "09-Practical-Network-Programming"),
    ("09-UNP-Vol1", "10-UNP-Vol1"),
    ("10-TCP-IP-Illustrated-Vol1", "11-TCP-IP-Illustrated-Vol1"),
    ("11-Linux-Kernel-Networking", "12-Linux-Kernel-Networking"),
    ("12-DPDK-Low-Latency-Network", "13-DPDK-Low-Latency-Network"),
    ("13-Systems-Performance-2nd", "14-Systems-Performance-2nd"),
    ("14-BPF-Performance-Tools", "15-BPF-Performance-Tools"),
    ("15-HFT-Low-Latency-Practice", "16-HFT-Low-Latency-Practice"),
    ("16-Rust-Quant-Trading-Guide", "17-Rust-Quant-Trading-Guide"),
    ("../08-Practical", "../09-Practical"),
    ("../09-UNP", "../10-UNP"),
    ("../10-TCP", "../11-TCP"),
    ("../11-Linux-Kernel-Networking", "../12-Linux-Kernel-Networking"),
    ("../12-DPDK", "../13-DPDK"),
    ("../13-Systems-Performance", "../14-Systems-Performance"),
    ("../14-BPF", "../15-BPF"),
    ("../15-HFT", "../16-HFT"),
    ("../16-Rust", "../17-Rust"),
    ("../17-cpp", "../08-cpp"),
    ("../../08-Practical", "../../09-Practical"),
    ("../../09-UNP", "../../10-UNP"),
    ("../../10-TCP", "../../11-TCP"),
    ("../../11-Linux-Kernel-Networking", "../../12-Linux-Kernel-Networking"),
    ("../../12-DPDK", "../../13-DPDK"),
    ("../../13-Systems-Performance", "../../14-Systems-Performance"),
    ("../../14-BPF", "../../15-BPF"),
    ("../../15-HFT", "../../16-HFT"),
    ("../../16-Rust", "../../17-Rust"),
    ("../../17-cpp", "../../08-cpp"),
    ("../../../08-Practical", "../../../09-Practical"),
    ("../../../09-UNP", "../../../10-UNP"),
    ("../../../10-TCP", "../../../11-TCP"),
    ("../../../11-Linux-Kernel-Networking", "../../../12-Linux-Kernel-Networking"),
    ("../../../12-DPDK", "../../../13-DPDK"),
    ("../../../13-Systems-Performance", "../../../14-Systems-Performance"),
    ("../../../14-BPF", "../../../15-BPF"),
    ("../../../15-HFT", "../../../16-HFT"),
    ("../../../16-Rust", "../../../17-Rust"),
    ("../../../17-cpp", "../../../08-cpp"),
    ("../../../../08-Practical", "../../../../09-Practical"),
    ("../../../../09-UNP", "../../../../10-UNP"),
    ("../../../../10-TCP", "../../../../11-TCP"),
    ("../../../../11-Linux-Kernel-Networking", "../../../../12-Linux-Kernel-Networking"),
    ("../../../../12-DPDK", "../../../../13-DPDK"),
    ("../../../../13-Systems-Performance", "../../../../14-Systems-Performance"),
    ("../../../../14-BPF", "../../../../15-BPF"),
    ("../../../../15-HFT", "../../../../16-HFT"),
    ("../../../../16-Rust", "../../../../17-Rust"),
    ("../../../../17-cpp", "../../../../08-cpp"),
    ("[08-Practical", "[09-Practical"),
    ("[09-UNP", "[10-UNP"),
    ("[10-TCP", "[11-TCP"),
    ("[11-Linux-Kernel-Networking", "[12-Linux-Kernel-Networking"),
    ("[12-DPDK", "[13-DPDK"),
    ("[13-Systems-Performance", "[14-Systems-Performance"),
    ("[14-BPF", "[15-BPF"),
    ("[15-HFT", "[16-HFT"),
    ("[16-Rust", "[17-Rust"),
    ("[17-cpp", "[08-cpp"),
    ("| **08** | [Practical", "| **09** | [Practical"),
    ("| **09** | [UNP", "| **10** | [UNP"),
    ("| **10** | [TCP", "| **11** | [TCP"),
    ("| **11** | [Linux-Kernel-Networking", "| **12** | [Linux-Kernel-Networking"),
    ("| **12** | [DPDK", "| **13** | [DPDK"),
    ("| **13** | [Systems-Performance", "| **14** | [Systems-Performance"),
    ("| **14** | [BPF", "| **15** | [BPF"),
    ("| **15** | [HFT", "| **16** | [HFT"),
    ("| **16** | [Rust", "| **17** | [Rust"),
    ("| **17** | [**cpp", "| **08** | [cpp"),
    ("`12` DPDK → `13`–`14` → `15` HFT", "`13` DPDK → `14`–`15` → `16` HFT"),
    ("`13`/`14` 在 `12` DPDK 之后", "`14`/`15` 在 `13` DPDK 之后"),
    ("| **13** | [SysPerf]", "| **14** | [SysPerf]"),
    ("| **14** | [BPF Tools]", "| **15** | [BPF Tools]"),
    ("| **15–16** | HFT / Rust", "| **16–17** | HFT / Rust"),
    ("| **08–12** | PNP", "| **09–13** | PNP"),
    ("13 SysPerf → 14 BPF", "14 SysPerf → 15 BPF"),
    ("15 HFT", "16 HFT"),
    ("07 之后、08 PNP 之前", "07 之后、09 PNP 之前（`08` C++）"),
    ("09 之后、10 前", "08 之后、09 前"),
    ("09 之后、10 PNP 之前", "08 之后、09 PNP 之前"),
    ("`09` 之后、`10` PNP", "`08` 之后、`09` PNP"),
    ("`17` → `10`", "`08` → `09`"),
    ("17 → 10", "08 → 09"),
    ("[12-DPDK", "[13-DPDK"),
    ("12 DPDK", "13 DPDK"),
    ("`12` DPDK", "`13` DPDK"),
    ("13 SysPerf", "14 SysPerf"),
    ("14 BPF", "15 BPF"),
    ("15 HFT", "16 HFT"),
    ("16 Rust", "17 Rust"),
    ("可与 08–09 交叉", "可与 09–10 交叉"),
    ("网络 `10`–`14`", "网络 `09`–`13`"),
    ("工程 `15`–`16`", "工程 `16`–`17`"),
    ("`05`–`09` → **`17` C++", "`05`–`08` → **`08` C++"),
]

SKIP_DIRS = {".git", "node_modules", ".cursor", "__pycache__"}
SKIP_FILES = {"renumber-modules-17-to-08.py"}


def git_mv(src: str, dst: str) -> None:
    r = subprocess.run(["git", "mv", src, dst], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"git mv failed: {src} -> {dst}\n{r.stderr}", file=sys.stderr)
        sys.exit(1)
    print(f"git mv {src} -> {dst}")


def apply_replacements(text: str) -> str:
    for old, new in PATH_SWAP:
        text = text.replace(old, new)
    for old, new in PLACEHOLDER_TO_NEW:
        text = text.replace(old, new)
    for old, new in PROSE_REPLACEMENTS:
        if old in text:
            text = text.replace(old, new)
    return text


def update_text_files() -> int:
    count = 0
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(p in SKIP_DIRS for p in path.parts):
            continue
        if path.name in SKIP_FILES:
            continue
        if path.suffix.lower() not in {".md", ".py", ".mdc", ".txt", ".yml", ".yaml", ".json"}:
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        updated = apply_replacements(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8", newline="\n")
            count += 1
            print(f"updated {path.relative_to(ROOT)}")
    return count


def main() -> None:
    for src, dst in GIT_MV_TO_TMP:
        if (ROOT / src).exists():
            git_mv(src, dst)
        else:
            print(f"skip missing: {src}")
    for src, dst in GIT_MV_TO_FINAL:
        if (ROOT / src).exists():
            git_mv(src, dst)
        else:
            print(f"skip missing: {src}")
    n = update_text_files()
    print(f"\nDone. Updated {n} text files.")


if __name__ == "__main__":
    main()
