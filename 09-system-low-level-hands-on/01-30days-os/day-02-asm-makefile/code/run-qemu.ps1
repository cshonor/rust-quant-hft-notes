# 用本机 QEMU 启动 helloos.img
# 默认 QEMU：D:\qemu\qemu-system-i386.exe（与 Day 1 §1.1.5 一致）
# 用法：.\run-qemu.ps1
# 环境变量：$env:QEMU = "D:\qemu\qemu-system-i386.exe" 可覆盖

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$img = Join-Path $here 'helloos.img'
$qemu = if ($env:QEMU) { $env:QEMU } else { 'D:\qemu\qemu-system-i386.exe' }

if (-not (Test-Path $img)) {
    Write-Error "Missing helloos.img — run: nasm -f bin helloos.asm -o ipl.bin; then .\build-img.ps1"
}
if (-not (Test-Path $qemu)) {
    Write-Error "QEMU not found at $qemu — install to D:\qemu or set `$env:QEMU"
}

# 工作目录勿用 QEMU 安装目录；用 D:\haribote 或 code 目录（与 Day 1 排错一致）
$workDir = if (Test-Path 'D:\haribote') { 'D:\haribote' } else { $here }

Write-Host "QEMU: $qemu"
Write-Host "Image: $img"
Write-Host "Cwd:  $workDir"
Write-Host "Close the QEMU window to exit."

Start-Process -FilePath $qemu -ArgumentList '-fda', $img, '-boot', 'a' -WorkingDirectory $workDir
