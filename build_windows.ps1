param(
    [switch]$SkipInstall,
    [switch]$SkipRust,
    [string]$CertificateThumbprint = $env:TECHGUY_SIGNING_CERT_THUMBPRINT
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Assert-File([string]$Path, [string]$Label) {
    if (-not (Test-Path $Path) -or (Get-Item $Path).Length -le 0) {
        throw "$Label missing or empty: $Path"
    }
}

Write-Host "TECHGUY TOOL Huawei one-file release" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.11+ is required."
}

if (-not $SkipInstall) {
    python -m pip install --upgrade pip
    python -m pip install -e ".[test]" pyside6-deploy
}

if (-not $SkipRust) {
    if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
        throw "Rust/Cargo is required for the release health core. Use -SkipRust only for UI development builds."
    }
    cargo build --manifest-path "rust\health_core\Cargo.toml" --release
    if ($LASTEXITCODE -ne 0) { throw "Rust health core build failed." }
    New-Item -ItemType Directory -Force "runtime\health" | Out-Null
    Copy-Item "rust\health_core\target\release\techguy_health_core.exe" "runtime\health\techguy_health_core.exe" -Force
    Assert-File "runtime\health\techguy_health_core.exe" "Rust health core"
}

python tools\generate_icon.py
if ($LASTEXITCODE -ne 0) { throw "Application icon generation failed." }
Assert-File "assets\brand\techguy_huawei.ico" "Generated Windows icon"
python tools\generate_qrc.py
if ($LASTEXITCODE -ne 0) { throw "Qt resource generation failed." }
python -m pytest
if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
python tools\review_20_for_2.py --strict
if ($LASTEXITCODE -ne 0) { throw "20-for-2 review failed." }

python -m PySide6.scripts.pyside_tool rcc resources.qrc -o techguy_huawei\resources_rc.py
if ($LASTEXITCODE -ne 0) {
    pyside6-rcc resources.qrc -o techguy_huawei\resources_rc.py
    if ($LASTEXITCODE -ne 0) { throw "pyside6-rcc failed." }
}
Assert-File "techguy_huawei\resources_rc.py" "Compiled Qt resources"

if (Test-Path dist) { Remove-Item dist -Recurse -Force }
pyside6-deploy -c pysidedeploy.spec -f
if ($LASTEXITCODE -ne 0) { throw "pyside6-deploy failed." }

$Exe = Get-ChildItem -Path dist -Filter "TECHGUYTOOL_Huawei.exe" -Recurse | Select-Object -First 1
if (-not $Exe) { throw "TECHGUYTOOL_Huawei.exe was not produced." }

if ($CertificateThumbprint) {
    $SignTool = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if (-not $SignTool) { throw "Signing thumbprint was supplied, but signtool.exe is unavailable." }
    & $SignTool.Source sign /sha1 $CertificateThumbprint /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $Exe.FullName
    if ($LASTEXITCODE -ne 0) { throw "Code signing failed." }
} else {
    Write-Warning "No signing certificate thumbprint supplied. The executable is verified but unsigned."
}

$Hash = Get-FileHash -Algorithm SHA256 $Exe.FullName
"$($Hash.Hash.ToLowerInvariant())  $($Exe.Name)" | Set-Content -Encoding ASCII (Join-Path $Exe.DirectoryName "SHA256SUMS.txt")
Write-Host "Release ready: $($Exe.FullName)" -ForegroundColor Green
