#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploys the Cloud-Based Banking System to Azure
.DESCRIPTION
    Creates all necessary Azure resources (App Service, SQL Database, Key Vault)
    and deploys the Flask application
.PARAMETER ResourceGroupName
    Name of the Azure resource group
.PARAMETER Location
    Azure region (default: eastus)
.PARAMETER SqlAdminPassword
    SQL Server admin password (will prompt if not provided)
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus",
    
    [Parameter(Mandatory=$false)]
    [string]$SqlAdminPassword
)

# ========== Configuration ==========

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

Write-Host "🏦 Virtual Banking System - Azure Deployment" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# ========== Prerequisites Check ==========

Write-Host "`n📋 Checking prerequisites..." -ForegroundColor Yellow

try {
    $azCli = az --version 2>&1 | Select-Object -First 1
    Write-Host "✓ Azure CLI installed: $azCli" -ForegroundColor Green
}
catch {
    Write-Host "✗ Azure CLI not found. Install from: https://docs.microsoft.com/cli/azure/" -ForegroundColor Red
    exit 1
}

# ========== Authentication ==========

Write-Host "`n🔐 Checking Azure authentication..." -ForegroundColor Yellow

$account = az account show -o json 2>&1 | ConvertFrom-Json

if ($?) {
    $subscriptionId = $account.id
    $subscriptionName = $account.name
    Write-Host "✓ Logged in to: $subscriptionName ($subscriptionId)" -ForegroundColor Green
}
else {
    Write-Host "⚠ Not authenticated. Initiating login..." -ForegroundColor Yellow
    az login --use-device-code
    $account = az account show -o json | ConvertFrom-Json
    Write-Host "✓ Authentication successful" -ForegroundColor Green
}

# ========== Input Parameters ==========

if (-not $SqlAdminPassword) {
    Write-Host "`n🔐 Enter SQL Server admin password:" -ForegroundColor Yellow
    $SecurePassword = Read-Host -AsSecureString
    $SqlAdminPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToCoTaskMemUnicode($SecurePassword))
}

# Validate password
if ($SqlAdminPassword.Length -lt 8) {
    Write-Host "✗ Password must be at least 8 characters" -ForegroundColor Red
    exit 1
}

# ========== Create Resource Group ==========

Write-Host "`n📦 Creating resource group..." -ForegroundColor Yellow

az group create `
    --name $ResourceGroupName `
    --location $Location `
    -o none

if ($?) {
    Write-Host "✓ Resource group created: $ResourceGroupName" -ForegroundColor Green
}
else {
    Write-Host "✗ Failed to create resource group" -ForegroundColor Red
    exit 1
}

# ========== Deploy Bicep Template ==========

Write-Host "`n🏗️ Deploying Azure infrastructure..." -ForegroundColor Yellow
Write-Host "   (This may take 3-5 minutes)" -ForegroundColor Gray

$deployment = az deployment group create `
    --resource-group $ResourceGroupName `
    --template-file infrastructure/main.bicep `
    --parameters sqlAdminPassword=$SqlAdminPassword `
    -o json | ConvertFrom-Json

if ($?) {
    $outputs = $deployment.properties.outputs
    
    $webAppUrl = $outputs.webAppUrl.value
    $sqlServerFqdn = $outputs.sqlServerFqdn.value
    $databaseName = $outputs.databaseName.value
    $keyVaultName = $outputs.keyVaultName.value
    $keyVaultUri = $outputs.keyVaultUri.value
    
    Write-Host "✓ Infrastructure deployed successfully!" -ForegroundColor Green
    
    Write-Host "`n📊 Deployment Summary:" -ForegroundColor Cyan
    Write-Host "  Web App URL:        $webAppUrl" -ForegroundColor White
    Write-Host "  SQL Server:         $sqlServerFqdn" -ForegroundColor White
    Write-Host "  Database:           $databaseName" -ForegroundColor White
    Write-Host "  Key Vault:          $keyVaultName" -ForegroundColor White
}
else {
    Write-Host "✗ Deployment failed" -ForegroundColor Red
    exit 1
}

# ========== Store Secrets in Key Vault ==========

Write-Host "`n🔑 Storing secrets in Key Vault..." -ForegroundColor Yellow

try {
    $jwtSecret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    
    az keyvault secret set `
        --vault-name $keyVaultName `
        --name SqlPassword `
        --value $SqlAdminPassword `
        -o none
    
    az keyvault secret set `
        --vault-name $keyVaultName `
        --name JwtSecret `
        --value $jwtSecret `
        -o none
    
    Write-Host "✓ Secrets stored in Key Vault" -ForegroundColor Green
}
catch {
    Write-Host "⚠ Warning: Could not store secrets (may need Key Vault access policy setup)" -ForegroundColor Yellow
}

# ========== Create Environment File ==========

Write-Host "`n⚙️ Creating .env configuration file..." -ForegroundColor Yellow

$envContent = @"
# ========== Banking API Configuration ==========

# App Settings
APP_PORT=5000
DEBUG=false
CORS_ORIGINS=https://$($webAppUrl -replace 'https://', '')

# Database Configuration
USE_SQL=true
SQL_SERVER=$sqlServerFqdn
SQL_DATABASE=$databaseName
SQL_USER=sqladmin
SQL_PASSWORD=$SqlAdminPassword

# JWT Configuration
JWT_SECRET=$jwtSecret
JWT_ALGORITHM=HS256
"@

Set-Content -Path "src/.env" -Value $envContent -Encoding UTF8
Write-Host "✓ Configuration file created: src/.env" -ForegroundColor Green

# ========== Package Application ==========

Write-Host "`n📦 Packaging application..." -ForegroundColor Yellow

try {
    $compress = @{
        Path = "src/app.py", "src/database.py", "src/config.py", "src/__init__.py", "requirements.txt"
        DestinationPath = "banking-app.zip"
    }
    Compress-Archive @compress -Force -ErrorAction Stop
    Write-Host "✓ Application packaged: banking-app.zip" -ForegroundColor Green
}
catch {
    Write-Host "⚠ Warning: Could not package application: $_" -ForegroundColor Yellow
}

# ========== Deployment Instructions ==========

Write-Host "`n📝 Next Steps:" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Gray

Write-Host "`n1️⃣ DEPLOY BACKEND APPLICATION:" -ForegroundColor Yellow

$appServiceName = ($webAppUrl -split '://')[1].split('.')[0]

Write-Host "
   az webapp deployment source config-zip `
       --resource-group $ResourceGroupName `
       --name $appServiceName `
       --src banking-app.zip
" -ForegroundColor White

Write-Host "`n2️⃣ UPDATE FRONTEND:" -ForegroundColor Yellow
Write-Host "
   In index.html, change:
   const API_URL = 'https://$($webAppUrl -replace 'https://', '')';
" -ForegroundColor White

Write-Host "`n3️⃣ CONFIGURE DATABASE:" -ForegroundColor Yellow
Write-Host "
   # Add firewall rule for your IP
   az sql server firewall-rule create `
       --resource-group $ResourceGroupName `
       --server $($sqlServerFqdn.split('.')[0]) `
       --name AllowMyIP `
       --start-ip-address YOUR.IP.ADDRESS `
       --end-ip-address YOUR.IP.ADDRESS
" -ForegroundColor White

Write-Host "`n📊 Resource Information:" -ForegroundColor Cyan
Write-Host "  Resource Group:     $ResourceGroupName" -ForegroundColor White
Write-Host "  Region:             $Location" -ForegroundColor White
Write-Host "  Subscription:       $subscriptionName" -ForegroundColor White

Write-Host "`n✅ Deployment preparation complete!" -ForegroundColor Green
