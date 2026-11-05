$ErrorActionPreference = "Stop"

$root = "C:\Users\Haneesh\Documents\network_speed_test"
$serversFile = Join-Path $root "federation\servers.json"
$viteFile = Join-Path $root "dashboard\vite.config.js"
$appFile = Join-Path $root "dashboard\src\App.jsx"

Write-Host "`n=== Network Speed-Test Launcher ===" -ForegroundColor Cyan
$backendIp = Read-Host "Enter Santosh's current backend/server IP"

$parsedIp = $null
if (-not [System.Net.IPAddress]::TryParse($backendIp, [ref]$parsedIp) -or
    $parsedIp.AddressFamily -ne
    [System.Net.Sockets.AddressFamily]::InterNetwork) {
    throw "Please enter a valid IPv4 address."
}

$backendIp = $parsedIp.ToString()

$servers = Get-Content $serversFile -Raw | ConvertFrom-Json
if (@($servers.servers).Count -ne 3) {
    throw "Expected exactly three configured servers. No changes made."
}

$vite = Get-Content $viteFile -Raw
$matches = [regex]::Matches(
    $vite,
    "target:\s*'http://[^']+:5000'"
)


if ($matches.Count -ne 2) {
    throw "Expected exactly two backend proxy targets on port 5000. No changes made."
}

# Read and validate App.jsx
$app = Get-Content $appFile -Raw

$appPattern = 'host:\s*([''"])(?:\d{1,3}\.){3}\d{1,3}:(500[1-3])\1'
$appMatches = [regex]::Matches($app, $appPattern)

if ($appMatches.Count -ne 3) {
    throw "Expected three fallback server hosts in App.jsx. No changes made."
}

# Back up files


$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
Copy-Item $serversFile "$serversFile.$timestamp.bak"
Copy-Item $viteFile "$viteFile.$timestamp.bak"
Copy-Item $appFile "$appFile.$timestamp.bak"

try {
    foreach ($server in $servers.servers) {
        $server.host = $backendIp
    }

    $json = $servers | ConvertTo-Json -Depth 10
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($serversFile, $json, $utf8NoBom)

    $vite = [regex]::Replace(
        $vite,
        "target:\s*'http://[^']+:5000'",
        "target: 'http://${backendIp}:5000'"
    )
    Set-Content $viteFile $vite -Encoding utf8
    $app = [regex]::Replace(
        $app,
        $appPattern,
        {
            param($m)
            "host: $($m.Groups[1].Value)${backendIp}:$($m.Groups[2].Value)$($m.Groups[1].Value)"
        }
    )

    Set-Content $appFile $app -Encoding utf8

    Write-Host "`nChecking Santosh's backend..." -ForegroundColor Cyan
    $backendReady = $false
    try {
        $connection = Test-NetConnection $backendIp -Port 5000 `
            -WarningAction SilentlyContinue
        $backendReady = $connection.TcpTestSucceeded
    } catch {}

    if ($backendReady) {
        Write-Host "Backend port 5000 is reachable." -ForegroundColor Green
    } else {
        Write-Warning "Backend port 5000 is not reachable yet. Check that Santosh started Flask and that the network/firewall allows access."
    }

    
# Start federation registry synchronization
Write-Host "`nStarting federation registry synchronization..." -ForegroundColor Cyan

$registryScript = Join-Path $root "federation\server_registry_sync.py"
$pythonExe = Join-Path $root "validation\.venv\Scripts\python.exe"

if (-not (Test-Path $registryScript)) {
    throw "Registry script not found: $registryScript"
}

if (-not (Test-Path $pythonExe)) {
    throw "Project virtual-environment Python not found: $pythonExe"
}

$registryRunning = Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -and
        $_.CommandLine -like "*server_registry_sync.py*"
    }

if (-not $registryRunning) {
    $registryCommand = "`$env:BACKEND_URL='http://${backendIp}:5000'; Set-Location '$root'; & '$pythonExe' '$registryScript'"

    Start-Process powershell.exe -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $registryCommand
    )

    Write-Host "Federation registry synchronization started." -ForegroundColor Green
}
else {
    Write-Host "Federation registry synchronization is already running." -ForegroundColor Yellow
}

    Write-Host "`nStarting the local dashboard..." -ForegroundColor Cyan

    $listener = Get-NetTCPConnection -LocalPort 5173 `
        -State Listen -ErrorAction SilentlyContinue

    if (-not $listener) {
        Start-Process -FilePath "cmd.exe" `
            -WorkingDirectory (Join-Path $root "dashboard") `
            -ArgumentList "/k", "npm run dev"
        Start-Sleep -Seconds 4
    } else {
        Write-Host "Port 5173 already has a listener; not starting a duplicate." `
            -ForegroundColor Yellow
    }

    $edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
    if (!(Test-Path $edge)) {
        $edge = "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
    }

    if (Test-Path $edge) {
        Start-Process $edge "http://localhost:5173"
    } else {
        Start-Process "http://localhost:5173"
    }

    Write-Host "`nLauncher finished. Configuration backups are saved beside the original files." `
        -ForegroundColor Green
} catch {
    Copy-Item "$serversFile.$timestamp.bak" $serversFile -Force
    Copy-Item "$viteFile.$timestamp.bak" $viteFile -Force
    Copy-Item "$appFile.$timestamp.bak" $appFile -Force
    throw
}
