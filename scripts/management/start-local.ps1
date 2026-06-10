param(
    [switch]$SkipInstall,
    [string]$VenvPath = ".venv-local"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info($Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Warn($Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-ErrorAndExit($Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

function Resolve-PythonCommand {
    $pyCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCmd) {
        return @{
            Command = "py"
            Arguments = @("-3")
        }
    }

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return @{
            Command = $pythonCmd.Source
            Arguments = @()
        }
    }

    Write-ErrorAndExit "Python nao encontrado no PATH. Instale Python 3.9+ ou ajuste o PATH."
}

function Resolve-DockerCommand {
    $dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
    if ($dockerCmd) {
        return $dockerCmd.Source
    }

    return $null
}

function Invoke-Python {
    param(
        [Parameter(Mandatory = $true)]
        [hashtable]$PythonSpec,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [string]$WorkingDirectory
    )

    $allArgs = @()
    $allArgs += $PythonSpec.Arguments
    $allArgs += $Arguments

    if ($WorkingDirectory) {
        Push-Location $WorkingDirectory
    }

    try {
        & $PythonSpec.Command @allArgs | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw "Comando Python falhou com codigo $LASTEXITCODE"
        }
    } finally {
        if ($WorkingDirectory) {
            Pop-Location
        }
    }
}

function Load-EnvFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $values = @{}
    if (-not (Test-Path $Path)) {
        return $values
    }

    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        $separatorIndex = $trimmed.IndexOf("=")
        if ($separatorIndex -lt 1) {
            continue
        }

        $key = $trimmed.Substring(0, $separatorIndex).Trim()
        $value = $trimmed.Substring($separatorIndex + 1).Trim()
        $values[$key] = $value
    }

    return $values
}

function To-SqliteUri {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $normalized = $Path.Replace("\", "/")
    return "sqlite:///$normalized"
}

function New-LocalEnvironment {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot
    )

    $envPath = Join-Path $ProjectRoot ".env"
    $exampleEnvPath = Join-Path $ProjectRoot ".env.example"
    $values = Load-EnvFile -Path $(if (Test-Path $envPath) { $envPath } else { $exampleEnvPath })

    $frontendPort = if ($values.ContainsKey("FRONTEND_PORT")) { $values["FRONTEND_PORT"] } else { "3000" }
    $analysisPort = if ($values.ContainsKey("ANALYSIS_SERVICE_PORT")) { $values["ANALYSIS_SERVICE_PORT"] } else { "5002" }
    $accessPointPort = if ($values.ContainsKey("ACCESS_POINT_SERVICE_PORT")) { $values["ACCESS_POINT_SERVICE_PORT"] } else { "5004" }

    $accessPointRoot = Join-Path $ProjectRoot "services/access_point_service"
    $accessPointDbPath = Join-Path $accessPointRoot "instance/access_points.local.db"

    $instanceDirs = @(
        (Split-Path $accessPointDbPath -Parent)
    )

    foreach ($directory in $instanceDirs) {
        if (-not (Test-Path $directory)) {
            New-Item -ItemType Directory -Path $directory | Out-Null
        }
    }

    $values["FLASK_ENV"] = if ($values.ContainsKey("FLASK_ENV")) { $values["FLASK_ENV"] } else { "development" }
    $values["HOST"] = "127.0.0.1"
    $values["FRONTEND_SERVICE_URL"] = "http://127.0.0.1:$frontendPort"
    $values["ANALYSIS_SERVICE_URL"] = "http://127.0.0.1:$analysisPort"
    $values["ACCESS_POINT_SERVICE_URL"] = "http://127.0.0.1:$accessPointPort"
    $values["FRONTEND_HTTP_TIMEOUT"] = if ($values.ContainsKey("FRONTEND_HTTP_TIMEOUT")) { $values["FRONTEND_HTTP_TIMEOUT"] } else { "120" }
    $values["FRONTEND_HTTP_VERIFY_SSL"] = if ($values.ContainsKey("FRONTEND_HTTP_VERIFY_SSL")) { $values["FRONTEND_HTTP_VERIFY_SSL"] } else { "false" }
    $values["ACCESS_POINT_DATABASE_URI"] = To-SqliteUri -Path $accessPointDbPath

    return $values
}

function Ensure-VenvAndDependencies {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot,
        [Parameter(Mandatory = $true)]
        [string]$ResolvedVenvPath
    )

    $pythonSpec = Resolve-PythonCommand

    if (-not (Test-Path $ResolvedVenvPath)) {
        Write-Info "Criando ambiente virtual em $ResolvedVenvPath"
        Invoke-Python -PythonSpec $pythonSpec -Arguments @("-m", "venv", $ResolvedVenvPath) -WorkingDirectory $ProjectRoot
    }

    $venvPython = Join-Path $ResolvedVenvPath "Scripts/python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-ErrorAndExit "Python do ambiente virtual nao encontrado em $venvPython"
    }

    $venvSpec = @{
        Command = $venvPython
        Arguments = @()
    }

    if (-not $SkipInstall) {
        Write-Info "Atualizando pip"
        Invoke-Python -PythonSpec $venvSpec -Arguments @("-m", "pip", "install", "--upgrade", "pip") -WorkingDirectory $ProjectRoot

        $requirements = @(
            "services/frontend_service/requirements.txt",
            "services/access_point_service/requirements.txt"
        )

        foreach ($requirement in $requirements) {
            Write-Info "Instalando dependencias de $requirement"
            Invoke-Python -PythonSpec $venvSpec -Arguments @("-m", "pip", "install", "-r", (Join-Path $ProjectRoot $requirement)) -WorkingDirectory $ProjectRoot
        }
    }

    return $venvPython
}

function Start-ServiceWindow {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        [Parameter(Mandatory = $true)]
        [string]$WorkingDirectory,
        [Parameter(Mandatory = $true)]
        [string]$CommandExe,
        [Parameter(Mandatory = $true)]
        [string[]]$CommandArgs,
        [string[]]$PreCommands = @(),
        [Parameter(Mandatory = $true)]
        [hashtable]$Environment
    )

    $scriptLines = @(
        ('$Host.UI.RawUI.WindowTitle = ' + "'" + $Title.Replace("'", "''") + "'"),
        ('Set-Location ' + "'" + $WorkingDirectory.Replace("'", "''") + "'")
    )

    foreach ($key in ($Environment.Keys | Sort-Object)) {
        $value = [string]$Environment[$key]
        $escapedValue = $value.Replace("'", "''")
        $scriptLines += '$env:' + $key + " = '" + $escapedValue + "'"
    }

    foreach ($line in $PreCommands) {
        $scriptLines += $line
    }

    $quotedArgs = $CommandArgs | ForEach-Object {
        "'" + $_.Replace("'", "''") + "'"
    }
    $scriptLines += '& ' + "'" + $CommandExe.Replace("'", "''") + "'" + ' ' + ($quotedArgs -join ' ')

    $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) "PowerTrackZ"
    if (-not (Test-Path $tempRoot)) {
        New-Item -ItemType Directory -Path $tempRoot | Out-Null
    }

    $safeTitle = ($Title -replace '[^a-zA-Z0-9_-]', '_')
    $tempScriptPath = Join-Path $tempRoot ($safeTitle + ".ps1")
    Set-Content -Path $tempScriptPath -Value ($scriptLines -join [Environment]::NewLine) -Encoding UTF8

    $argumentList = "-NoExit -ExecutionPolicy Bypass -File `"$tempScriptPath`""
    Start-Process powershell -ArgumentList $argumentList | Out-Null
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$resolvedVenvPath = if ([System.IO.Path]::IsPathRooted($VenvPath)) {
    $VenvPath
} else {
    Join-Path $projectRoot $VenvPath
}

$venvPython = Ensure-VenvAndDependencies -ProjectRoot $projectRoot -ResolvedVenvPath $resolvedVenvPath
$dockerExe = Resolve-DockerCommand
$baseEnvironment = New-LocalEnvironment -ProjectRoot $projectRoot

$services = @(
    @{
        Title = "PowerTrackZ Access Point Service"
        WorkingDirectory = (Join-Path $projectRoot "services/access_point_service/app")
        CommandExe = $venvPython
        CommandArgs = @("main.py")
        Environment = @{
            PORT = $baseEnvironment["ACCESS_POINT_SERVICE_PORT"]
            ACCESS_POINT_DATABASE_URI = $baseEnvironment["ACCESS_POINT_DATABASE_URI"]
            ACCESS_POINT_HTTP_TIMEOUT = $baseEnvironment["ACCESS_POINT_HTTP_TIMEOUT"]
        }
    }
)

if ($dockerExe) {
    $analysisPort = $baseEnvironment["ANALYSIS_SERVICE_PORT"]
    $analysisAccessPointUrl = "http://host.docker.internal:$($baseEnvironment["ACCESS_POINT_SERVICE_PORT"])"
    $analysisImage = "powertrackz-analysis-service-local"
    $analysisContainer = "powertrackz-analysis-service-local"
    $analysisContext = (Join-Path $projectRoot "services/analysis_service")

    $services += @{
        Title = "PowerTrackZ Analysis Service (C)"
        WorkingDirectory = $projectRoot
        CommandExe = $dockerExe
        CommandArgs = @(
            "run",
            "--rm",
            "--name", $analysisContainer,
            "-p", ("127.0.0.1:{0}:{0}" -f $analysisPort),
            "-e", ("PORT={0}" -f $analysisPort),
            "-e", "HOST=0.0.0.0",
            "-e", ("ACCESS_POINT_SERVICE_URL={0}" -f $analysisAccessPointUrl),
            "-e", ("ANALYSIS_HTTP_TIMEOUT={0}" -f $baseEnvironment["ANALYSIS_HTTP_TIMEOUT"]),
            $analysisImage
        )
        PreCommands = @(
            "& '$($dockerExe.Replace("'", "''"))' rm -f '$analysisContainer' *> `$null",
            "& '$($dockerExe.Replace("'", "''"))' build -t '$analysisImage' '$($analysisContext.Replace("'", "''"))'"
        )
        Environment = @{
            PORT = $analysisPort
            ACCESS_POINT_SERVICE_URL = $analysisAccessPointUrl
            ANALYSIS_HTTP_TIMEOUT = $baseEnvironment["ANALYSIS_HTTP_TIMEOUT"]
        }
    }
} else {
    Write-Warn "Docker nao encontrado no PATH. O analysis_service em C nao sera iniciado por este script."
}

$services += @(
    @{
        Title = "PowerTrackZ Frontend Service"
        WorkingDirectory = (Join-Path $projectRoot "services/frontend_service")
        CommandExe = $venvPython
        CommandArgs = @("app.py")
        Environment = @{
            PORT = $baseEnvironment["FRONTEND_PORT"]
            FRONTEND_SECRET_KEY = $baseEnvironment["FRONTEND_SECRET_KEY"]
            ANALYSIS_SERVICE_URL = $baseEnvironment["ANALYSIS_SERVICE_URL"]
            ACCESS_POINT_SERVICE_URL = $baseEnvironment["ACCESS_POINT_SERVICE_URL"]
            FRONTEND_HTTP_TIMEOUT = $baseEnvironment["FRONTEND_HTTP_TIMEOUT"]
            FRONTEND_HTTP_VERIFY_SSL = $baseEnvironment["FRONTEND_HTTP_VERIFY_SSL"]
        }
    }
)

foreach ($service in $services) {
    $serviceEnv = @{}
    foreach ($pair in $baseEnvironment.GetEnumerator()) {
        $serviceEnv[$pair.Key] = [string]$pair.Value
    }
    foreach ($pair in $service.Environment.GetEnumerator()) {
        $serviceEnv[$pair.Key] = [string]$pair.Value
    }

    $serviceEnv["HOST"] = "127.0.0.1"
    $serviceEnv["FLASK_ENV"] = $baseEnvironment["FLASK_ENV"]
    $serviceEnv["LOG_LEVEL"] = $baseEnvironment["LOG_LEVEL"]
    $serviceEnv["LOG_FORMAT"] = $baseEnvironment["LOG_FORMAT"]

    Write-Info "Iniciando $($service.Title)"
    Start-ServiceWindow `
        -Title $service.Title `
        -WorkingDirectory $service.WorkingDirectory `
        -CommandExe $service.CommandExe `
        -CommandArgs $service.CommandArgs `
        -PreCommands $(if ($service.ContainsKey("PreCommands")) { $service.PreCommands } else { @() }) `
        -Environment $serviceEnv
}

Write-Host ""
Write-Info "Servicos iniciados em janelas separadas."
Write-Info "Frontend: http://127.0.0.1:$($baseEnvironment["FRONTEND_PORT"])"
Write-Info "Use Ctrl+C em cada janela para encerrar os servicos."
