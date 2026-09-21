param(
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot
$projectName = "satisfaction-ch8-" + [guid]::NewGuid().ToString("N").Substring(0, 12)
$timer = [System.Diagnostics.Stopwatch]::StartNew()

function Invoke-Checked {
    param([scriptblock]$Command, [string]$Step)
    Write-Host "[*] $Step"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed (exit $LASTEXITCODE)"
    }
}

$env:DB_HOST = "postgres_db"
$env:DB_PORT = "5432"
$env:DB_USER = "admin"
$env:DB_PASSWORD = "ch8-local-test-password"
$env:DB_NAME = "satisfaction_ch8_test"
$env:MLFLOW_TRACKING_URI = "http://mlflow:5000"
$env:MODEL_BOOTSTRAP_PATH = "/app/app/models/sentiment_model.pkl"
$env:MODEL_BOOTSTRAP_SHA256_PATH = "/app/app/models/sentiment_model.sha256"
$env:CELERY_BROKER_URL = "redis://redis:6379/0"
$env:CELERY_RESULT_BACKEND = "redis://redis:6379/1"
$env:JWT_SECRET_KEY = "ch8-test-jwt-secret-at-least-32-bytes"
$env:DEMO_ADMIN_EMAIL = "demo@satisfaction.local"
$env:DEMO_ADMIN_PASSWORD = "demo-password"
$env:POSTGRES_HOST_PORT = "15433"
$env:MLFLOW_HOST_PORT = "15001"
$env:REDIS_HOST_PORT = "16380"
$env:API_HOST_PORT = "18001"
$env:FRONTEND_HOST_PORT = "15174"
$env:DASHBOARD_HOST_PORT = "18502"
$env:VITE_API_BASE_URL = "http://localhost:18001"
$env:FRONTEND_BASE_URL = "http://localhost:15174"

Invoke-Checked { docker compose version } "Docker Compose availability"
$existing = @(docker volume ls --format '{{.Name}}' --filter "label=com.docker.compose.project=$projectName")
if ($LASTEXITCODE -ne 0 -or $existing.Count -ne 0) {
    throw "Refusing to reuse existing Compose project $projectName"
}

try {
    Invoke-Checked {
        docker compose -p $projectName up -d --build postgres_db mlflow redis model_bootstrap api celery_worker frontend
    } "Isolated stack startup"
    Invoke-Checked {
        docker compose -p $projectName run --rm --no-deps --entrypoint sh api -c "python -m pip install -q -r requirements-dev.txt && python -m pytest -q tests"
    } "Backend and migration tests"
    if (-not $SkipFrontend) {
        Invoke-Checked {
            docker compose -p $projectName run --rm --no-deps --entrypoint sh frontend -c "VITE_API_BASE_URL=http://localhost:8000 npm test && npm run build"
        } "Frontend tests and build"
    }
    Invoke-Checked {
        docker compose -p $projectName run --rm --no-deps --entrypoint python api scripts/verify_e2e.py
    } "CSV HTTP E2E smoke test"
    $timer.Stop()
    Write-Host "PASS reproducibility checks in $([math]::Round($timer.Elapsed.TotalSeconds, 1))s"
}
catch {
    docker compose -p $projectName logs --no-color --tail 40 api celery_worker model_bootstrap
    throw
}
finally {
    docker compose -p $projectName down -v
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Temporary Compose cleanup failed for $projectName"
    }
    foreach ($service in @("api", "celery_worker", "model_bootstrap", "frontend")) {
        $image = "${projectName}-${service}:latest"
        docker image inspect $image *> $null
        if ($LASTEXITCODE -eq 0) {
            docker image rm $image | Out-Null
        }
    }
}
