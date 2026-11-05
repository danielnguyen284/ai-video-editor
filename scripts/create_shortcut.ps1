param([string]$DesktopPath = [Environment]::GetFolderPath('Desktop'))
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$pythonWindowless = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonWindowless)) { throw 'Run scripts/setup.ps1 -WithEditor first.' }
if (-not (Test-Path -LiteralPath $DesktopPath -PathType Container)) { throw 'Desktop directory does not exist.' }
$shortcutPath = Join-Path $DesktopPath 'AI Editor Studio.lnk'
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonWindowless
$shortcut.Arguments = '"' + (Join-Path $projectRoot 'launch_editor.pyw') + '"'
$shortcut.WorkingDirectory = $projectRoot
$shortcut.Description = 'Open AI Editor Studio and resume the last project'
$shortcut.IconLocation = (Join-Path $env:SystemRoot 'System32\shell32.dll') + ',116'
$shortcut.Save()
Write-Output "Created: $shortcutPath"
