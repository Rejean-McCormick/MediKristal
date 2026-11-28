#requires -Version 7.0
[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8001,
    [string]$PublicIndex,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$repo = $PSScriptRoot
$deploy = Join-Path $repo 'deploy'
$state = Join-Path $repo '.local'
New-Item -ItemType Directory -Path $state -Force | Out-Null
$envFile = Join-Path $state 'compose.env'
if (-not (Test-Path -LiteralPath $envFile)) {
    $password = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(24))
    $secret = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    $envLines = @("MEDIKRISTAL_DB_PASSWORD=$password", "MEDIKRISTAL_AUTH_SECRET=$secret")
    [IO.File]::WriteAllLines($envFile, $envLines)
}
if (-not $PublicIndex) {
    $indexDir = Join-Path (Split-Path $repo -Parent) 'MediKristal-Donnees/index-public'
    if (Test-Path -LiteralPath $indexDir) {
        $indexes = @(Get-ChildItem -LiteralPath $indexDir -Filter '*.sqlite3' -File)
        if ($indexes.Count -eq 1) {
            $PublicIndex = $indexes[0].FullName
        } elseif ($indexes.Count -gt 1) {
            Write-Host 'Plusieurs index sont disponibles. Utilise -PublicIndex pour choisir une version.'
        }
    }
}
if ($PublicIndex) {
    $file = Get-Item -LiteralPath $PublicIndex
    if ($file.PSIsContainer) { throw 'PublicIndex doit désigner un fichier SQLite.' }
}
$yaml = @('services:', '  api:', '    environment:', '      MEDIKRISTAL_ENV: development',
          '      MEDIKRISTAL_LOCAL_EPISODE_DEMO: "1"')
if ($PublicIndex) {
    $quotedPath = $file.FullName.Replace('$', '$$').Replace("'", "''")
    $yaml += @('      MEDIKRISTAL_PUBLIC_INDEX: /app/public-index.sqlite3',
               '    volumes:', '      - type: bind', "        source: '$quotedPath'",
               '        target: /app/public-index.sqlite3', '        read_only: true',
               '        bind:', '          create_host_path: false')
}
$override = Join-Path $state 'local.compose.yml'
[IO.File]::WriteAllLines($override, $yaml)
$compose = @('compose', '--project-name', 'medikristal-v2', '--env-file', $envFile,
             '-f', (Join-Path $deploy 'docker-compose.yml'), '-f', $override)
$previousPort = $env:MEDIKRISTAL_PORT
try {
    $env:MEDIKRISTAL_PORT = "$Port"
    & docker @compose up --detach --build --wait --wait-timeout 180
} finally {
    $env:MEDIKRISTAL_PORT = $previousPort
}
$url = "http://127.0.0.1:$Port/episodes"
Invoke-RestMethod -Uri "http://127.0.0.1:$Port/readyz" -TimeoutSec 15 | Out-Null
Write-Host "MediKristal · $url"
if (-not $NoBrowser) { Start-Process $url }
