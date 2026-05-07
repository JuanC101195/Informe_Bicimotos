<#
.SYNOPSIS
  Regenera el dashboard de Informe_Bicimotos y lo publica en GitHub Pages.

.DESCRIPTION
  Toma dos Excels (GPS + nopagos), corre el CLI, valida local en reportes/,
  y si confirmas publica a docs/, hace commit, push y merge a main.

.EXAMPLE
  .\actualizar.ps1 -Gps "C:\Users\LeNoVo\Downloads\reports_gps.xlsx" `
                   -Nopagos "C:\Users\LeNoVo\Downloads\nopagos.xlsx"

.EXAMPLE
  # Solo regenerar local, no tocar git:
  .\actualizar.ps1 -Gps "..." -Nopagos "..." -SoloLocal
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$Gps,

    [Parameter(Mandatory=$true)]
    [string]$Nopagos,

    [switch]$SoloLocal
)

$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$python = "C:\Users\LeNoVo\AppData\Local\Programs\Python\Python312\python.exe"

function Fail($msg) {
    Write-Host "[ERROR] $msg" -ForegroundColor Red
    exit 1
}

# 1. Validaciones
if (-not (Test-Path $python))   { Fail "No encuentro Python 3.12 en $python" }
if (-not (Test-Path $Gps))      { Fail "No existe el Excel GPS: $Gps" }
if (-not (Test-Path $Nopagos))  { Fail "No existe el Excel nopagos: $Nopagos" }

Set-Location $repo

if (-not $SoloLocal) {
    $dirty = git status --porcelain
    if ($dirty) {
        Fail "Working tree no esta limpio. Commitea o stashea antes de seguir.`n$dirty"
    }
    $branchActual = git branch --show-current
    if ($branchActual -ne "main") {
        Fail "Estas en '$branchActual'. Cambiate a main antes de correr esto: git checkout main"
    }
}

# 2. Generar local primero (validacion)
$gpsAbs     = (Resolve-Path $Gps).Path
$nopagosAbs = (Resolve-Path $Nopagos).Path

Write-Host ""
Write-Host "=== Generando dashboard local ===" -ForegroundColor Cyan
Write-Host "  GPS    : $gpsAbs"
Write-Host "  Nopagos: $nopagosAbs"
Write-Host ""

& $python cli.py reporte --input $gpsAbs --nopagos $nopagosAbs --out "reportes/bicimotos.html"
if ($LASTEXITCODE -ne 0) { Fail "El CLI fallo (exit $LASTEXITCODE)" }

$reporteLocal = Join-Path $repo "reportes\bicimotos.html"
Write-Host ""
Write-Host "Reporte local: $reporteLocal" -ForegroundColor Green

if ($SoloLocal) {
    Write-Host "Modo -SoloLocal: no toco git. Abriendo el reporte..." -ForegroundColor Yellow
    Start-Process $reporteLocal
    return
}

# 3. Confirmacion antes de publicar
Write-Host ""
Start-Process $reporteLocal
Write-Host "Revisa el reporte que se acaba de abrir." -ForegroundColor Yellow
$resp = Read-Host "Publicar a GitHub Pages (commit + push + merge a main)? [s/N]"
if ($resp -notmatch '^[sS]') {
    Write-Host "Cancelado. El reporte queda en reportes/bicimotos.html" -ForegroundColor Yellow
    return
}

# 4. Branch + copia a docs/ + commit + push + merge
$fecha = Get-Date -Format "yyyy-MM-dd"
$branch = "docs/regenera-dashboard-$fecha"

Write-Host ""
Write-Host "=== Publicando ===" -ForegroundColor Cyan

git checkout -b $branch 2>$null
if ($LASTEXITCODE -ne 0) {
    git checkout $branch
    if ($LASTEXITCODE -ne 0) { Fail "No pude crear ni checkout de $branch" }
}

Copy-Item "reportes\bicimotos.html" "docs\index.html" -Force
Copy-Item "reportes\imprimir.html"  "docs\imprimir.html" -Force

git add docs/index.html docs/imprimir.html
$staged = git diff --cached --name-only
if (-not $staged) {
    Write-Host "No hay diferencias en docs/. Volviendo a main..." -ForegroundColor Yellow
    git checkout main
    git branch -d $branch 2>$null
    return
}

# Mensaje de commit (archivo temporal porque PowerShell rompe -m multilinea)
$msgFile = Join-Path $repo ".commit_msg.tmp"
@"
docs(pages): regenera dashboard $fecha

Procesado con:
  GPS:     $(Split-Path $gpsAbs -Leaf)
  Nopagos: $(Split-Path $nopagosAbs -Leaf)
"@ | Set-Content -Path $msgFile -Encoding utf8

try {
    git commit -F $msgFile
    if ($LASTEXITCODE -ne 0) { Fail "git commit fallo" }
} finally {
    Remove-Item $msgFile -Force -ErrorAction SilentlyContinue
}

git push -u origin $branch
if ($LASTEXITCODE -ne 0) { Fail "git push de la rama fallo" }

git checkout main
git merge --no-ff $branch -m "Merge $branch"
if ($LASTEXITCODE -ne 0) { Fail "git merge a main fallo" }

git push origin main
if ($LASTEXITCODE -ne 0) { Fail "git push de main fallo" }

Write-Host ""
Write-Host "OK -> Publicado en https://juanc101195.github.io/Informe_Bicimotos/" -ForegroundColor Green
Write-Host "     (GitHub Pages tarda 1-2 min en propagar)" -ForegroundColor Green
