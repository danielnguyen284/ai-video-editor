param([switch]$WithTranscription, [switch]$WithMotion, [switch]$WithVision, [switch]$WithEditor)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        & python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create Python virtual environment.' }
    }
    $projectPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    & $projectPython scripts/setup_tools.py
    if ($LASTEXITCODE -ne 0) { throw 'FFmpeg setup failed.' }
    if ($WithTranscription) {
        & $projectPython -m pip install -r requirements-stt.txt
        if ($LASTEXITCODE -ne 0) { throw 'Transcription dependency installation failed.' }
    }
    if ($WithVision) {
        & $projectPython -m pip install -r requirements-vision.txt
        if ($LASTEXITCODE -ne 0) { throw 'Vision dependency installation failed.' }
    }
    if ($WithMotion -or $WithEditor) {
        Push-Location -LiteralPath (Join-Path $projectRoot 'motion')
        try {
            & npm.cmd ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'Remotion dependency installation failed.' }
            & npm.cmd run typecheck
            if ($LASTEXITCODE -ne 0) { throw 'Motion TypeScript check failed.' }
        } finally { Pop-Location }
    }
    if ($WithEditor) {
        Push-Location -LiteralPath (Join-Path $projectRoot 'editor')
        try {
            & npm.cmd ci --no-audit --no-fund
            if ($LASTEXITCODE -ne 0) { throw 'Editor dependency installation failed.' }
            & npm.cmd run build
            if ($LASTEXITCODE -ne 0) { throw 'Editor build failed.' }
        } finally { Pop-Location }
    }
    & $projectPython ai_editor.py doctor
    if ($LASTEXITCODE -ne 0) { throw 'Required tools are missing.' }
} finally { Pop-Location }
