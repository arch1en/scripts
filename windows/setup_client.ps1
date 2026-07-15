#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Installs/enables OpenSSH Server on Windows, sets a custom listening port,
    and updates Windows Firewall rules accordingly.

.DESCRIPTION
    - Installs the OpenSSH.Server Windows capability if not already present.
    - Sets the sshd service to Automatic startup and starts it.
    - Edits sshd_config to listen on the specified port.
    - Creates/updates a firewall rule allowing inbound TCP on the new port.
    - If the new port is not 22, disables/removes the default port 22 firewall rule.

.PARAMETER Port
    The TCP port SSH should listen on. Defaults to 22 (no change) if not specified.

.EXAMPLE
    .\Setup-SSHServer.ps1 -Port 2222

.EXAMPLE (via curl/irm, since piped scripts can't take normal params)
    $Port = 2222
    iex "& { $(irm https://example.com/Setup-SSHServer.ps1) } -Port $Port"
#>

param(
    [Parameter(Mandatory = $false)]
    [ValidateRange(1, 65535)]
    [int]$Port = 22
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host "==> $msg" -ForegroundColor Cyan
}

# --- 0. Must be running as Administrator ---
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "This script must be run as Administrator. Re-launch an elevated PowerShell and try again."
    exit 1
}

# --- 1. Install OpenSSH Server capability if missing ---
Write-Step "Checking OpenSSH Server capability..."
$capability = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'

if ($capability.State -ne 'Installed') {
    Write-Step "Installing OpenSSH Server..."
    Add-WindowsCapability -Online -Name $capability.Name | Out-Null
} else {
    Write-Step "OpenSSH Server already installed."
}

# --- 2. Enable and start the sshd service ---
Write-Step "Setting sshd service to Automatic and starting it..."
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd -ErrorAction SilentlyContinue

# Optional but common: also enable ssh-agent
try {
    Set-Service -Name ssh-agent -StartupType Automatic
    Start-Service ssh-agent -ErrorAction SilentlyContinue
} catch {
    Write-Host "Note: ssh-agent service not found/adjusted (non-fatal)." -ForegroundColor Yellow
}

# --- 3. Update sshd_config with the new port ---
$sshdConfigPath = "$env:ProgramData\ssh\sshd_config"

if (-not (Test-Path $sshdConfigPath)) {
    Write-Error "sshd_config not found at $sshdConfigPath. Installation may have failed."
    exit 1
}

Write-Step "Configuring sshd to listen on port $Port..."
$configContent = Get-Content $sshdConfigPath

# Remove any existing Port lines (commented or not), then insert the correct one at the top
$configContent = $configContent | Where-Object { $_ -notmatch '^\s*#?\s*Port\s+\d+' }
$configContent = @("Port $Port") + $configContent

Set-Content -Path $sshdConfigPath -Value $configContent -Encoding ASCII

# --- 4. Restart sshd to apply the config change ---
Write-Step "Restarting sshd service to apply changes..."
Restart-Service sshd

# --- 5. Firewall: allow the new port ---
$ruleName = "OpenSSH-Server-In-TCP-$Port"

Write-Step "Ensuring firewall rule for port $Port exists..."
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existingRule) {
    New-NetFirewallRule -DisplayName $ruleName `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort $Port `
        -Action Allow | Out-Null
    Write-Host "Created firewall rule '$ruleName' allowing TCP/$Port inbound." -ForegroundColor Green
} else {
    Write-Host "Firewall rule '$ruleName' already exists." -ForegroundColor Green
}

# --- 6. Firewall: close port 22 if a different port is used ---
if ($Port -ne 22) {
    Write-Step "Custom port in use — locking down default port 22..."

    # Disable the built-in rule Windows creates for OpenSSH (OpenSSH-Server-In-TCP)
    $defaultRule = Get-NetFirewallRule -DisplayName "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
    if ($defaultRule) {
        Disable-NetFirewallRule -DisplayName "OpenSSH-Server-In-TCP"
        Write-Host "Disabled default 'OpenSSH-Server-In-TCP' (port 22) firewall rule." -ForegroundColor Yellow
    }

    # Also catch any other rule explicitly bound to port 22
    $port22Rules = Get-NetFirewallPortFilter -Protocol TCP |
        Where-Object { $_.LocalPort -eq 22 } |
        Get-NetFirewallRule

    foreach ($rule in $port22Rules) {
        if ($rule.Enabled -eq 'True') {
            Disable-NetFirewallRule -Name $rule.Name
            Write-Host "Disabled rule '$($rule.DisplayName)' (bound to port 22)." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "Port 22 is in use — leaving default firewall rules untouched." -ForegroundColor Yellow
}

# --- 7. Summary ---
Write-Step "Done."
Write-Host ""
Write-Host "SSH server status:" -ForegroundColor Green
Get-Service sshd | Format-Table Name, Status, StartType -AutoSize
Write-Host "Listening port: $Port" -ForegroundColor Green
Write-Host ""
Write-Host "Test from a remote machine with:" -ForegroundColor Cyan
Write-Host "  ssh -p $Port <username>@<this-machine-ip>"
