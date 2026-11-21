# Create a Desktop shortcut and a Start-menu shortcut for this install.
$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$Launcher = Join-Path $Repo "tools\sim-lab\windows\Launch-SimLab.cmd"
$Shell = New-Object -ComObject WScript.Shell

function New-LabShortcut([string]$Path) {
    $shortcut = $Shell.CreateShortcut($Path)
    $shortcut.TargetPath = $Launcher
    $shortcut.WorkingDirectory = $Repo
    $shortcut.WindowStyle = 1
    $shortcut.Description = "All That Endures Simulation Laboratory"
    $shortcut.Save()
    Write-Host "Shortcut: $Path"
}

$desktop = [Environment]::GetFolderPath("Desktop")
New-LabShortcut (Join-Path $desktop "ATE Simulation Laboratory.lnk")
$programs = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
New-Item -ItemType Directory -Force -Path $programs | Out-Null
New-LabShortcut (Join-Path $programs "ATE Simulation Laboratory.lnk")
