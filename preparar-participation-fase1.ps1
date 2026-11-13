[CmdletBinding()]
param([ValidateSet('CONTROL','RF-12','RF-23','RF-25')][string]$RF='CONTROL')
$ErrorActionPreference='Stop'
$anterior=$env:PYTHONIOENCODING
try {
 $env:PYTHONIOENCODING='utf-8'
 & (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') -B -u (Join-Path $PSScriptRoot 'backend\docs\postman\participation_fase1\preparar.py') --rf $RF
 if($LASTEXITCODE -ne 0){throw 'Laboratorio no completado. Revisar registros propios, sin tocar otros recursos.'}
} finally {
 if($null -eq $anterior){Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue}else{$env:PYTHONIOENCODING=$anterior}
}
