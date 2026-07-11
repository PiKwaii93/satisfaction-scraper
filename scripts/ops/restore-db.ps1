param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [string]$Database = "satisfaction_client",
    [string]$User = "admin",
    [string]$Service = "postgres_db",
    [string]$Container = "satisfaction_db",
    [switch]$Yes
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

if (-not (Test-Path $BackupFile)) {
    throw "Backup introuvable: $BackupFile"
}

$resolvedBackup = Resolve-Path $BackupFile
$fileName = Split-Path $resolvedBackup -Leaf
$containerPath = "/tmp/$fileName"

if (-not $Yes) {
    Write-Host "[!] Cette operation va restaurer la base '$Database' et remplacer les objets existants."
    $answer = Read-Host "Tape RESTORE pour confirmer"
    if ($answer -ne "RESTORE") {
        Write-Host "Restauration annulee."
        exit 0
    }
}

Write-Host "[*] Verification du service PostgreSQL..."
Invoke-Checked { docker-compose up -d $Service }

Write-Host "[*] Copie du dump dans le conteneur..."
Invoke-Checked { docker cp $resolvedBackup "$Container`:$containerPath" }

Write-Host "[*] Restauration de $Database..."
Invoke-Checked { docker-compose exec -T $Service pg_restore -U $User -d $Database --clean --if-exists --no-owner --no-privileges $containerPath }

Write-Host "[*] Nettoyage du fichier temporaire dans le conteneur..."
Invoke-Checked { docker-compose exec -T $Service rm -f $containerPath }

Write-Host "[+] Restauration terminee depuis: $resolvedBackup"
