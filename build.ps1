# build.ps1 - local one-click build (PyInstaller + Inno Setup)
# usage: .\build.ps1 [-Version 3.0.0.0]
param([string]$Version = "")

# NOTE: PS 5.1 turns native stderr lines into terminating errors under
# ErrorActionPreference=Stop; keep Continue and check exit codes instead.
$ErrorActionPreference = "Continue"

function Invoke-Step([string]$label, [scriptblock]$cmd) {
  & $cmd
  if ($LASTEXITCODE -ne 0) { throw "$label failed (exit $LASTEXITCODE)" }
}

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $root

if (-not $Version) {
  $Version = (& .\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'.'); from app.version import VERSION; print(VERSION)")
}
Write-Output "building version $Version"

# 1) python deps
if (-not (Test-Path .\.venv\Scripts\python.exe)) {
  Invoke-Step "venv" { python -m venv .venv }
}
Invoke-Step "pip" { .\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller }

# 2) PyInstaller
Invoke-Step "pyinstaller" { .\.venv\Scripts\python.exe -m PyInstaller --noconfirm CountdownDesktop.spec }

# 3) locate ISCC (Inno Setup 6/7)
$iscc = $null
foreach ($p in @(
  "C:\Program Files\Inno Setup 7\ISCC.exe",
  "C:\Program Files\Inno Setup 6\ISCC.exe",
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
  "C:\Program Files (x86)\Inno Setup 5\ISCC.exe")) {
  if (Test-Path $p) { $iscc = $p; break }
}
if (-not $iscc) {
  $found = Get-ChildItem "C:\Program Files","C:\Program Files (x86)" -Filter ISCC.exe -Recurse -Depth 2 -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($found) { $iscc = $found.FullName }
}
if (-not $iscc) { throw "ISCC.exe not found; install Inno Setup first" }
Write-Output "using $iscc"

Invoke-Step "iscc" { & $iscc /DVERSION=$Version installer\setup.iss }

Write-Output "done: CountdownDesktop_Setup_$Version.exe"
Pop-Location
