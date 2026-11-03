param([ValidateSet('modded', 'vanilla')][string]$Mode = 'modded')
$ErrorActionPreference = 'Stop'
try {
    $repo = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
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
    $candidates += Join-Path $repo 'deps\python\python.exe'
    $py = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (!$py) {
        $py = (Get-Command python.exe -ErrorAction Stop).Source
    }
    & $py (Join-Path $PSScriptRoot 'drybowser.py') play --repo $repo --mode $Mode
    exit $LASTEXITCODE
}
catch {
    Write-Host "FEHLER: $_" -ForegroundColor Red
    exit 1 
}
