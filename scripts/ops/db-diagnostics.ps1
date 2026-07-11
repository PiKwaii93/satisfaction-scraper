param(
    [string]$Database = "satisfaction_client",
    [string]$User = "admin",
    [string]$Service = "postgres_db"
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

Write-Host "[*] Verification du service PostgreSQL..."
Invoke-Checked { docker-compose up -d $Service }

Write-Host ""
Write-Host "== Version Alembic =="
Invoke-Checked { docker-compose exec -T $Service psql -U $User -d $Database -c "SELECT version_num FROM alembic_version;" }

Write-Host ""
Write-Host "== Volumes produit =="
Invoke-Checked { docker-compose exec -T $Service psql -U $User -d $Database -c "SELECT 'organizations' AS table_name, COUNT(*) FROM organizations UNION ALL SELECT 'users', COUNT(*) FROM users UNION ALL SELECT 'companies', COUNT(*) FROM companies UNION ALL SELECT 'analysis_runs', COUNT(*) FROM analysis_runs UNION ALL SELECT 'reviews', COUNT(*) FROM reviews UNION ALL SELECT 'review_feedback', COUNT(*) FROM review_feedback UNION ALL SELECT 'business_alerts', COUNT(*) FROM business_alerts UNION ALL SELECT 'model_training_runs', COUNT(*) FROM model_training_runs ORDER BY table_name;" }

Write-Host ""
Write-Host "== Derniers runs =="
Invoke-Checked { docker-compose exec -T $Service psql -U $User -d $Database -c "SELECT ar.run_id, o.name AS organization, c.company_name, ar.source, ar.status, ar.total_reviews, ar.created_at FROM analysis_runs ar JOIN companies c ON c.company_id = ar.company_id JOIN organizations o ON o.organization_id = ar.organization_id ORDER BY ar.run_id DESC LIMIT 8;" }
