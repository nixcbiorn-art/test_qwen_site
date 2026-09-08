<#
.SYNOPSIS
    Checks for .NET SDK and installs .NET 8 SDK if missing.

.USAGE
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
    .\install-dotnet-sdk.ps1
#>

Write-Host "=== Checking .NET SDK ===" -ForegroundColor Cyan

$dotnetCmd = Get-Command dotnet -ErrorAction SilentlyContinue

if ($dotnetCmd) {
    Write-Host "Found dotnet at: $($dotnetCmd.Source)" -ForegroundColor Green
    Write-Host ""
    Write-Host "--- dotnet --info ---"
    dotnet --info

    $sdks = dotnet --list-sdks 2>$null
    if ($sdks) {
        Write-Host ""
        Write-Host "Installed SDKs:" -ForegroundColor Green
        $sdks | ForEach-Object { Write-Host "  $_" }

        $has8 = $sdks | Where-Object { $_ -match "^8\." }
        if ($has8) {
            Write-Host ""
            Write-Host ".NET 8 SDK is already installed. Nothing to do." -ForegroundColor Green
            exit 0
        } else {
            Write-Host ""
            Write-Host "dotnet found, but no 8.x SDK (only Runtime or a different SDK version)." -ForegroundColor Yellow
            Write-Host "Continuing with .NET 8 SDK install..." -ForegroundColor Yellow
        }
    } else {
        Write-Host ""
        Write-Host "dotnet command exists, but no SDKs found (Runtime only, most likely)." -ForegroundColor Yellow
        Write-Host "Continuing with .NET 8 SDK install..." -ForegroundColor Yellow
    }
} else {
    Write-Host "dotnet not found in PATH. Installing .NET 8 SDK..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Installing .NET 8 SDK ===" -ForegroundColor Cyan

$installDir = "$env:LOCALAPPDATA\Microsoft\dotnet"
$scriptPath = "$env:TEMP\dotnet-install.ps1"

Write-Host "Downloading official Microsoft install script..."
Invoke-WebRequest -Uri "https://dot.net/v1/dotnet-install.ps1" -OutFile $scriptPath -UseBasicParsing

Write-Host "Installing .NET 8 SDK into $installDir ..."
& $scriptPath -Channel 8.0 -InstallDir $installDir

# Add to PATH for current session
$env:PATH = "$installDir;$env:PATH"

# Add to user PATH permanently (if not already there)
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$installDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$installDir", "User")
    Write-Host "Added $installDir to user PATH (restart your terminal for it to take effect)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Verifying install ===" -ForegroundColor Cyan
& "$installDir\dotnet.exe" --version
& "$installDir\dotnet.exe" --list-sdks

Write-Host ""
Write-Host "Done. Close this PowerShell window, open a new one, then run:" -ForegroundColor Green
Write-Host "  cd C:\parser\ParserApp"
Write-Host "  dotnet restore"
Write-Host "  dotnet run"
