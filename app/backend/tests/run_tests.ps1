<#
.SYNOPSIS  Runs the AutoCare Pro regression tests against a THROW-AWAY PostgreSQL server (never the production database).
.DESCRIPTION
  Creates a temporary database server from the bundled PostgreSQL (runtime\pgsql) on a spare port, runs every test in this folder,
  then stops the server and deletes its files. The production services (AutoCarePG / AutoCarePro) and data are not touched.
  Usage (normal PowerShell, no administrator rights needed):   .\run_tests.ps1   [-Port 5598] [-Filter test_financial_audit.py]   (-Filter is a file pattern)
#>
[CmdletBinding()]
param([int]$Port = 5598, [string]$Filter = "")
$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $PSScriptRoot
$install = Split-Path -Parent $backend
if (-not (Test-Path "$install\runtime\pgsql\bin\initdb.exe")) { $install = Split-Path -Parent $install }  # installer-package layout: <package>\app\backend
$bin = Join-Path $install "runtime\pgsql\bin"
$py = Join-Path $install "runtime\python\python.exe"
if (-not (Test-Path "$bin\initdb.exe") -or -not (Test-Path $py)) { throw "runtime\pgsql or runtime\python not found next to the backend folder ($install)." }
if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) { throw "Port $Port is already in use; pass -Port <free port>." }

$work = Join-Path $env:TEMP ("autocare-tests-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$data = Join-Path $work "data"
New-Item -ItemType Directory -Force $work | Out-Null
$server = $null
$code = 1
try {
  & "$bin\initdb.exe" -D $data -U postgres -A trust -E UTF8 --no-locale | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "initdb failed (it cannot run from an administrator window: use a normal PowerShell)." }
  $server = Start-Process -FilePath "$bin\postgres.exe" -ArgumentList @("-D", $data, "-p", "$Port", "-c", "listen_addresses=127.0.0.1", "-c", "fsync=off", "-c", "max_connections=40") `
    -WindowStyle Hidden -PassThru -RedirectStandardOutput "$work\out.log" -RedirectStandardError "$work\err.log"
  $ready = $false
  for ($i = 0; $i -lt 40; $i++) { & "$bin\pg_isready.exe" -h 127.0.0.1 -p $Port 2>$null | Out-Null; if ($LASTEXITCODE -eq 0) { $ready = $true; break }; Start-Sleep 1 }
  if (-not $ready) { throw "The temporary database did not start (see $work\err.log)." }
  & "$bin\psql.exe" -h 127.0.0.1 -p $Port -U postgres -d postgres -c "create database autocare_test encoding 'UTF8' template template0" | Out-Null
  $env:AUTOCARE_TEST_DATABASE_URL = "postgresql+psycopg://postgres@127.0.0.1:$Port/autocare_test"
  Push-Location $backend
  try {
    if ($Filter) { & $py -X utf8 -W ignore -m unittest discover -s tests -t . -p $Filter -v } else { & $py -X utf8 -W ignore -m unittest discover -s tests -t . -v }
    $code = $LASTEXITCODE
  } finally { Pop-Location }
} finally {
  Remove-Item Env:AUTOCARE_TEST_DATABASE_URL -ErrorAction SilentlyContinue
  if ($server -and -not $server.HasExited) {
    & "$bin\pg_ctl.exe" -D $data stop -m fast 2>$null | Out-Null
    Start-Sleep 1
    if (-not $server.HasExited) { Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue }
  }
  Start-Sleep 1
  Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}
if ($code -eq 0) { Write-Host "`nALL TESTS PASSED" -ForegroundColor Green } else { Write-Host "`nTESTS FAILED (exit code $code)" -ForegroundColor Red }
exit $code
