param(
    [ValidateSet('todos','participation','evaluation','feedback')][string]$Escenario = 'todos',
    [switch]$Pausar
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$python = Join-Path $repo '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'No se encuentra el Python de .venv.' }
$activos = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^python(w)?\.exe$' -and $_.CommandLine -match 'pytest'
}
if ($activos) { throw 'Hay otra ejecución pytest activa. Espere a que termine.' }
$rama = & git -C $repo branch --show-current
if ($LASTEXITCODE -ne 0 -or $rama.Trim() -ne 'feature/integracion-backend') {
    throw 'La rama actual no es feature/integracion-backend. No se cambió de rama.'
}
# Consultar una imagen instalada no descarga nada ni utiliza contenedores existentes.
& docker image inspect docker.io/library/postgres:17 --format '{{.Id}}'
if ($LASTEXITCODE -ne 0) { throw 'Se requiere Docker activo y la imagen postgres:17 instalada.' }
$salida = Join-Path $PSScriptRoot ('salidas/' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff') + '_' + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $salida | Out-Null
$archivo = Join-Path $PSScriptRoot 'test_demostracion.py'
$seleccion = @{ participation='test_01'; evaluation='test_02'; feedback='test_03' }
$argumentos = @('-B','-m','pytest','-c',(Join-Path $repo 'backend/pyproject.toml'),$archivo,'-s','-v','-rs','--tb=short')
if ($Escenario -ne 'todos') { $argumentos += @('-k',$seleccion[$Escenario]) }
$variables = @('PYTHONPATH','PYTHONDONTWRITEBYTECODE','PYTHONIOENCODING','SPS_TEST_IDENTITY_MAPPING_DOCKER','SPS_TEST_POSTGRESQL','TEST_DATABASE_URL','SPS_IDENTITY_TEST_URL','SPS_PERSISTENCE_LAB_URL','SPS_EVIDENCIAS_DIR','SPS_EVIDENCIA_PAUSA')
$anteriores = @{}
foreach ($nombre in $variables) { $anteriores[$nombre] = [Environment]::GetEnvironmentVariable($nombre,'Process') }
$codigo = 1
Push-Location $repo
try {
    $env:PYTHONPATH = Join-Path $repo 'backend'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:SPS_TEST_IDENTITY_MAPPING_DOCKER = '1'
    $env:SPS_TEST_POSTGRESQL = '0'
    foreach ($nombre in @('TEST_DATABASE_URL','SPS_IDENTITY_TEST_URL','SPS_PERSISTENCE_LAB_URL')) {
        [Environment]::SetEnvironmentVariable($nombre,$null,'Process')
    }
    $env:SPS_EVIDENCIAS_DIR = $salida
    $env:SPS_EVIDENCIA_PAUSA = $(if ($Pausar) {'1'} else {'0'})
    Write-Host "LABORATORIO AISLADO. Evidencias: $salida"
    # La transcripción no incluye tokens ni cadenas de conexión.
    Start-Transcript -Path (Join-Path $salida 'consola.txt') | Out-Null
    try {
        & $python @argumentos
        $codigo = $LASTEXITCODE
    } finally { Stop-Transcript | Out-Null }
} finally {
    foreach ($nombre in $variables) { [Environment]::SetEnvironmentVariable($nombre,$anteriores[$nombre],'Process') }
    Pop-Location
}
if ($codigo -ne 0) { throw "La demostración falló (código $codigo). Conserve la evidencia; no la presente como aprobada." }
Write-Host "Demostración terminada. Archivos JSON y consola: $salida"
