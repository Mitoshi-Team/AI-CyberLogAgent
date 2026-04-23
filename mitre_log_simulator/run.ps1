param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "random", "fixed", "logs", "stop", "down", "help")]
    [string]$Command = "start",

    [ValidateSet("random", "fixed")]
    [string]$Mode = "random",

    [string]$Technique = "T1059",

    [int]$Interval = 90,

    [int]$MinInterval = 60,

    [int]$MaxInterval = 120,

    [int]$Seed = 42,

    [int]$Rate = 200,

    [int]$MaxLogs = 0,

    [int]$MaxIncidents = 0,

    [int]$MinIncidents = 0,

    [switch]$NoIncidents,

    [string]$HostName = "target-node-01",

    [string]$OutputDir,

    [switch]$OutputRoot,

    [switch]$NoBuild,

    [switch]$Logs,

    [switch]$Down,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Extra
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Show-Usage {
    @"
Usage:
  .\run.ps1 [command] [options]

Commands:
  start                      Start simulator (default)
  random                     Alias for start in random mode
  fixed [TECHNIQUE] [sec]    Start fixed mode (technique + optional interval)
  logs                       Follow container logs
  stop                       Stop and remove containers (alias: down)
  down                       Stop and remove containers
  help                       Show this help

Examples:
  .\run.ps1 start
  .\run.ps1 fixed T1059 60
  .\run.ps1 random -MinInterval 30 -MaxInterval 45 -Seed 123 -NoBuild
  .\run.ps1 fixed T1059 5 -MaxLogs 250 -MaxIncidents 3
  .\run.ps1 random -MaxLogs 250 -MinIncidents 3
  .\run.ps1 -OutputRoot
  .\run.ps1 logs
  .\run.ps1 stop
"@
}

switch ($Command) {
    "help" {
        Show-Usage
        exit 0
    }
    "random" {
        $Mode = "random"
    }
    "fixed" {
        $Mode = "fixed"
        if ($Extra.Count -ge 1 -and -not [string]::IsNullOrWhiteSpace($Extra[0])) {
            $Technique = $Extra[0]
        }
        if ($Extra.Count -ge 2 -and -not [string]::IsNullOrWhiteSpace($Extra[1])) {
            $parsedInterval = 0
            if (-not [int]::TryParse($Extra[1], [ref]$parsedInterval)) {
                Write-Error "Fixed interval must be an integer number of seconds"
            }
            $Interval = $parsedInterval
        }
    }
    "logs" {
        $Logs = $true
    }
    "stop" {
        $Down = $true
    }
    "down" {
        $Down = $true
    }
    "start" {
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not in PATH"
}

$useDockerComposeV2 = $false
try {
    docker compose version *> $null
    if ($LASTEXITCODE -eq 0) {
        $useDockerComposeV2 = $true
    }
} catch {
    $useDockerComposeV2 = $false
}

$useDockerComposeV1 = $false
if (-not $useDockerComposeV2 -and (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    $useDockerComposeV1 = $true
}

if (-not $useDockerComposeV2 -and -not $useDockerComposeV1) {
    Write-Error "Neither 'docker compose' nor 'docker-compose' is available"
}

if ($Mode -eq "fixed" -and [string]::IsNullOrWhiteSpace($Technique)) {
    Write-Error "For fixed mode, provide -Technique, e.g. -Technique T1059"
}

$env:ATTACK_MODE = $Mode
$env:FIXED_TECHNIQUE = $Technique
$env:ATTACK_INTERVAL = [string]$Interval
$env:ATTACK_INTERVAL_MIN = [string]$MinInterval
$env:ATTACK_INTERVAL_MAX = [string]$MaxInterval
$env:RANDOM_SEED = [string]$Seed
$env:LOG_RATE = [string]$Rate
$env:MAX_LOG_LINES = [string]$MaxLogs
$env:MAX_INCIDENTS = [string]$MaxIncidents
$env:MIN_INCIDENTS = [string]$MinIncidents
$env:DISABLE_INCIDENTS = if ($NoIncidents) { "1" } else { "0" }
$env:RESTART_POLICY = if ($MaxLogs -gt 0 -or $MaxIncidents -gt 0) { "no" } else { "unless-stopped" }
$env:HOSTNAME_OVERRIDE = $HostName

if ($OutputRoot) {
    $env:LOG_OUTPUT_DIR = (Resolve-Path -Path (Join-Path $PSScriptRoot "..")).Path
} elseif (-not [string]::IsNullOrWhiteSpace($OutputDir)) {
    if (-not (Test-Path -Path $OutputDir)) {
        New-Item -Path $OutputDir -ItemType Directory -Force | Out-Null
    }
    $env:LOG_OUTPUT_DIR = (Resolve-Path -Path $OutputDir).Path
}

if ($useDockerComposeV2) {
    if ($Down) {
        docker compose down --remove-orphans
        exit $LASTEXITCODE
    }
    if ($Logs) {
        docker compose logs -f mitre-log-simulator
        exit $LASTEXITCODE
    }

    if ($NoBuild) {
        docker compose up --remove-orphans
    } else {
        docker compose up --build --remove-orphans
    }
    exit $LASTEXITCODE
}

if ($Down) {
    docker-compose down --remove-orphans
    exit $LASTEXITCODE
}
if ($Logs) {
    docker-compose logs -f mitre-log-simulator
    exit $LASTEXITCODE
}

if ($NoBuild) {
    docker-compose up --remove-orphans
} else {
    docker-compose up --build --remove-orphans
}
exit $LASTEXITCODE
