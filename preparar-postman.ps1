[CmdletBinding()]
param([ValidateSet('1','2','3')][string]$Opcion)
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonLab = Join-Path $projectRoot '.venv\Scripts\python.exe'
$desktopScript = Join-Path $projectRoot 'backend\docs\postman\entrega_20261109\desktop.py'
if (-not (Test-Path -LiteralPath $pythonLab)) { throw 'Falta .venv. Consulte GUIA_POSTMAN_SUSTENTACION.md para instalar dependencias.' }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Falta Docker Desktop/CLI. No se usará ninguna base existente.' }
$modos = @{ '1'='principal'; '2'='reportes'; '3'='worker' }
$modoUnico = -not [string]::IsNullOrEmpty($Opcion)
$oldEncoding = $env:PYTHONIOENCODING
$savedConsoleEncoding = [Console]::OutputEncoding
$savedPipeEncoding = $OutputEncoding
try {
    $env:PYTHONIOENCODING = 'utf-8'
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
    $OutputEncoding = [Text.UTF8Encoding]::new($false)
    do {
        if (-not $modoUnico) {
            Write-Host "`nPROYECTO NUCLEAR — POSTMAN DESKTOP"
            Write-Host '1. Recorrido principal (MAIN + inicio LAB explícito)'
            Write-Host '2. Evaluación oficial y reportes RF-16 (MAIN)'
            Write-Host '3. Worker RF-19 (MAIN + w en esta consola)'
            Write-Host 'q. Salir'
            $Opcion = Read-Host 'Seleccione'
            if ($Opcion -eq 'q') { break }
            if (-not $modos.ContainsKey($Opcion)) { Write-Host 'Seleccione 1, 2, 3 o q.'; continue }
        }
        & $pythonLab -B -u $desktopScript --modo $modos[$Opcion]
        if ($LASTEXITCODE -ne 0) { Write-Warning 'El laboratorio no finalizó correctamente. Revise la guía; no se tocaron recursos ajenos.' }
        if ($modoUnico) { if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; break }
    } while ($true)
} finally {
    [Console]::OutputEncoding = $savedConsoleEncoding
    $OutputEncoding = $savedPipeEncoding
    if ($null -eq $oldEncoding) { Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue }
    else { $env:PYTHONIOENCODING = $oldEncoding }
}
