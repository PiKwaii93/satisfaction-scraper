param(
    [string]$Database = "satisfaction_client",
    [string]$User = "admin",
    [string]$Service = "postgres_db",
    [string]$Container = "satisfaction_db",
    [string]$BackupDir = "backups"
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Commande echouee: $Command"
    }
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path (Get-Location) $BackupDir
$fileName = "$Database-$timestamp.dump"
$localPath = Join-Path $backupRoot $fileName
$containerPath = "/tmp/$fileName"

if (-not (Test-Path $backupRoot)) {
    New-Item -ItemType Directory -Path $backupRoot | Out-Null
}

Write-Host "[*] Verification du service PostgreSQL..."
Invoke-Checked { docker-compose up -d $Service }

Write-Host "[*] Creation du dump PostgreSQL dans le conteneur..."
Invoke-Checked { docker-compose exec -T $Service pg_dump -U $User -d $Database -Fc -f $containerPath }

Write-Host "[*] Copie du dump vers $localPath..."
Invoke-Checked { docker cp "$Container`:$containerPath" $localPath }

Write-Host "[*] Nettoyage du fichier temporaire dans le conteneur..."
Invoke-Checked { docker-compose exec -T $Service rm -f $containerPath }

$size = [math]::Round((Get-Item $localPath).Length / 1MB, 2)
Write-Host "[+] Backup cree: $localPath ($size MB)"
