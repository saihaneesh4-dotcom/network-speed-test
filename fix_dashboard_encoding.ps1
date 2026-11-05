
$ErrorActionPreference = "Stop"

$path = (Resolve-Path ".\dashboard\src\App.jsx").Path
$backup = "$path.before-encoding-fix.bak"

Copy-Item $path $backup -Force

# Read source as UTF-8
$content = [System.IO.File]::ReadAllText($path)

# Replace common mojibake sequences using Unicode code points.
$badDash = [string]::Concat(
    [char]0x00E2, [char]0x20AC, [char]0x201D
)
$goodDash = [char]0x2014
$content = $content.Replace($badDash, [string]$goodDash)

$badDot = [string]::Concat([char]0x00C2, [char]0x00B7)
$goodDot = [char]0x00B7
$content = $content.Replace($badDot, [string]$goodDot)

$badDown = [string]::Concat(
    [char]0x00E2, [char]0x2020, [char]0x201C
)
$content = $content.Replace($badDown, [string][char]0x2193)

$badUp = [string]::Concat(
    [char]0x00E2, [char]0x2020, [char]0x2122
)
$content = $content.Replace($badUp, [string][char]0x2191)

$encoding = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($path, $content, $encoding)

Write-Host "Basic encoding repair completed. Backup created." -ForegroundColor Green
