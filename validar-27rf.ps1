[CmdletBinding()]
param([string]$ModuloNewman)
$ErrorActionPreference='Stop'
if([string]::IsNullOrEmpty($ModuloNewman)){
    $registro=Join-Path $PSScriptRoot 'evidencias\postman_desktop_20261108\newman_runtime.json'
    if(Test-Path -LiteralPath $registro){$r=Get-Content -Raw -LiteralPath $registro | ConvertFrom-Json;$ModuloNewman=Join-Path $r.ruta 'node_modules\newman'}
}
if([string]::IsNullOrEmpty($ModuloNewman) -or -not(Test-Path -LiteralPath (Join-Path $ModuloNewman 'package.json'))){throw 'Indique -ModuloNewman con el modulo privado instalado. Consulte README.md de cobertura_27rf.'}
$python27=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$script27=Join-Path $PSScriptRoot 'backend\docs\postman\cobertura_27rf\ejecutar_rf.py'
$destino27=Join-Path $PSScriptRoot ('evidencias\cobertura_27rf_run_'+[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')+'_'+[guid]::NewGuid().ToString('N').Substring(0,6))
Push-Location -LiteralPath $PSScriptRoot
try {
    & $python27 -B -u $script27 --rf todos --newman $ModuloNewman --evidencias $destino27
    $codigoHTTP27=$LASTEXITCODE
    & $python27 -B (Join-Path $PSScriptRoot 'backend\docs\postman\cobertura_27rf\informar.py') --evidencias $destino27
    if($LASTEXITCODE -ne 0){throw ('No se pudo conciliar la matriz; revisar '+$destino27)}
    if($codigoHTTP27 -ne 0){throw ('Hubo fallos tecnicos; matriz y logs conservados en '+$destino27)}
    Write-Host ('Evidencias nominales: '+$destino27)
    Write-Host 'Revise los veredictos por RF. Aserciones verdes no significan 27 RF aprobados.'
} finally {Pop-Location}
