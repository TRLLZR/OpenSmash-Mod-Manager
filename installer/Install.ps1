param([string]$Repo, [string]$Mod, [switch]$Check, [switch]$Uninstall)
$ErrorActionPreference = 'Stop'
try {
    if (!$Repo) {
        $candidates = @($PSScriptRoot, (Split-Path $PSScriptRoot -Parent))
        $parent = Split-Path $PSScriptRoot -Parent
        $candidates += @(Get-ChildItem -LiteralPath $parent -Directory | ForEach-Object FullName)
        $found = @($candidates | Select-Object -Unique | Where-Object { Test-Path -LiteralPath (Join-Path $_ 'scripts\run.py') -PathType Leaf })
        if ($found.Count -eq 1) {
            $Repo = $found[0] 
        }
        else {
            $Repo = (Read-Host 'OpenSmash-Projektordner (enthaelt Play SSBU.bat)').Trim().Trim('"') 
        }
    }
    $Repo = (Resolve-Path -LiteralPath $Repo).Path
    if (!(Test-Path -LiteralPath (Join-Path $Repo 'scripts\run.py'))) {
        throw 'Falscher Projektordner.' 
    }
    $candidates = @((Join-Path $PSScriptRoot 'runtime\python.exe'))
    $settings = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'OpenSmashMods\settings.json'
    if (Test-Path -LiteralPath $settings) {
        try {
            $preferences = [IO.File]::ReadAllText($settings) | ConvertFrom-Json
            if ($preferences.app -eq 'OpenSmashModsPreferences-v1' -and $preferences.install_dir) {
                $candidates += Join-Path $preferences.install_dir 'runtime\python.exe'
            }
        }
        catch {
        }
    }
    $candidates += Join-Path $Repo 'deps\python\python.exe'
    $py = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (!$py) {
        $py = (Get-Command python.exe -ErrorAction Stop).Source
    }
    $action = 'install'
    if ($Check) {
        $action = 'check' 
    }
    if ($Uninstall) {
        $action = 'uninstall' 
    }
    $arguments = @((Join-Path $PSScriptRoot 'drybowser.py'), $action, '--repo', $Repo)
    if (!$Uninstall) {
        if (!$Mod) {
            $defaultMod = Join-Path $Repo 'mods\custom'
            if (Test-Path -LiteralPath $defaultMod -PathType Container) {
                $Mod = $defaultMod 
            }
            else {
                $Mod = (Read-Host 'Entpackter Full-Replacement-Mod-Ordner oder ZIP-Datei').Trim().Trim('"') 
            }
        }
        $arguments += @('--mod', $Mod)
    }
    if ($Uninstall -and (Test-Path -LiteralPath (Join-Path $Repo 'opensmash_mods\state.json'))) {
        & $py (Join-Path $PSScriptRoot 'modmanager.py') --repo $Repo uninstall
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE 
        }
    }
    & $py @arguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE 
    }
    if (!$Check -and !$Uninstall) {
        & $py (Join-Path $PSScriptRoot 'modmanager.py') --repo $Repo setup --source $Mod
        exit $LASTEXITCODE
    }
    exit 0
}
catch {
    Write-Host "FEHLER: $_" -ForegroundColor Red
    exit 1 
}
