$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonw = Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\pythonw.exe"
$main = Join-Path $root "main.py"
if (-not (Test-Path -LiteralPath $pythonw)) { throw "ATHENA Python 3.10 was not found." }
if (-not (Test-Path -LiteralPath $main)) { throw "Huawei main.py was not found." }
$existing = Get-Process -Name pythonw -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowTitle -like "*TECHGUY TOOL*HUAWEI*" } |
    Select-Object -First 1
if ($existing) {
    [void](New-Object -ComObject WScript.Shell).AppActivate([int]$existing.Id)
    exit 0
}
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:QT_QUICK_CONTROLS_STYLE = "Basic"
$env:TECHGUY_STARTUP_DIAGNOSTIC_PATH = (Join-Path $root ".workspace\evidence\main_huawei_launcher_startup.json")
Start-Process -FilePath $pythonw -ArgumentList ('"' + $main + '"') -WorkingDirectory $root
