# Network Speed Test launcher for Windows PowerShell 5.1+
# Updates server hosts in servers.json, App.jsx fallback hosts, and Vite backend defaults.
# Creates timestamped backups before writing and restores originals if a write fails.

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$ErrorActionPreference = 'Stop'

$projectRoot = 'C:\Users\Haneesh\Documents\network_speed_test'
$serversPath = Join-Path $projectRoot 'federation\servers.json'
$appPath = Join-Path $projectRoot 'dashboard\src\App.jsx'
$vitePath = Join-Path $projectRoot 'dashboard\vite.config.js'

foreach ($filePath in @($serversPath, $appPath, $vitePath)) {
    if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) {
        [System.Windows.Forms.MessageBox]::Show(
            "Cannot find required file:`n$filePath`n`nExpected project folder:`n$projectRoot",
            'Network Speed Test - File not found', 'OK', 'Error'
        ) | Out-Null
        exit 1
    }
}

# Prompt for Santosh's current IPv4 address. Avoid PlaceholderText, which is unavailable
# on some Windows PowerShell / .NET Framework Windows Forms TextBox controls.
$form = New-Object System.Windows.Forms.Form
$form.Text = 'Network Speed Test - Configure Server IP'
$form.Size = New-Object System.Drawing.Size(520, 230)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.Topmost = $true

$label = New-Object System.Windows.Forms.Label
$label.Location = New-Object System.Drawing.Point(18, 18)
$label.Size = New-Object System.Drawing.Size(470, 45)
$label.Text = "Enter Santosh's CURRENT IPv4 address on the same reachable network.`r`nThe launcher updates project configuration and starts the dashboard."
$form.Controls.Add($label)

$ipBox = New-Object System.Windows.Forms.TextBox
$ipBox.Location = New-Object System.Drawing.Point(20, 72)
$ipBox.Size = New-Object System.Drawing.Size(455, 28)
$ipBox.Font = New-Object System.Drawing.Font('Segoe UI', 11)
$ipBox.Text = ''
$form.Controls.Add($ipBox)

$note = New-Object System.Windows.Forms.Label
$note.Location = New-Object System.Drawing.Point(20, 108)
$note.Size = New-Object System.Drawing.Size(460, 25)
$note.Text = 'Backend port 5000 and measurement ports 5001–5003 are preserved.'
$form.Controls.Add($note)

$launchButton = New-Object System.Windows.Forms.Button
$launchButton.Location = New-Object System.Drawing.Point(270, 145)
$launchButton.Size = New-Object System.Drawing.Size(205, 32)
$launchButton.Text = 'Update & Launch Dashboard'
$launchButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
$form.Controls.Add($launchButton)
$form.AcceptButton = $launchButton

$cancelButton = New-Object System.Windows.Forms.Button
$cancelButton.Location = New-Object System.Drawing.Point(165, 145)
$cancelButton.Size = New-Object System.Drawing.Size(95, 32)
$cancelButton.Text = 'Cancel'
$cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$form.Controls.Add($cancelButton)

$result = $form.ShowDialog()
if ($result -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }

$serverIp = $ipBox.Text.Trim()
$parsedIp = $null
if (-not [System.Net.IPAddress]::TryParse($serverIp, [ref]$parsedIp) -or
    $parsedIp.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
    [System.Windows.Forms.MessageBox]::Show(
        'Enter a valid IPv4 address, for example 192.168.1.25.',
        'Invalid IP address', 'OK', 'Warning'
    ) | Out-Null
    exit 1
}

# Read and validate every input before changing any file.
$serversText = [System.IO.File]::ReadAllText($serversPath)
$appText = [System.IO.File]::ReadAllText($appPath)
$viteText = [System.IO.File]::ReadAllText($vitePath)
try {
    $serversObject = $serversText | ConvertFrom-Json
} catch {
    [System.Windows.Forms.MessageBox]::Show(
        "servers.json is not valid JSON:`n$($_.Exception.Message)`n`nNo project files were changed.",
        'Invalid servers.json', 'OK', 'Error'
    ) | Out-Null
    exit 1
}

if ($null -eq $serversObject.servers -or @($serversObject.servers).Count -eq 0) {
    [System.Windows.Forms.MessageBox]::Show(
        'servers.json must contain a non-empty top-level servers array. No files were changed.',
        'Unexpected servers.json format', 'OK', 'Error'
    ) | Out-Null
    exit 1
}

# This project stores host and port separately, e.g. host=10.x.x.x and port=5001.
$updatedServerCount = 0
foreach ($server in $serversObject.servers) {
    $existingHostIp = $null
    $portNumber = 0
    $validHost = [System.Net.IPAddress]::TryParse([string]$server.host, [ref]$existingHostIp) -and
        $existingHostIp.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork
    $validPort = [int]::TryParse([string]$server.port, [ref]$portNumber) -and
        $portNumber -ge 5001 -and $portNumber -le 5003

    if ($validHost -and $validPort) {
        $server.host = $serverIp
        $updatedServerCount++
    }
}

if ($updatedServerCount -eq 0) {
    [System.Windows.Forms.MessageBox]::Show(
        'No servers with a valid IPv4 host and port 5001–5003 were found in servers.json. No files were changed.',
        'Could not identify server hosts', 'OK', 'Error'
    ) | Out-Null
    exit 1
}
$newServersText = ($serversObject | ConvertTo-Json -Depth 100) + [Environment]::NewLine

# Update App.jsx fallback hosts written as host: 'IPv4:5001' or host: "IPv4:5001".
# Quote style and each port are preserved. Use a double-quoted PowerShell string so the
# regex can safely contain both quote characters.
$appPattern = "host:\s*(['""])(?:\d{1,3}\.){3}\d{1,3}:(500[1-3])\1"
$appMatches = [regex]::Matches($appText, $appPattern)
$newAppText = [regex]::Replace($appText, $appPattern, [System.Text.RegularExpressions.MatchEvaluator]{
    param($match)
    return "host: $($match.Groups[1].Value)$serverIp`:$($match.Groups[2].Value)$($match.Groups[1].Value)"
})

# Replace hard-coded IPv4 backend defaults at port 5000 in Vite config. The launcher also
# sets NETWORK_SPEED_TEST_BACKEND when starting Vite, so environment-based configs work too.
$vitePattern = 'http://(?:\d{1,3}\.){3}\d{1,3}:5000'
$viteMatches = [regex]::Matches($viteText, $vitePattern)
$newViteText = [regex]::Replace($viteText, $vitePattern, "http://$serverIp`:5000")

# Make timestamped backups before writing any files.
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backupDir = Join-Path $projectRoot "launcher_backups\$timestamp"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item -LiteralPath $serversPath -Destination (Join-Path $backupDir 'servers.json')
Copy-Item -LiteralPath $appPath -Destination (Join-Path $backupDir 'App.jsx')
Copy-Item -LiteralPath $vitePath -Destination (Join-Path $backupDir 'vite.config.js')

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
try {
    [System.IO.File]::WriteAllText($serversPath, $newServersText, $utf8NoBom)
    [System.IO.File]::WriteAllText($appPath, $newAppText, $utf8NoBom)
    [System.IO.File]::WriteAllText($vitePath, $newViteText, $utf8NoBom)
} catch {
    # Restore all originals if any write fails.
    Copy-Item -LiteralPath (Join-Path $backupDir 'servers.json') -Destination $serversPath -Force
    Copy-Item -LiteralPath (Join-Path $backupDir 'App.jsx') -Destination $appPath -Force
    Copy-Item -LiteralPath (Join-Path $backupDir 'vite.config.js') -Destination $vitePath -Force
    [System.Windows.Forms.MessageBox]::Show(
        "Failed to update project files. The original files have been restored.`n$($_.Exception.Message)",
        'Update failed', 'OK', 'Error'
    ) | Out-Null
    exit 1
}

# Start Vite from the dashboard folder. Bind to localhost only; the browser runs on this PC.
$dashboardDir = Join-Path $projectRoot 'dashboard'
$startCommand = "Set-Location -LiteralPath '$dashboardDir'; `$env:NETWORK_SPEED_TEST_BACKEND='http://$serverIp`:5000'; `$env:BACKEND_URL='http://$serverIp`:5000'; npm run dev -- --host 127.0.0.1"
Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $startCommand) | Out-Null

$dashboardUrl = 'http://localhost:5173'
$ready = $false
for ($i = 0; $i -lt 45; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri $dashboardUrl -TimeoutSec 2 -UseBasicParsing
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
            $ready = $true
            break
        }
    } catch { }
}

if ($ready) {
    Start-Process $dashboardUrl | Out-Null
} else {
    [System.Windows.Forms.MessageBox]::Show(
        "The dashboard did not respond at $dashboardUrl within 45 seconds. The Vite terminal was left open so you can inspect errors.`n`nBackup folder:`n$backupDir",
        'Dashboard startup timed out', 'OK', 'Warning'
    ) | Out-Null
}

$backendStatus = 'Could not reach backend yet. Confirm Santosh has started the backend and both laptops can reach each other.'
try {
    $null = Invoke-RestMethod -Uri "http://$serverIp`:5000/servers" -TimeoutSec 3
    $backendStatus = 'Backend responded at port 5000.'
} catch { }

if ($ready) {
    [System.Windows.Forms.MessageBox]::Show(
        "Dashboard opened.`n`nServer IP: $serverIp`nservers.json hosts updated: $updatedServerCount`nApp.jsx fallback hosts matched: $($appMatches.Count)`nVite backend URLs updated: $($viteMatches.Count)`n`nBackup folder:`n$backupDir`n`n$backendStatus`n`nKeep the Vite terminal open. Santosh must run the backend and measurement servers separately.",
        'Network Speed Test - Launch complete', 'OK', 'Information'
    ) | Out-Null
}
