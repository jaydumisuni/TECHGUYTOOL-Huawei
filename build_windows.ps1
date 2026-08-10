param(
    [switch]$SkipInstall,
    [switch]$SkipRust,
    [switch]$CiTestSigning,
    [string]$CiTestSigningPfx = $env:TECHGUY_CI_TEST_SIGNING_PFX,
    [string]$CiTestSigningPassword = $env:TECHGUY_CI_TEST_SIGNING_PASSWORD,
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
if ($CiTestSigning -and $env:GITHUB_ACTIONS -ne "true") {
    throw "CI test signing is permitted only inside GitHub Actions."
}
if ($CiTestSigning) {
    if (-not $CiTestSigningPfx -or -not (Test-Path $CiTestSigningPfx)) {
        throw "CI test signing requires an explicit temporary PFX path."
    }
    if (-not $CiTestSigningPassword) {
        throw "CI test signing requires an explicit temporary PFX password."
    }
}

if (-not $SkipInstall) {
    python -m pip install --upgrade pip
    python -m pip install -e ".[test]" "nuitka==2.6.8" ordered_set zstandard
}

# Prove the checked-out source before creating any build/generated files.
python -m pytest
if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
python tools\review_20_for_2.py --strict
if ($LASTEXITCODE -ne 0) { throw "20-for-2 review failed." }

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

$Rcc = Get-Command pyside6-rcc -ErrorAction SilentlyContinue
if (-not $Rcc) { throw "pyside6-rcc is unavailable." }
& $Rcc.Source resources.qrc -o techguy_huawei\resources_rc.py
if ($LASTEXITCODE -ne 0) { throw "pyside6-rcc failed." }
Assert-File "techguy_huawei\resources_rc.py" "Compiled Qt resources"

if (Test-Path dist) { Remove-Item dist -Recurse -Force }
if (Test-Path deployment) { Remove-Item deployment -Recurse -Force }
if (-not (Get-Command pyside6-deploy -ErrorAction SilentlyContinue)) {
    throw "pyside6-deploy was not installed with PySide6."
}
pyside6-deploy -c pysidedeploy.spec -f
if ($LASTEXITCODE -ne 0) { throw "pyside6-deploy failed." }

# pyside6-deploy owns its intermediate executable name (main.exe for main.py).
# Preserve that contract during deployment, then apply the frozen product filename.
$TargetDirectory = Join-Path $Root "dist"
New-Item -ItemType Directory -Force $TargetDirectory | Out-Null
$TargetPath = Join-Path $TargetDirectory "TECHGUYTOOL_Huawei.exe"
$BuiltExe = Get-ChildItem -Path $TargetDirectory -Filter "main.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $BuiltExe) {
    $BuiltExe = Get-ChildItem -Path $TargetDirectory -Filter "TECHGUYTOOL_Huawei.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
}
if (-not $BuiltExe) {
    throw "pyside6-deploy completed but produced no expected one-file executable."
}
if ($BuiltExe.FullName -ne $TargetPath) {
    Move-Item -LiteralPath $BuiltExe.FullName -Destination $TargetPath -Force
}
Assert-File $TargetPath "TECHGUYTOOL_Huawei.exe"
$Exe = Get-Item $TargetPath

$SigningMode = "unsigned"
if ($CiTestSigning -or $CertificateThumbprint) {
    $SignTool = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if (-not $SignTool) { throw "A signing mode was requested, but signtool.exe is unavailable." }
    if ($CiTestSigning) {
        & $SignTool.Source sign /f $CiTestSigningPfx /p $CiTestSigningPassword /fd SHA256 $Exe.FullName
        $SigningMode = "ci-test-authenticode"
    } else {
        & $SignTool.Source sign /sha1 $CertificateThumbprint /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $Exe.FullName
        $SigningMode = "production-authenticode"
    }
    if ($LASTEXITCODE -ne 0) { throw "Code signing failed." }
    $Signature = Get-AuthenticodeSignature $Exe.FullName
    if (-not $Signature.SignerCertificate) {
        throw "Authenticode signer certificate was not present after signing."
    }
    if ($CiTestSigning) {
        if ($Signature.SignerCertificate.Subject -notlike "*THETECHGUY Phase15 CI Test Signing - NOT FOR PRODUCTION*") {
            throw "CI Authenticode signer identity mismatch."
        }
    } elseif ($Signature.Status -ne "Valid") {
        throw "Production Authenticode signature validation failed: $($Signature.Status)"
    }
} else {
    Write-Warning "No signing certificate supplied. The executable is verified but unsigned and is not production-release eligible."
}

$Hash = Get-FileHash -Algorithm SHA256 $Exe.FullName
$ChecksumPath = Join-Path $Exe.DirectoryName "SHA256SUMS.txt"
"$($Hash.Hash.ToLowerInvariant())  $($Exe.Name)" | Set-Content -Encoding ASCII $ChecksumPath
Assert-File $ChecksumPath "SHA-256 checksum file"

$Provenance = [ordered]@{
    schema = "techguytool-huawei.windows-release-provenance.v1"
    filename = $Exe.Name
    sha256 = $Hash.Hash.ToLowerInvariant()
    packaging = "onefile"
    deploy_wrapper = "pyside6-deploy"
    compiler = "msvc"
    signing_mode = $SigningMode
    authenticode_required_for_production = $true
    ci_test_signature = [bool]$CiTestSigning
    production_signature = [bool]($SigningMode -eq "production-authenticode")
}
$Provenance | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 (Join-Path $Exe.DirectoryName "RELEASE_PROVENANCE.json")
Write-Host "Release candidate ready: $($Exe.FullName)" -ForegroundColor Green
