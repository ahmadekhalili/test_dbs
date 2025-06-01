# Windows PowerShell setup script for Django Database Benchmark
# Run this in PowerShell as Administrator if you encounter permission issues

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Django Database Benchmark Setup (Windows)" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Function to check if a command exists
function Test-Command {
    param($Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# Check prerequisites
Write-Host "`nChecking prerequisites..." -ForegroundColor Yellow

$missingPrereqs = @()

if (-not (Test-Command "docker")) {
    $missingPrereqs += "Docker Desktop"
}

if (-not (Test-Command "docker-compose")) {
    $missingPrereqs += "Docker Compose"
}

if (-not (Test-Command "python")) {
    $missingPrereqs += "Python 3"
}

if ($missingPrereqs.Count -gt 0) {
    Write-Host "Error: The following prerequisites are missing:" -ForegroundColor Red
    $missingPrereqs | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host "`nPlease install missing components and try again." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ All prerequisites are installed" -ForegroundColor Green

# Navigate to docker directory and start containers
Write-Host "`n1. Starting Docker containers..." -ForegroundColor Yellow
Set-Location -Path "docker"

# Stop any existing containers
docker-compose down 2>$null

# Start new containers
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to start Docker containers" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# Function to check container health
function Wait-ForContainer {
    param(
        [string]$ContainerName,
        [int]$MaxAttempts = 30
    )
    
    Write-Host "Waiting for $ContainerName to be ready..." -NoNewline
    
    for ($i = 0; $i -lt $MaxAttempts; $i++) {
        $health = docker inspect --format='{{.State.Health.Status}}' $ContainerName 2>$null
        
        if ($health -eq "healthy") {
            Write-Host " ✓" -ForegroundColor Green
            return $true
        }
        
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 2
    }
    
    Write-Host " ✗" -ForegroundColor Red
    return $false
}

# Wait for containers
Write-Host "`n2. Waiting for containers to be ready..." -ForegroundColor Yellow
Write-Host "This may take up to 30 seconds..." -ForegroundColor Gray

$containersReady = $true
$containersReady = $containersReady -and (Wait-ForContainer "postgres_db")
$containersReady = $containersReady -and (Wait-ForContainer "mongo_db")
$containersReady = $containersReady -and (Wait-ForContainer "elasticsearch_db")

if (-not $containersReady) {
    Write-Host "`nSome containers failed to start properly." -ForegroundColor Red
    Write-Host "Check Docker Desktop and container logs for details." -ForegroundColor Red
    Set-Location ..
    exit 1
}

# Return to project root
Set-Location ..

# Setup Python virtual environment
Write-Host "`n3. Setting up Python virtual environment..." -ForegroundColor Yellow

if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment and install dependencies
Write-Host "`n4. Installing Python dependencies..." -ForegroundColor Yellow

# Activate venv and install packages
& ".\venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Run Django migrations
Write-Host "`n5. Running Django migrations..." -ForegroundColor Yellow
python manage.py migrate

if ($LASTEXITCODE -ne 0) {
    Write-Host "Migration failed!" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Migrations completed" -ForegroundColor Green

# Create cache table
Write-Host "`n6. Creating cache table..." -ForegroundColor Yellow
python manage.py createcachetable
Write-Host "✓ Cache table created" -ForegroundColor Green

# Test database connections
Write-Host "`n7. Testing database connections..." -ForegroundColor Yellow
python test_connections.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n==================================================" -ForegroundColor Green
    Write-Host "✓ Setup completed successfully!" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "To run the Django development server:" -ForegroundColor Cyan
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "  python manage.py runserver" -ForegroundColor White
    Write-Host ""
    Write-Host "To test the benchmark API:" -ForegroundColor Cyan
    Write-Host "  Invoke-RestMethod -Uri http://localhost:8000/api/benchmark/ -Method POST -ContentType 'application/json' -Body '{`"record_count`": 1000, `"query_count`": 100}'" -ForegroundColor White
    Write-Host ""
    Write-Host "Or using curl (if installed):" -ForegroundColor Cyan
    Write-Host '  curl -X POST http://localhost:8000/api/benchmark/ -H "Content-Type: application/json" -d "{\"record_count\": 1000, \"query_count\": 100}"' -ForegroundColor White
    Write-Host ""
    Write-Host "To stop the containers:" -ForegroundColor Cyan
    Write-Host "  cd docker; docker-compose down" -ForegroundColor White
} else {
    Write-Host "`n✗ Setup failed. Please check the error messages above." -ForegroundColor Red
    exit 1
}

# Keep window open
Write-Host "`nPress Enter to close this window..." -ForegroundColor Gray
Read-Host