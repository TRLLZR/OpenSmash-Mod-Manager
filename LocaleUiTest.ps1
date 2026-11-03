param([string]$Source, [string]$Repo, [string]$Report, [string]$Theme = 'Light')
$ErrorActionPreference = 'Stop'
$script:localeReport = $Report
$hook = @'
$script:localeDeadline=[datetime]::Now.AddSeconds(15)
$script:localeTimer=[Windows.Threading.DispatcherTimer]::new()
$localeTimer.Interval=[TimeSpan]::FromMilliseconds(100)
$localeTimer.add_Tick({
    try {
        if([datetime]::Now -gt $localeDeadline){throw 'Locale UI timeout'}
        if($script:busy -or !$script:state){return}
        $localeTimer.Stop();$netTimer.Stop()
        $script:gbLoaded=$true
        $window.UpdateLayout()
        if($ui.LibraryNav.Content -ne (L 'Bibliothek')){throw 'Localized library label missing'}
        if($ui.ZipButton.Template -ne $ui.PlayButton.Template -or $ui.MoreButton.Template -ne $ui.VanillaButton.Template){throw 'Button templates diverge'}
        Show-Workspace 'Downloads'
        if($ui.DownloadsWorkspace.Visibility -ne 'Visible'){throw 'Translated navigation changed worker identity'}
        Show-Workspace 'Library'
        $ui.ModsList.SelectedIndex=0
        $selectedId=$ui.ModsList.SelectedItem.Id
        foreach($mode in @('List','Tiles')) {
        Set-LibraryView $mode
        $window.UpdateLayout()
        if($ui.ModsList.SelectedItem.Id -ne $selectedId){throw 'View change lost selection'}
        $visual=$window
        $bitmap=[Windows.Media.Imaging.RenderTargetBitmap]::new([int]$visual.ActualWidth,[int]$visual.ActualHeight,96,96,[Windows.Media.PixelFormats]::Pbgra32)
        $bitmap.Render($visual)
        $encoder=[Windows.Media.Imaging.PngBitmapEncoder]::new()
        $encoder.Frames.Add([Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
        $file=[IO.File]::Create($script:localeReport+'.'+$mode+'.png')
        try{$encoder.Save($file)}finally{$file.Dispose()}
        }
        @{ok=$true;language=[OpenSmash.Localizer]::Language;theme=$VisualTestTheme;rtl=($window.FlowDirection -eq 'RightToLeft');unifiedButtons=$true;navigationInvariant=$true;libraryLabel=[string]$ui.LibraryNav.Content}|ConvertTo-Json|Set-Content -LiteralPath $script:localeReport -Encoding UTF8
        $window.Close()
    }catch{
        @{ok=$false;error=$_.Exception.ToString()}|ConvertTo-Json|Set-Content -LiteralPath $script:localeReport -Encoding UTF8
        $localeTimer.Stop();$window.Close()
    }
})
$window.add_ContentRendered({$localeTimer.Start()})
[void]$window.ShowDialog()
'@
$text = [IO.File]::ReadAllText((Join-Path $Source 'ModManager.ps1'), [Text.Encoding]::UTF8)
$text = $text.Replace('[void]$window.ShowDialog()', $hook).Replace('$PSScriptRoot', ("'" + $Source.Replace("'", "''") + "'"))
& ([ScriptBlock]::Create($text)) -Repo $Repo -ReadOnlySession -SettingsPath ($Report + '.settings.json') -VisualTestTheme $Theme
$result = [IO.File]::ReadAllText($Report, [Text.Encoding]::UTF8) | ConvertFrom-Json
if (!$result.ok) { throw $result.error }
