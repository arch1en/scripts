<#
.SYNOPSIS
    Sets up a local dev environment: WSL2 (Arch Linux), Podman, and Node.js.

.DESCRIPTION
    - Installs/enables WSL2 with the Arch Linux distro
    - Installs Podman (via winget)
    - Initializes and starts a Podman machine
    - Installs Node.js LTS (via winget)
    - Ensures Node.js is on the system PATH
    - Restarts the machine at the end if a pending reboot is required
      (e.g. after enabling WSL features), unless -NoReboot is specified.

.PARAMETER NoReboot
    Skip the automatic restart even if one is required. You will need to
    reboot manually and re-run the script to finish WSL/Podman setup.

.NOTES
    Must be run as Administrator. Requires winget (App Installer) to be
    present, which ships by default on modern Windows 10/11 builds.
#>

[CmdletBinding()]
param(
    [switch]$NoReboot
)

$ErrorActionPreference = 'Stop'
$script:RebootNeeded = $false

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Message)
    Write-Host "    $Message" -ForegroundColor Gray
}

function Write-Ok {
    param([string]$Message)
    Write-Host "    [OK] $Message" -ForegroundColor Green
}

function Write-Warn2 {
    param([string]$Message)
    Write-Host "    [!] $Message" -ForegroundColor Yellow
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Invoke-Winget {
    param(
        [Parameter(Mandatory)][string]$Id,
        [string]$Extra = ""
    )
    if (-not (Test-CommandExists 'winget')) {
        throw "winget was not found. Install 'App Installer' from the Microsoft Store, then re-run this script."
    }
    $args = @('install', '--id', $Id, '-e', '--source', 'winget',
              '--accept-package-agreements', '--accept-source-agreements', '--silent')
    if ($Extra) { $args += $Extra.Split(' ') }
    Write-Info "winget $($args -join ' ')"
    & winget @args
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne -1978335189) {
        # -1978335189 = APPINSTALLER_CLI_ERROR_NO_APPLICABLE_UPDATE_FOUND (already up to date)
        Write-Warn2 "winget exited with code $LASTEXITCODE for $Id (may already be installed/up to date)."
    }
}

function Refresh-EnvPath {
    # Re-read Machine + User PATH into the current process so newly
    # installed tools (podman, node) are usable without a new shell.
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath    = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machinePath;$userPath"
}

# ----------------------------------------------------------------------------
# 1. WSL2 + Arch Linux
# ----------------------------------------------------------------------------

function Install-WslArch {
    Write-Step "Checking WSL and Arch Linux distro"

    if (-not (Test-CommandExists 'wsl')) {
        Write-Warn2 "wsl.exe not found; this Windows build may not support 'wsl --install' directly."
    }

    # Enable required Windows features (idempotent; no-op if already enabled)
    $features = @('Microsoft-Windows-Subsystem-Linux', 'VirtualMachinePlatform')
    foreach ($feature in $features) {
        $state = (Get-WindowsOptionalFeature -Online -FeatureName $feature -ErrorAction SilentlyContinue).State
        if ($state -ne 'Enabled') {
            Write-Info "Enabling Windows feature: $feature"
            $result = Enable-WindowsOptionalFeature -Online -FeatureName $feature -All -NoRestart
            if ($result.RestartNeeded) { $script:RebootNeeded = $true }
        } else {
            Write-Ok "$feature already enabled"
        }
    }

    # Make sure the WSL kernel/tooling itself is installed and up to date.
    try {
        Write-Info "Ensuring WSL platform components are installed (wsl --install --no-distribution)"
        wsl --install --no-distribution 2>$null | Out-Null
    } catch {
        Write-Warn2 "wsl --install --no-distribution reported an issue (often harmless if WSL is already set up): $($_.Exception.Message)"
    }

    try {
        Write-Info "Setting WSL default version to 2"
        wsl --set-default-version 2 2>$null | Out-Null
    } catch {
        Write-Warn2 "Could not set default WSL version to 2 yet (may require a reboot first)."
        $script:RebootNeeded = $true
    }

    # Check whether Arch is already registered as a distro.
    $existingDistros = (wsl -l -q 2>$null) -replace "`0", ""
    $archInstalled = $existingDistros -match '^\s*archlinux\s*$'

    if ($archInstalled) {
        Write-Ok "Arch Linux distro already installed in WSL"
        return
    }

    if ($script:RebootNeeded) {
        Write-Warn2 "A reboot is required before the Arch Linux distro can be installed. It will be installed after restart if you re-run this script, or you can re-run it manually post-reboot."
        return
    }

    Write-Info "Installing Arch Linux distro for WSL (this can take a few minutes)"
    try {
        wsl --install -d archlinux
        Write-Ok "Arch Linux distro installation triggered"
    } catch {
        Write-Warn2 "Automatic 'wsl --install -d archlinux' failed: $($_.Exception.Message)"
        Write-Info "You can install it manually later with: wsl --install -d archlinux"
    }
}

# ----------------------------------------------------------------------------
# 2. Podman
# ----------------------------------------------------------------------------

function Install-Podman {
    Write-Step "Installing Podman"

    if (Test-CommandExists 'podman') {
        Write-Ok "Podman already installed"
        return
    }

    Invoke-Winget -Id 'RedHat.Podman'
    Refresh-EnvPath

    if (Test-CommandExists 'podman') {
        Write-Ok "Podman installed successfully"
    } else {
        Write-Warn2 "Podman command not found on PATH yet. A new shell/session (or reboot) may be required."
    }
}

function Initialize-PodmanMachine {
    Write-Step "Initializing and starting Podman machine"

    if (-not (Test-CommandExists 'podman')) {
        Write-Warn2 "Skipping podman machine setup: podman is not available on PATH in this session."
        return
    }

    $machines = & podman machine list --format "{{.Name}}" 2>$null
    $hasMachine = $machines -and ($machines -match '\S')

    if (-not $hasMachine) {
        Write-Info "Running: podman machine init"
        try {
            & podman machine init
        } catch {
            Write-Warn2 "podman machine init failed: $($_.Exception.Message)"
            return
        }
    } else {
        Write-Ok "Podman machine already initialized"
    }

    $running = & podman machine list --format "{{.Name}} {{.Running}}" 2>$null |
        Where-Object { $_ -match 'true\s*$' }

    if (-not $running) {
        Write-Info "Running: podman machine start"
        try {
            & podman machine start
            Write-Ok "Podman machine started"
        } catch {
            Write-Warn2 "podman machine start failed: $($_.Exception.Message)"
        }
    } else {
        Write-Ok "Podman machine already running"
    }
}

# ----------------------------------------------------------------------------
# 3. Node.js
# ----------------------------------------------------------------------------

function Install-NodeJs {
    Write-Step "Installing Node.js (LTS)"

    if (Test-CommandExists 'node') {
        $version = (& node --version)
        Write-Ok "Node.js already installed ($version)"
        return
    }

    Invoke-Winget -Id 'OpenJS.NodeJS.LTS'
    Refresh-EnvPath

    if (Test-CommandExists 'node') {
        Write-Ok "Node.js installed successfully ($(& node --version))"
    } else {
        Write-Warn2 "node command not found on PATH yet in this session."
    }
}

function Ensure-NodeJsOnPath {
    Write-Step "Verifying Node.js is on PATH"

    # Common install locations for the winget/MSI Node.js package.
    $candidatePaths = @(
        "$Env:ProgramFiles\nodejs",
        "${Env:ProgramFiles(x86)}\nodejs",
        "$Env:LOCALAPPDATA\Programs\nodejs"
    ) | Where-Object { $_ -and (Test-Path $_) }

    $nodeExe = Get-Command node -ErrorAction SilentlyContinue
    if ($nodeExe) {
        $installDir = Split-Path $nodeExe.Source -Parent
        if ($candidatePaths -notcontains $installDir) {
            $candidatePaths += $installDir
        }
    }

    if (-not $candidatePaths) {
        Write-Warn2 "Could not locate a Node.js install directory to add to PATH."
        return
    }

    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $pathEntries = $machinePath -split ';' | Where-Object { $_ }

    $updated = $false
    foreach ($dir in $candidatePaths) {
        if ($pathEntries -notcontains $dir) {
            Write-Info "Adding to system PATH: $dir"
            $pathEntries += $dir
            $updated = $true
        } else {
            Write-Ok "Already on PATH: $dir"
        }
    }

    if ($updated) {
        $newMachinePath = ($pathEntries -join ';')
        [Environment]::SetEnvironmentVariable('Path', $newMachinePath, 'Machine')
        Refresh-EnvPath
        Write-Ok "System PATH updated with Node.js location(s)"
    }
}

# ----------------------------------------------------------------------------
# 4. Reboot handling
# ----------------------------------------------------------------------------

function Test-PendingReboot {
    # Check well-known registry locations Windows uses to flag a pending reboot.
    $paths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending',
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { return $true }
    }
    try {
        $pending = Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' `
            -Name 'PendingFileRenameOperations' -ErrorAction SilentlyContinue
        if ($pending) { return $true }
    } catch { }
    return $false
}

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

function Main {
    Write-Host "=================================================" -ForegroundColor Magenta
    Write-Host " Dev Environment Setup: WSL/Arch, Podman, Node.js" -ForegroundColor Magenta
    Write-Host "=================================================" -ForegroundColor Magenta

    if (-not (Test-IsAdmin)) {
        Write-Host ""
        Write-Host "This script must be run as Administrator." -ForegroundColor Red
        Write-Host "Right-click PowerShell -> 'Run as administrator', then re-run this script." -ForegroundColor Red
        exit 1
    }

    Install-WslArch
    Install-Podman
    Initialize-PodmanMachine
    Install-NodeJs
    Ensure-NodeJsOnPath

    if (Test-PendingReboot) { $script:RebootNeeded = $true }

    Write-Step "Summary"
    if ($script:RebootNeeded) {
        Write-Warn2 "A restart is required to finish setup (e.g. to complete WSL feature installation)."
        if ($NoReboot) {
            Write-Info "Skipping automatic restart because -NoReboot was specified."
            Write-Info "Please restart manually, then re-run this script to complete any remaining steps (e.g. Arch Linux distro install)."
        } else {
            Write-Host ""
            Write-Host "Restarting the computer in 15 seconds. Press Ctrl+C to cancel." -ForegroundColor Yellow
            Start-Sleep -Seconds 15
            Restart-Computer -Force
        }
    } else {
        Write-Ok "No reboot required. Setup complete!"
        Write-Info "Open a NEW terminal window so PATH changes take effect, then verify with:"
        Write-Info "  wsl -d archlinux -- echo ok"
        Write-Info "  podman info"
        Write-Info "  node --version"
    }
}

Main
