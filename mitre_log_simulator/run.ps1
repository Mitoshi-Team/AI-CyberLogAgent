param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('start', 'stop', 'logs', 'restart')]
    [string]$Command,

    [string]$Technique,

    [switch]$RandomAttacks,

    [switch]$NoAttacks,

    [ValidateRange(1, 86400)]
    [int]$IntervalSeconds = 30,

    [ValidateRange(1, 10000)]
    [int]$NoiseBatchSize = 30,

    [switch]$Detached
)

$ErrorActionPreference = 'Stop'

$volumeName = if ($env:SHARED_EXTERNAL_LOGS_VOLUME_NAME) { $env:SHARED_EXTERNAL_LOGS_VOLUME_NAME } else { 'cyberlog_external_logs' }

switch ($Command) {
    'start' {
        docker volume create $volumeName | Out-Null

        # Ensure host bind folder exists (default: project root/shared_external_logs)
        $hostLogsDir = Join-Path (Resolve-Path "$PSScriptRoot\.." | Select-Object -ExpandProperty Path) 'shared_external_logs'
        if (-not (Test-Path $hostLogsDir)) {
            New-Item -ItemType Directory -Path $hostLogsDir | Out-Null
        }
        $env:SHARED_EXTERNAL_LOGS_BIND = $hostLogsDir

        if ($PSBoundParameters.ContainsKey('Technique')) {
            $env:SIM_TECHNIQUE = $Technique
        } else {
            Remove-Item Env:SIM_TECHNIQUE -ErrorAction SilentlyContinue
        }
        $env:SIM_RANDOM_ATTACKS = if ($RandomAttacks) { 'true' } else { 'false' }
        $env:SIM_NO_ATTACKS = if ($NoAttacks) { 'true' } else { 'false' }

        if ($PSBoundParameters.ContainsKey('IntervalSeconds')) {
            $env:SIM_INTERVAL_SECONDS = $IntervalSeconds
        } else {
            Remove-Item Env:SIM_INTERVAL_SECONDS -ErrorAction SilentlyContinue
        }

        if ($PSBoundParameters.ContainsKey('NoiseBatchSize')) {
            $env:SIM_NOISE_BATCH_SIZE = $NoiseBatchSize
        } else {
            Remove-Item Env:SIM_NOISE_BATCH_SIZE -ErrorAction SilentlyContinue
        }

        $env:SHARED_EXTERNAL_LOGS_VOLUME_NAME = $volumeName

        $composeArgs = @('compose', '-f', (Join-Path $PSScriptRoot 'docker-compose.yml'), 'up', '--build')
        if ($Detached) {
            $composeArgs += '--detach'
        }

        docker @composeArgs
    }
    'stop' {
        docker compose -f (Join-Path $PSScriptRoot 'docker-compose.yml') down
    }
    'logs' {
        docker compose -f (Join-Path $PSScriptRoot 'docker-compose.yml') logs -f
    }
    'restart' {
        docker compose -f (Join-Path $PSScriptRoot 'docker-compose.yml') down
        docker volume create $volumeName | Out-Null
        docker compose -f (Join-Path $PSScriptRoot 'docker-compose.yml') up --build
    }
}