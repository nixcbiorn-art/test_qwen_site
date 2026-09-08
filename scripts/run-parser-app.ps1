<#
.SYNOPSIS
    Restores dependencies and runs ParserApp (WPF).

.USAGE
    cd C:\parser\scripts
    .\run-parser-app.ps1
#>

$ErrorActionPreference = "Stop"

$projectDir = Join-Path $PSScriptRoot "..\ParserApp"

if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    Write-Host "dotnet not found in PATH." -ForegroundColor Red
    Write-Host "Run install-dotnet-sdk.ps1 from this folder first." -ForegroundColor Yellow
    exit 1
}

Write-Host "=== dotnet --version ===" -ForegroundColor Cyan
dotnet --version

Push-Location $projectDir
try {
    Write-Host ""
    Write-Host "=== dotnet restore ===" -ForegroundColor Cyan
    dotnet restore

    Write-Host ""
    Write-Host "=== dotnet build ===" -ForegroundColor Cyan
    dotnet build --configuration Debug

    Write-Host ""
    Write-Host "=== dotnet run ===" -ForegroundColor Cyan
    dotnet run
}
finally {
    Pop-Location
}
