# Launch the laboratory from this install only.
# The founder's main checkout is never the working directory and is never updated.
$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$LogDir = Join-Path $env:LOCALAPPDATA "ATE-SimLab"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Log = Join-Path $LogDir "launch.log"

function Write-Log([string]$Message) {
    $line = "{0} {1}" -f (Get-Date -Format o), $Message
    Add-Content -Path $Log -Value $line
    Write-Host $Message
}

function Find-Python312 {
    $candidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try { $candidates += (& py -3.12 -c "import sys; print(sys.executable)").Trim() } catch {}
    }
    foreach ($name in @("python3.12", "python")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { $candidates += $cmd.Source }
    }
    foreach ($exe in $candidates) {
        if (-not $exe) { continue }
        $ver = & $exe -c "import sys; print('%d.%d' % sys.version_info[:2])"
        if ($ver -eq "3.12") { return $exe }
    }
    throw "Python 3.12 was not found. Install the 64-bit release from python.org. This launcher does not use any other checkout."
}

$python = Find-Python312
$venv = Join-Path $Repo ".venv"
$venvPy = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Log "Creating a virtual environment in this install"
    & $python -m venv $venv
}
$req = Join-Path $Repo "tools\sim-lab\requirements.txt"
$stamp = Join-Path $venv "ate-lab-requirements.sha256"
$hash = (Get-FileHash -Algorithm SHA256 -Path $req).Hash
$previous = ""
if (Test-Path $stamp) { $previous = (Get-Content -Raw -Path $stamp).Trim() }
if ($hash -ne $previous) {
    Write-Log "Installing laboratory dependencies"
    & $venvPy -m pip install -r $req
    if ($LASTEXITCODE -ne 0) { throw "pip install failed. See $Log" }
    Set-Content -Path $stamp -Value $hash -NoNewline
}

$entry = Join-Path $Repo "tools\sim-lab\simlab.py"
Write-Log "Checking this install's tracked branch"
& $venvPy $entry --update-only
if ($LASTEXITCODE -ne 0) {
    Write-Log "Update step exited $LASTEXITCODE. Launching the current version."
}
$hashNow = (Get-FileHash -Algorithm SHA256 -Path $req).Hash
$stampNow = ""
if (Test-Path $stamp) { $stampNow = (Get-Content -Raw -Path $stamp).Trim() }
if ($hashNow -ne $stampNow) {
    Write-Log "Requirements changed. Reinstalling."
    & $venvPy -m pip install -r $req
    if ($LASTEXITCODE -eq 0) { Set-Content -Path $stamp -Value $hashNow -NoNewline }
}

$pythonw = Join-Path $venv "Scripts\pythonw.exe"
if (-not (Test-Path $pythonw)) { $pythonw = $venvPy }
Write-Log "Launching $pythonw"
Start-Process -FilePath $pythonw -ArgumentList @("`"$entry`"", "--no-update") -WorkingDirectory $Repo
Write-Log "Window started. This console can close."
