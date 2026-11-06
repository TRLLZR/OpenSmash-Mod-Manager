param([string]$Output = (Join-Path $PSScriptRoot 'ModManager.exe'))
$ErrorActionPreference = 'Stop'
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (!(Test-Path -LiteralPath $compiler)) {
    $compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe' 
}
$sma = [System.Management.Automation.PowerShell].Assembly.Location
$wpf = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\WPF'
if (!(Test-Path -LiteralPath $wpf)) {
    $wpf = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\WPF' 
}
& $compiler (('/win32icon:') + (Join-Path $PSScriptRoot 'BrandIcon.ico')) /nologo /target:winexe /optimize+ /debug- (('/out:') + $Output) (('/win32manifest:') + (Join-Path $PSScriptRoot 'ModManager.manifest')) (('/reference:') + $sma) /reference:System.Web.Extensions.dll /reference:System.Drawing.dll /reference:System.IO.Compression.dll /reference:System.IO.Compression.FileSystem.dll /reference:System.Windows.Forms.dll /reference:System.Xaml.dll (('/reference:') + (Join-Path $wpf 'PresentationFramework.dll')) (('/reference:') + (Join-Path $wpf 'PresentationCore.dll')) (('/reference:') + (Join-Path $wpf 'WindowsBase.dll')) (('/resource:') + (Join-Path $PSScriptRoot 'locales.json') + ',OpenSmash.Locales.json') (Join-Path $PSScriptRoot 'ModManagerLauncher.cs') (Join-Path $PSScriptRoot 'Localization.cs') (Join-Path $PSScriptRoot 'StartupUpdate.cs')
if ($LASTEXITCODE -ne 0) {
    throw 'Modmanager-Launcher konnte nicht erstellt werden. Dieses Skript mit Windows PowerShell 5.1 ausfuehren.' 
}
