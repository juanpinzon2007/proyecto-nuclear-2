[CmdletBinding()]
param([Parameter(Mandatory=$true)][ValidatePattern('^RF-(0[1-9]|1[0-9]|2[0-7])$')][string]$RF)
$ErrorActionPreference='Stop'
$anterior=$env:PYTHONIOENCODING
$consoleAnterior=[Console]::OutputEncoding
$pipeAnterior=$OutputEncoding
try {
    $env:PYTHONIOENCODING='utf-8'
    [Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
    $OutputEncoding=[Text.UTF8Encoding]::new($false)
    & (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') -B -u (Join-Path $PSScriptRoot 'backend\docs\postman\cobertura_27rf\ejecutar_rf.py') --rf $RF --preparar
    if($LASTEXITCODE -ne 0){throw 'No se completo el laboratorio propio; revise Docker y las evidencias.'}
} finally {
    [Console]::OutputEncoding=$consoleAnterior
    $OutputEncoding=$pipeAnterior
    if($null -eq $anterior){Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue}else{$env:PYTHONIOENCODING=$anterior}
}
