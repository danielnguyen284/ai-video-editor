param(
    [switch]$All,
    [switch]$WithTranscription, [switch]$WithModel, [switch]$WithMotion, [switch]$WithVision, [switch]$WithEditor, [switch]$WithSkills
)
# -All installs everything a new machine needs: STT package + large-v3 model, Remotion, OpenCV,
# Studio (with desktop shortcut) and the pinned skill library. Safe to run again: finished parts are kept,
# an interrupted model download resumes.
$ErrorActionPreference = 'Stop'
if ($All) { $WithTranscription = $WithModel = $WithMotion = $WithVision = $WithEditor = $WithSkills = $true }
if ($WithModel) { $WithTranscription = $true }
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
function Step($text) { Write-Host "`n== $text" -ForegroundColor Cyan }
try {
    Step 'Checking prerequisites'
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python -or $python.Source -like '*WindowsApps*') {
        throw 'Python 3.11-3.13 is not installed (or only the Microsoft Store alias exists). Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH", then open a new terminal.'
    }
    $version = & python -c "import sys; print('%d.%d' % sys.version_info[:2])"
    if ([version]$version -lt [version]'3.11') { throw "Python $version found; this project needs Python 3.11 or newer." }
    Write-Host "Python $version"
    if ($WithMotion -or $WithEditor) {
        if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
            throw 'Node.js is not installed. Install Node.js 22 LTS from https://nodejs.org/ and open a new terminal.'
        }
        Write-Host ("Node.js " + (& node --version))
    }
    $free = (Get-PSDrive -Name (Split-Path -Qualifier $projectRoot).TrimEnd(':')).Free
    $modelPresent = Test-Path -LiteralPath '.tools\models\faster-whisper-large-v3\model.bin'
    $needed = if ($WithModel -and -not $modelPresent) { 6GB } else { 2GB }
    if ($free -lt $needed) { throw ("Not enough free disk space: need about {0} GB, have {1:N1} GB." -f ($needed / 1GB), ($free / 1GB)) }

    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        Step 'Creating the Python environment (.venv)'
        & python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create Python virtual environment.' }
    }
    $projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    Step 'FFmpeg (portable, checksum verified)'
    & $projectPython scripts/setup_tools.py
    if ($LASTEXITCODE -ne 0) { throw 'FFmpeg setup failed.' }
    if ($WithSkills) {
        Step 'Pinned skill library (GitHub, checksum verified)'
        & $projectPython scripts/install_skill_library.py
        if ($LASTEXITCODE -ne 0) { throw 'Pinned skill library installation failed. Run setup again to retry.' }
    }
    if ($WithTranscription) {
        Step 'Speech transcription package (faster-whisper)'
        & $projectPython -m pip install --disable-pip-version-check -r requirements-stt.txt
        if ($LASTEXITCODE -ne 0) { throw 'Transcription dependency installation failed.' }
    }
    if ($WithModel) {
        Step 'Large-v3 model (about 3 GB, resumable)'
        & $projectPython scripts/download_model.py
        if ($LASTEXITCODE -ne 0) { throw 'Model download did not finish. Run the same setup command again to resume.' }
    }
    if ($WithVision) {
        Step 'Footage analysis package (OpenCV)'
        & $projectPython -m pip install --disable-pip-version-check -r requirements-vision.txt
        if ($LASTEXITCODE -ne 0) { throw 'Vision dependency installation failed.' }
    }
    if ($WithMotion -or $WithEditor) {
        Step 'Remotion motion templates'
        Push-Location -LiteralPath (Join-Path $projectRoot 'motion')
        try {
            & npm.cmd ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'Remotion dependency installation failed.' }
            & npm.cmd run typecheck
            if ($LASTEXITCODE -ne 0) { throw 'Motion TypeScript check failed.' }
        } finally { Pop-Location }
    }
    if ($WithEditor) {
        Step 'AI Editor Studio (build + desktop shortcut)'
        Push-Location -LiteralPath (Join-Path $projectRoot 'editor')
        try {
            & npm.cmd ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'Editor dependency installation failed.' }
            & npm.cmd run build
            if ($LASTEXITCODE -ne 0) { throw 'Editor build failed.' }
        } finally { Pop-Location }
        & (Join-Path $PSScriptRoot 'create_shortcut.ps1')
    }
    Step 'Checking the installation'
    & $projectPython ai_editor.py doctor
    if ($LASTEXITCODE -ne 0) { throw 'Some required parts are missing (see the lines above). Run setup again with -All.' }
    if ($WithEditor) {
        Write-Host "`nSetup finished. Open 'AI Editor Studio' on the desktop, then open this folder in Codex or Claude Code." -ForegroundColor Green
    } else {
        Write-Host "`nSetup finished for the selected parts. Run setup with -All to add the rest (Studio, model, motion)." -ForegroundColor Green
    }
} finally { Pop-Location }
