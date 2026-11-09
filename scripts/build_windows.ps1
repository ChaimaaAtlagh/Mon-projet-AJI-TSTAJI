[CmdletBinding()]
param(
    [string]$Version,
    [string]$ApiBaseUrl = $env:AJI_PUBLIC_API_BASE_URL,
    [string]$PythonPath = $env:AJI_BUILD_PYTHON,
    [switch]$SkipInstaller,
    [switch]$AllowEmptyApiUrlForTests
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$defaultPython = Join-Path $root ".venv\Scripts\python.exe"
$python = if ([string]::IsNullOrWhiteSpace($PythonPath)) { $defaultPython } else { $PythonPath }
$spec = Join-Path $root "AJI_TSTAJI.spec"
$installerSpec = Join-Path $root "deployment\AJI_TSTAJI.iss"
$versionFile = Join-Path $root "deployment\VERSION"
$readme = Join-Path $root "deployment\README_WINDOWS.md"
$envExample = Join-Path $root "deployment\AJI_TSTAJI.env.example"

if (-not $Version) {
    $Version = (Get-Content -LiteralPath $versionFile -Raw).Trim()
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version invalide '$Version'. Utilisez le format numérique X.Y.Z."
}
if (-not [string]::IsNullOrWhiteSpace($ApiBaseUrl)) {
    $apiUri = $null
    if (-not [Uri]::TryCreate($ApiBaseUrl, [UriKind]::Absolute, [ref]$apiUri)) {
        throw "AJI_PUBLIC_API_BASE_URL doit être une URL absolue HTTPS terminant par /api/v1."
    }
    $apiHost = $apiUri.Host.ToLowerInvariant()
    $parsedIp = $null
    $isIpLiteral = [System.Net.IPAddress]::TryParse($apiHost, [ref]$parsedIp)
    if (
        $apiUri.Scheme -ne "https" -or
        -not $apiUri.AbsolutePath.TrimEnd('/').EndsWith('/api/v1', [StringComparison]::OrdinalIgnoreCase) -or
        $apiUri.IsLoopback -or
        $apiUri.UserInfo -or $apiUri.Query -or $apiUri.Fragment -or
        $isIpLiteral -or
        $apiHost -in @("example.com", "example.org", "example.net") -or
        $apiHost.EndsWith(".localhost") -or $apiHost.EndsWith(".local") -or
        $apiHost.EndsWith(".example") -or $apiHost.EndsWith(".example.com") -or
        $apiHost.EndsWith(".example.org") -or $apiHost.EndsWith(".example.net") -or
        $apiHost.EndsWith(".test") -or $apiHost.EndsWith(".invalid")
    ) {
        throw "L'URL de l'API doit être une URL HTTPS publique réelle se terminant par /api/v1."
    }
}
else {
    if (-not $AllowEmptyApiUrlForTests) {
        throw "Renseignez AJI_PUBLIC_API_BASE_URL. L'option -AllowEmptyApiUrlForTests est réservée aux tests locaux/CI non distribuables."
    }
    Write-Warning "Aucune URL publique fournie : le paquet de test refusera toute connexion locale et ne peut pas être publié."
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "Interpréteur Python de build introuvable : $python"
}
$python = (Resolve-Path -LiteralPath $python).Path
$pythonVersion = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0) {
    throw "Impossible de démarrer l'interpréteur de build : $python"
}
$projectPythonVersion = & $defaultPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or $projectPythonVersion -ne $pythonVersion) {
    throw "Le Python de build ($pythonVersion) doit utiliser la même version majeure/mineure que .venv ($projectPythonVersion)."
}
& $python -c "from openai import OpenAI; assert OpenAI is not None"
if ($LASTEXITCODE -ne 0) {
    throw "Le SDK OpenAI requis par le chatbot est absent ou incomplet dans .venv. Installez requirements.txt avant le build."
}
if (-not (Test-Path -LiteralPath $spec)) {
    throw "Fichier PyInstaller introuvable : $spec"
}
if (-not (Test-Path -LiteralPath (Join-Path $root "data\cleaned\data_nettoyee.xlsx"))) {
    throw "Le dataset nettoyé data\cleaned\data_nettoyee.xlsx est absent."
}

$compiler = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $compiler) {
    foreach ($candidate in @(
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 7\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 7\ISCC.exe")
    )) {
        if (Test-Path -LiteralPath $candidate) {
            $compiler = $candidate
            break
        }
    }
}
if (-not $SkipInstaller -and (-not $compiler -or -not (Test-Path -LiteralPath $installerSpec))) {
    throw "Inno Setup (ISCC.exe) est requis pour produire l'installateur. Utilisez -SkipInstaller uniquement pour un build portable local."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$outputRoot = Join-Path $root "release\windows-v$Version-$stamp"
if (Test-Path -LiteralPath $outputRoot) {
    throw "Le dossier de sortie existe déjà, aucun ancien build ne sera remplacé : $outputRoot"
}
$distRoot = Join-Path $outputRoot "dist"
$workRoot = Join-Path $outputRoot "work"
$configRoot = Join-Path $outputRoot "build-config"
$packageDir = Join-Path $outputRoot "package"
$exeName = "AJI_TSTAJI_FINAL.exe"
$installerName = "AJI_TSTAJI_Setup.exe"
$zipPath = Join-Path $outputRoot "AJI_TSTAJI_FINAL-Windows-v$Version.zip"
$clientConfigPath = Join-Path $configRoot "client_api.json"

New-Item -ItemType Directory -Path $distRoot,$workRoot,$configRoot,$packageDir | Out-Null
$clientConfig = @{ api_base_url = $ApiBaseUrl }
$json = $clientConfig | ConvertTo-Json -Compress
[System.IO.File]::WriteAllText(
    $clientConfigPath,
    $json,
    [System.Text.UTF8Encoding]::new($false)
)

$oldApiConfigPath = [Environment]::GetEnvironmentVariable("AJI_API_CONFIG_FILE", "Process")
$oldInstallerSource = [Environment]::GetEnvironmentVariable("AJI_INSTALLER_SOURCE", "Process")
$oldInstallerOutput = [Environment]::GetEnvironmentVariable("AJI_INSTALLER_OUTPUT", "Process")
$oldInstallerVersion = [Environment]::GetEnvironmentVariable("AJI_INSTALLER_VERSION", "Process")
$oldInstallerIcon = [Environment]::GetEnvironmentVariable("AJI_INSTALLER_ICON", "Process")

Push-Location $root
try {
    $env:AJI_API_CONFIG_FILE = $clientConfigPath
    & $python -m PyInstaller --noconfirm --clean `
        --distpath $distRoot --workpath $workRoot $spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller a échoué avec le code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
    if ($null -eq $oldApiConfigPath) { Remove-Item Env:AJI_API_CONFIG_FILE -ErrorAction SilentlyContinue }
    else { $env:AJI_API_CONFIG_FILE = $oldApiConfigPath }
}

$builtExePath = Join-Path $distRoot $exeName
if (-not (Test-Path -LiteralPath $builtExePath)) {
    throw "La compilation est terminée mais l'exécutable est absent : $builtExePath"
}
$archiveViewer = Join-Path (Split-Path -Parent $python) "pyi-archive_viewer.exe"
if (-not (Test-Path -LiteralPath $archiveViewer)) {
    throw "pyi-archive_viewer est absent; impossible de vérifier les modules et la configuration intégrés."
}
$archiveEntries = @(& $archiveViewer -l -r $builtExePath 2>&1)
if ($LASTEXITCODE -ne 0 -or -not [bool]($archiveEntries -match "openai")) {
    throw "OpenAI n'a pas été intégré à l'exécutable PyInstaller."
}
if (-not [bool]($archiveEntries -match "client_api.json")) {
    throw "La configuration d'API publique n'a pas été intégrée à l'exécutable."
}
if ($archiveEntries -match "(?i)(^|[/\\])\.env(['\s,]|$)") {
    throw "Un fichier .env semble intégré à l'exécutable; le build est interrompu."
}
Copy-Item -LiteralPath $builtExePath -Destination (Join-Path $packageDir $exeName)
Copy-Item -LiteralPath $builtExePath -Destination (Join-Path $outputRoot $exeName)
$exePath = Join-Path $outputRoot $exeName
Copy-Item -LiteralPath $readme -Destination (Join-Path $packageDir "LISEZ-MOI.md")
Copy-Item -LiteralPath $envExample -Destination (Join-Path $packageDir "AJI_TSTAJI.env.example")

$forbiddenFiles = @(
    Get-ChildItem -LiteralPath $packageDir -Recurse -File | Where-Object {
        $_.Name -eq ".env" -or
        $_.Name -match '(?i)\.(db|sqlite|sqlite3)$' -or
        $_.Name -match '(?i)^(utilisateurs\.json|.*secret.*|.*password.*)$'
    }
)
if ($forbiddenFiles.Count -gt 0) {
    throw "Fichier privé détecté dans le paquet : $($forbiddenFiles[0].FullName)"
}
Compress-Archive -LiteralPath $packageDir -DestinationPath $zipPath -CompressionLevel Optimal
Get-FileHash -LiteralPath $exePath -Algorithm SHA256 |
    ForEach-Object { "$($_.Hash)  $([IO.Path]::GetFileName($exePath))" } |
    Set-Content -LiteralPath "$exePath.sha256" -Encoding ascii
Get-FileHash -LiteralPath $zipPath -Algorithm SHA256 |
    ForEach-Object { "$($_.Hash)  $([IO.Path]::GetFileName($zipPath))" } |
    Set-Content -LiteralPath "$zipPath.sha256" -Encoding ascii

$installerPath = $null
if (-not $SkipInstaller) {
    try {
        $env:AJI_INSTALLER_SOURCE = $packageDir
        $env:AJI_INSTALLER_OUTPUT = $outputRoot
        $env:AJI_INSTALLER_VERSION = $Version
        $env:AJI_INSTALLER_ICON = Join-Path $root "app\assets\AJI_TSTAJI.ico"
        & $compiler $installerSpec
        if ($LASTEXITCODE -ne 0) {
            throw "La compilation Inno Setup a échoué avec le code $LASTEXITCODE."
        }
        $installerPath = Join-Path $outputRoot $installerName
        if (-not (Test-Path -LiteralPath $installerPath)) {
            throw "L'installateur attendu est absent : $installerPath"
        }
        Get-FileHash -LiteralPath $installerPath -Algorithm SHA256 |
            ForEach-Object { "$($_.Hash)  $([IO.Path]::GetFileName($installerPath))" } |
            Set-Content -LiteralPath "$installerPath.sha256" -Encoding ascii
    }
    finally {
        if ($null -eq $oldInstallerSource) { Remove-Item Env:AJI_INSTALLER_SOURCE -ErrorAction SilentlyContinue }
        else { $env:AJI_INSTALLER_SOURCE = $oldInstallerSource }
        if ($null -eq $oldInstallerOutput) { Remove-Item Env:AJI_INSTALLER_OUTPUT -ErrorAction SilentlyContinue }
        else { $env:AJI_INSTALLER_OUTPUT = $oldInstallerOutput }
        if ($null -eq $oldInstallerVersion) { Remove-Item Env:AJI_INSTALLER_VERSION -ErrorAction SilentlyContinue }
        else { $env:AJI_INSTALLER_VERSION = $oldInstallerVersion }
        if ($null -eq $oldInstallerIcon) { Remove-Item Env:AJI_INSTALLER_ICON -ErrorAction SilentlyContinue }
        else { $env:AJI_INSTALLER_ICON = $oldInstallerIcon }
    }
}

Write-Host "Version       : $Version"
Write-Host "Application   : $exePath"
Write-Host "Empreinte EXE : $exePath.sha256"
Write-Host "Paquet ZIP    : $zipPath"
Write-Host "Empreinte ZIP : $zipPath.sha256"
if ($installerPath) {
    Write-Host "Installateur  : $installerPath"
    Write-Host "Empreinte EXE : $installerPath.sha256"
}
