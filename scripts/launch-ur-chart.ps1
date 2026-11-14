# UR Chart local demo launcher. Windows 10/11, PowerShell 5.1+.
# Sets up fictional demo data on the first launch. Never use with real patient records.
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$pythonExe = Join-Path $backend '.venv\Scripts\python.exe'
$marker = Join-Path $backend '.venv\.urchart-dependencies-ready'
$envFile = Join-Path $backend '.env'
$generatedTokenFile = Join-Path $backend '.demo-access-token'
$siteUrl = 'http://127.0.0.1:5173'

function Assert-LastCommand($description) {
  if ($LASTEXITCODE -ne 0) { throw "$description failed (exit code $LASTEXITCODE)." }
}
function New-DemoToken {
  $bytes = New-Object byte[] 36
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
  return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+','-').Replace('/','_')
}

Write-Host 'UR Chart | Local Demo Launcher' -ForegroundColor Cyan
Write-Host 'Educational prototype. Fictional patient data only.'
if (-not (Test-Path (Join-Path $backend 'app\main.py'))) { throw 'Cannot find the Python backend.' }
if (-not (Test-Path (Join-Path $frontend 'package.json'))) { throw 'Cannot find the React frontend.' }

if (-not (Test-Path $pythonExe)) {
  Write-Host 'Creating Python virtual environment...'
  $pythonCommand = if (Get-Command py.exe -ErrorAction SilentlyContinue) { 'py.exe' } elseif (Get-Command python.exe -ErrorAction SilentlyContinue) { 'python.exe' } else { $null }
  if (-not $pythonCommand) { throw 'Install Python 3.11+ and ensure py or python is in PATH.' }
  if ($pythonCommand -eq 'py.exe') { & $pythonCommand -3 -m venv (Join-Path $backend '.venv') }
  else { & $pythonCommand -m venv (Join-Path $backend '.venv') }
  Assert-LastCommand 'Python virtual environment creation'
}
if (-not (Test-Path $marker)) {
  Write-Host 'Installing Python dependencies (first run)...'
  & $pythonExe -m pip install -r (Join-Path $backend 'requirements-lock.txt')
  Assert-LastCommand 'Python dependency installation'
  Set-Content -Path $marker -Value 'Dependency installation completed' -Encoding Ascii
}

if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
  throw 'Install Node.js 20+ (includes npm), then run this shortcut again.'
}
if (-not (Test-Path (Join-Path $frontend 'node_modules\.bin\vite.cmd'))) {
  Write-Host 'Installing website dependencies (first run)...'
  Push-Location $frontend
  try { & npm.cmd ci; Assert-LastCommand 'npm ci' }
  finally { Pop-Location }
}

$createdDemo = $false
if (-not (Test-Path $envFile)) {
  Write-Host 'Creating local-only synthetic demo credentials...'
  $token = New-DemoToken
  $config = Get-Content (Join-Path $backend '.env.example') -Raw
  $config = [regex]::Replace($config,'(?m)^DEMO_AUTH_ENABLED=.*$','DEMO_AUTH_ENABLED=true')
  $config = [regex]::Replace($config,'(?m)^DEMO_TOKENS=.*$',('DEMO_TOKENS={"' + $token + '":"synthetic-demo-patient"}'))
  $config = [regex]::Replace($config,'(?m)^AI_PROVIDER=.*$','AI_PROVIDER=approved_instructions')
  [System.IO.File]::WriteAllText($envFile,$config,(New-Object System.Text.UTF8Encoding($false)))
  [System.IO.File]::WriteAllText($generatedTokenFile,$token,(New-Object System.Text.UTF8Encoding($false)))
  $createdDemo = $true
}

Write-Host 'Preparing the local database...'
Push-Location $backend
try {
  & $pythonExe -m alembic upgrade head
  Assert-LastCommand 'Database migration'
  # Seed is idempotent and runs only in demo-auth development mode.
  $settingsOutput = & $pythonExe -c 'from app.config import Settings; print(int(Settings().demo_auth_enabled))'
  Assert-LastCommand 'Backend settings check'
  if (($settingsOutput | Select-Object -Last 1) -eq '1') {
    & $pythonExe -m app.seed
    Assert-LastCommand 'Synthetic demo data setup'
  } else {
    Write-Warning 'Demo auth is off in backend/.env. You must configure it to sign in to the demo website.'
  }
}
finally { Pop-Location }

# Each server runs in its own visible command window so error messages remain readable.
Write-Host 'Starting FastAPI and React servers...'
$backendCommand = 'title UR Chart API && cd /d "' + $backend + '" && "' + $pythonExe + '" -m uvicorn app.main:app --reload --no-access-log'
$frontendCommand = 'title UR Chart Website && cd /d "' + $frontend + '" && npm run dev'
Start-Process -FilePath 'cmd.exe' -ArgumentList @('/k', $backendCommand) -WorkingDirectory $backend | Out-Null
Start-Process -FilePath 'cmd.exe' -ArgumentList @('/k', $frontendCommand) -WorkingDirectory $frontend | Out-Null

$ready = $false
for ($i=0; $i -lt 50; $i++) {
  try {
    $response = Invoke-WebRequest -Uri $siteUrl -UseBasicParsing -TimeoutSec 2
    if ($response.StatusCode -eq 200) { $ready = $true; break }
  } catch { Start-Sleep -Seconds 1 }
}
if (-not $ready) {
  Write-Warning 'Website did not respond. Check the two new terminal windows for errors.'
  throw "Could not reach $siteUrl"
}

if ($createdDemo -and (Test-Path $generatedTokenFile)) {
  $token = Get-Content $generatedTokenFile -Raw
  Write-Host ''
  Write-Host 'Your fictional patient demo token (copy and paste at login):' -ForegroundColor Yellow
  Write-Host $token.Trim() -ForegroundColor Green
  try { Set-Clipboard -Value $token.Trim(); Write-Host 'Token also copied to clipboard. Press Ctrl+V on the login screen.' }
  catch { Write-Host 'Copy the token displayed above to sign in.' }
} elseif (Test-Path $generatedTokenFile) {
  $token = (Get-Content $generatedTokenFile -Raw).Trim()
  try { Set-Clipboard -Value $token; Write-Host 'Previously generated fictional demo token copied to clipboard for login.' }
  catch { Write-Host 'See backend/.demo-access-token for your fictional demo token.' }
} else {
  Write-Host 'Sign in using a demo token from your existing backend/.env configuration.'
}
Write-Host "Opening $siteUrl" -ForegroundColor Cyan
Start-Process $siteUrl
Write-Host 'Keep the two server windows open. Close them to stop the local app.'
