$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
if (Get-Process -Name "TS4_x64" -ErrorAction SilentlyContinue) {
    throw "Close The Sims 4 before installing ShadySimDeals."
}

py -3.12 (Join-Path $root "build_mod.py")
$game = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Electronic Arts\The Sims 4"
$mods = Join-Path $game "Mods\ShadySimDeals"
New-Item -ItemType Directory -Force $mods | Out-Null
Copy-Item -Force (Join-Path $root "dist\ShadySimDeals.ts4script") $mods
Copy-Item -Force (Join-Path $root "dist\ShadySimDeals.package") $mods
Remove-Item -Force (Join-Path $game "localthumbcache.package") -ErrorAction SilentlyContinue
Write-Host "Installed ShadySimDeals to $mods"
Write-Warning "Requires Lot 51 Core Library 1.43 or newer. Restart the game after installation."
