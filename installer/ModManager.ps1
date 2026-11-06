param([string]$GameBananaLink, [string]$Repo, [string]$DropPath, [switch]$SmokeTest, [switch]$SafeVisuals,
    [switch]$BackdropTest, [switch]$ReadOnlySession, [string[]]$DropPaths, [string]$SettingsPath, [ValidateSet('Auto', 'Light', 'Dark', 'HighContrast')][string]$VisualTestTheme = 'Auto')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase, System.Windows.Forms
if (!('OpenSmash.ModRow' -as [type])) {
    [Reflection.Assembly]::LoadFrom((Join-Path $PSScriptRoot 'ModManager.exe')) | Out-Null 
}

$script:settingsFile = if ($SettingsPath) {
    $SettingsPath
}
elseif ($env:OPENSMASH_SETTINGS_PATH) {
    $env:OPENSMASH_SETTINGS_PATH
}
else {
    Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'OpenSmashMods\settings.json'
}
. (Join-Path $PSScriptRoot 'Localization.ps1')
. (Join-Path $PSScriptRoot 'UiSupport.ps1')
. (Join-Path $PSScriptRoot 'Theme.ps1')
$script:preferences = Read-Preferences
$script:glassPreset = 'Solid'
$script:themeChoice = $preferences.theme
$script:highContrast = [System.Windows.SystemParameters]::HighContrast -or $VisualTestTheme -eq 'HighContrast'
$script:dark = ($script:themeChoice -eq 'Dark' -or ($script:themeChoice -eq 'System' -and [OpenSmash.UiNative]::DarkTheme))
function Find-Repo {
    $parent = Split-Path $PSScriptRoot -Parent
    $candidates = @($script:preferences.repo, $PSScriptRoot, $parent, (Split-Path $parent -Parent)) | Where-Object { $_ }
    $candidates += @(Get-ChildItem -LiteralPath $parent -Directory -ErrorAction SilentlyContinue | ForEach-Object FullName)
    $found = @($candidates | Select-Object -Unique | Where-Object { Test-Path -LiteralPath (Join-Path $_ 'scripts\run.py') -PathType Leaf })
    if ($found.Count -eq 1) {
        return $found[0] 
    }
    return Show-ConnectionDialog
}
if (!$Repo) {
    $Repo = Find-Repo 
}
if (!$Repo) {
    return 
}
$Repo = (Resolve-Path -LiteralPath $Repo).Path
if (!(Test-Path -LiteralPath (Join-Path $Repo 'scripts\run.py') -PathType Leaf)) {
    throw (L 'Der gewählte Ordner ist kein OpenSmash-Projekt.') 
}
$script:python = Resolve-Python $Repo
$script:backend = Join-Path $PSScriptRoot 'modmanager.py'
$script:busy = $false
$script:refreshing = $false
$script:preview = $null
$script:source = $null
$script:pendingChanges = @{}
$script:operationToken = $null
$script:pendingLinks = New-Object 'System.Collections.Generic.Queue[string]'
if ($GameBananaLink) {
    $script:pendingLinks.Enqueue($GameBananaLink)
}
$script:batchJob = $null
$script:cancelRequested = $false
$script:state = $null
$script:operation = $null
$script:pendingDrop = @($DropPaths) + @($DropPath) | Where-Object { $_ }
$script:lastFailure = $null
$script:backdrop = $false
$script:started = [datetime]::Now
$script:activity = New-Object 'System.Collections.Generic.List[string]'
$script:highContrast = [System.Windows.SystemParameters]::HighContrast -or $VisualTestTheme -eq 'HighContrast'
$script:dark = ($VisualTestTheme -eq 'Dark' -or ($VisualTestTheme -ne 'Light' -and ($script:themeChoice -eq 'Dark' -or ($script:themeChoice -eq 'System' -and [OpenSmash.UiNative]::DarkTheme))))
$script:tier = [System.Windows.Media.RenderCapability]::Tier -shr 16
$script:constrained = ([OpenSmash.UiNative]::RemoteSession -or [OpenSmash.UiNative]::EnergySaver -or $script:tier -lt 2)
$script:effects = $false
$script:motion = (!$SafeVisuals -and !$script:highContrast -and !$script:constrained -and [System.Windows.SystemParameters]::ClientAreaAnimation)
$script:textScale = [OpenSmash.UiNative]::TextScale
$script:timings = @{Hover =150
    Press                 =90
    Toggle                =180
    Panel                 =220
    Status                =260
    Success               =340
}
$raw = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'ModManager.xaml'))
foreach ($key in $timings.Keys) {
    $duration = if ($script:motion) {
        [TimeSpan]::FromMilliseconds($timings[$key]).ToString('c')
    }
    else {
        '0:0:0'
    }
    $raw = $raw.Replace(('__' + $key.ToUpperInvariant() + '__'), $duration)
}
$raw = $raw.Replace('__LIFT__', $(if ($script:motion) {
            '-1'
        }
        else {
            '0'
        }))
$reader = New-Object System.Xml.XmlNodeReader (ConvertTo-LocalizedXaml $raw)
try {
    $script:window = [System.Windows.Markup.XamlReader]::Load($reader) 
}
finally {
    $reader.Close() 
}
$names = @('ExportListButton', 'ImportListButton', 'ListViewButton', 'TileViewButton', 'CoverButton', 'LibraryNav', 'DiscoverNav', 'DownloadsNav', 'RefreshButton', 'UpdatesButton', 'BulkButton', 'OperationCancel', 'ConflictDisabled', 'ConflictReplace', 'ConflictOverlay', 'ConflictUnderlay', 'LibraryWorkspace', 'DiscoverWorkspace', 'DownloadsWorkspace', 'ExportButton', 'BrandLogo', 'HeaderTools', 'MoreButton', 'MoreMenu', 'OpenLinkButton', 'CopyLinkButton', 'ConflictActions', 'AppearanceButton', 'BatchTab', 'BatchList', 'BatchSummary', 'BatchProgress', 'BatchCancel', 'RootViewport', 'Layout', 'ProjectPath', 'LogsButton', 'RetryButton', 'DropSurface', 'DropHalo', 'DropTitle', 'DropHint', 'PreviewSummary',
    'ZipButton', 'FolderButton', 'InstallButton', 'LibraryPanel', 'ModCount', 'SearchBox', 'ModsList', 'EmptyLibrary', 'RemoveButton', 'UndoButton',
    'DetailsPanel', 'DetailBadge', 'DetailBadgeText', 'DetailTabs', 'DetailContent', 'DetailTitle', 'DetailSubtitle', 'DetailsText', 'ActivityText',
    'ActionSurface', 'StatusSymbol', 'StatusText', 'BusyProgress', 'PlayButton', 'VanillaButton')
$window.Language = [Windows.Markup.XmlLanguage]::GetLanguage([Globalization.CultureInfo]::CurrentUICulture.IetfLanguageTag)
if ([OpenSmash.Localizer]::RightToLeft) {
    $window.FlowDirection = 'RightToLeft'
}
$script:ui = @{}
foreach ($name in $names) {
    $control = $window.FindName($name)
    if (!$control) {
        throw (L 'UI-Komponente fehlt: ') + $name 
    }
    $ui[$name] = $control
}

$logo = New-Object System.Windows.Media.Imaging.BitmapImage
$logo.BeginInit()
$logo.CacheOption = 'OnLoad'
$logo.UriSource = New-Object System.Uri((Join-Path $PSScriptRoot 'BrandLogo.png'), [UriKind]::Absolute)
$logo.EndInit()
$logo.Freeze()
$ui.BrandLogo.Source = $logo
$window.Icon = [System.Windows.Media.Imaging.BitmapFrame]::Create((New-Object System.Uri((Join-Path $PSScriptRoot 'BrandIcon.ico'), [UriKind]::Absolute)), [System.Windows.Media.Imaging.BitmapCreateOptions]::None, [System.Windows.Media.Imaging.BitmapCacheOption]::OnLoad)
# Opaque semantic surfaces; the button material is shared across all views.
$palette = Get-ThemePalette $script:dark
if ($script:highContrast) {
    $palette = @{
        PopupSurface    =[System.Windows.SystemColors]::WindowColor.ToString()
        WindowSurface   =[System.Windows.SystemColors]::WindowColor.ToString()
        ContentSurface  =[System.Windows.SystemColors]::WindowColor.ToString()

        Text            =[System.Windows.SystemColors]::WindowTextColor.ToString()
        SecondaryText   =[System.Windows.SystemColors]::WindowTextColor.ToString()

        Accent          =[System.Windows.SystemColors]::HighlightColor.ToString()
        OnAccent        =[System.Windows.SystemColors]::HighlightTextColor.ToString()

        ControlSurface  =[System.Windows.SystemColors]::WindowColor.ToString()
        ControlBorder   =[System.Windows.SystemColors]::WindowTextColor.ToString()

        PanelBorder     =[System.Windows.SystemColors]::WindowTextColor.ToString()
        SoftSurface     =[System.Windows.SystemColors]::ControlColor.ToString()

        SelectedSurface =[System.Windows.SystemColors]::ControlColor.ToString()
        SelectionBorder =[System.Windows.SystemColors]::WindowTextColor.ToString()

        Success         =[System.Windows.SystemColors]::WindowTextColor.ToString()
        Danger          =[System.Windows.SystemColors]::WindowTextColor.ToString()

        Warning         =[System.Windows.SystemColors]::WindowTextColor.ToString()
        GlassSurface    =[System.Windows.SystemColors]::WindowColor.ToString()

        GlassEdge       =[System.Windows.SystemColors]::WindowTextColor.ToString()
        HoverTint       =[System.Windows.SystemColors]::HighlightColor.ToString()
    }
    foreach ($token in @('BrandSurface', 'PlaySurface')) {
        $palette[$token] = $palette.Accent
    }
    $palette.PlayText = $palette.OnAccent
    $palette.ImportSurface = $palette.ContentSurface
    $palette.RowSurface = $palette.ContentSurface
    foreach ($token in @('SuccessSurface', 'DangerSurface', 'WarningSurface', 'InfoSurface')) {
        $palette[$token] = $palette.SoftSurface
    }
    $palette.Separator = $palette.PanelBorder
    $palette.DropLight = $palette.Accent
}
elseif (!$script:effects -and !$script:dark) {
    # A deliberate opaque design for remote sessions, energy saver and disabled transparency.
    $palette.ContentSurface = '#F7FDFF'
    $palette.ControlSurface = '#FFFFFF'
    $palette.ImportSurface = '#EFFBFF'
    $palette.GlassSurface = '#F1FCFF'
    $palette.SoftSurface = '#ECF9FA'
    $palette.RowSurface = '#FFFFFF'
}
foreach ($token in $palette.Keys) {
    $brush = New-Object System.Windows.Media.SolidColorBrush ([System.Windows.Media.ColorConverter]::ConvertFromString($palette[$token]))
    $brush.Freeze()
    $window.Resources.Add($token, $brush)
}
Set-ButtonMaterials
$window.Resources.Add('ReflectionOpacity', [double]$(if ($script:highContrast -or $SafeVisuals) {
            0
        }
        else {
            1
        }))
$ui.ProjectPath.Text = (L 'Spiel: ') + (Split-Path $Repo -Leaf)
$ui.ProjectPath.ToolTip = $Repo
$area = [System.Windows.SystemParameters]::WorkArea
$window.Width = [math]::Min(1120, [math]::Max(400, $area.Width - 32))
$window.Height = [math]::Min(820, [math]::Max(350, $area.Height - 32))
$window.MinWidth = [math]::Min(840, $window.Width)
$window.MinHeight = [math]::Min(620, $window.Height)
$ui.Layout.LayoutTransform = New-Object System.Windows.Media.ScaleTransform($script:textScale, $script:textScale)
$ui.Layout.ClearValue([System.Windows.FrameworkElement]::HeightProperty)
$ui.Layout.ClearValue([System.Windows.FrameworkElement]::WidthProperty)
function Update-LayoutBounds {
    if ($ui.RootViewport.ActualHeight -gt 0) {
        $ui.Layout.Height = [math]::Max(720, ($ui.RootViewport.ActualHeight - 2) / $script:textScale)
        $ui.Layout.Width = [math]::Max(770, ($ui.RootViewport.ActualWidth - 18) / $script:textScale)
    }
}
$ui.RootViewport.add_SizeChanged({ Update-LayoutBounds })
$script:rows = New-Object 'System.Collections.ObjectModel.ObservableCollection[OpenSmash.ModRow]'
$ui.ModsList.ItemsSource = $script:rows
$script:view = [System.Windows.Data.CollectionViewSource]::GetDefaultView($script:rows)
$script:view.Filter = [Predicate[object]] { param($row) return ([string]$row.Name).IndexOf($ui.SearchBox.Text, [StringComparison]::CurrentCultureIgnoreCase) -ge 0 }

function Add-Activity([string]$text, [string]$kind = (L 'info')) {
    $script:activity.Add(('[{0:HH:mm:ss}] {1}: {2}' -f [datetime]::Now, $kind.ToUpperInvariant(), $text))
    while ($script:activity.Count -gt 200) {
        $script:activity.RemoveAt(0) 
    }
    $ui.ActivityText.Text = $script:activity -join "`r`n"
    $ui.ActivityText.ScrollToEnd()
}
function Set-Status([string]$text, [string]$kind = (L 'info')) {
    $script:statusKind = $kind
    $ui.StatusText.Text = $text
    $token = switch ($kind) {
        'error' {
            'Danger'
        } 'warning' {
            'Warning'
        } 'success' {
            'Success'
        } default {
            'SecondaryText'
        }
    }
    $ui.StatusSymbol.Foreground = $window.Resources[$token]
    $ui.StatusSymbol.Text = switch ($kind) {
        'error' {
            '!'
        } 'warning' {
            '!'
        } 'success' {
            '✓'
        } default {
            '●'
        }
    }
    if ($script:motion) {
        $fade = New-Object System.Windows.Media.Animation.DoubleAnimation(.65, 1, [TimeSpan]::FromMilliseconds($timings.Status))
        $ui.StatusText.BeginAnimation([System.Windows.UIElement]::OpacityProperty, $fade)
    }
}
function Show-Detail([string]$title, [string]$subtitle, [string]$body, [string]$kind = (L 'info')) {
    $script:detailKind = $kind
    $ui.DetailTitle.Text = $title
    $ui.DetailSubtitle.Text = $subtitle
    $ui.DetailsText.Text = $body
    $ui.DetailTabs.SelectedIndex = 0
    $label = switch ($kind) {
        'error' {
            (L 'Fehler')
        } 'warning' {
            (L 'Hinweise')
        } 'success' {
            (L 'Bereit')
        } default {
            (L 'Info')
        }
    }
    $token = switch ($kind) {
        'error' {
            'Danger'
        } 'warning' {
            'Warning'
        } 'success' {
            'Success'
        } default {
            'SecondaryText'
        }
    }
    $ui.DetailBadge.Visibility = if ($kind -in @('error', 'warning')) {
        'Visible'
    }
    else {
        'Collapsed'
    }
    $ui.DetailBadgeText.Text = $label
    $ui.DetailBadgeText.Foreground = $window.Resources[$token]
    $surface = switch ($kind) {
        'error' {
            'DangerSurface'
        } 'warning' {
            'WarningSurface'
        } 'success' {
            'SuccessSurface'
        } default {
            'InfoSurface'
        }
    }
    $ui.DetailBadge.Background = $window.Resources[$surface]
    if ($script:motion) {
        $animation = New-Object System.Windows.Media.Animation.DoubleAnimation(.76, 1, [TimeSpan]::FromMilliseconds($timings.Panel))
        $ui.DetailContent.BeginAnimation([System.Windows.UIElement]::OpacityProperty, $animation)
        $move = New-Object System.Windows.Media.Animation.DoubleAnimation(4, 0, [TimeSpan]::FromMilliseconds($timings.Panel))
        $move.EasingFunction = New-Object System.Windows.Media.Animation.CubicEase
        $ui.DetailContent.RenderTransform.BeginAnimation([System.Windows.Media.TranslateTransform]::YProperty, $move)
    }
}
function Refresh-Empty {
    $ui.EmptyLibrary.Visibility = if ($ui.ModsList.Items.Count -eq 0) {
        'Visible'
    }
    else {
        'Collapsed'
    }
    $ui.EmptyLibrary.Text = if ($script:rows.Count -eq 0) {
        (L "Deine Bibliothek ist noch leer.`nFüge oben deine erste Mod hinzu.")
    }
    else {
        (L "Keine passenden Mods gefunden.`nVersuche einen anderen Suchbegriff.")
    }
}
function Set-Busy([bool]$value) {
    $script:busy = $value
    $ready = (!$value -and $null -ne $script:state)
    foreach ($name in @('ZipButton', 'FolderButton', 'PlayButton', 'VanillaButton')) {
        $ui[$name].IsEnabled = $ready
    }
    $ui.SearchBox.IsEnabled = ($null -ne $script:state)
    $ui.ModsList.IsEnabled = ($null -ne $script:state)
    Set-Resource 'CanChangeMods' ([bool]($ready -and !$ReadOnlySession))
    $ui.BatchCancel.IsEnabled = ($value -and $null -ne $script:batchJob -and !$script:cancelRequested)
    $ui.BatchCancel.Visibility = if ($value -and $script:batchJob) {
        'Visible'
    }
    else {
        'Collapsed'
    }
    if ($ReadOnlySession) {
        $ui.PlayButton.IsEnabled = $false
        $ui.VanillaButton.IsEnabled = $false
    }
    $ui.UpdatesButton.IsEnabled = ($ready -and @($script:state.mods | Where-Object { $_.origin.provider -eq 'GameBanana' }).Count -gt 0)
    $ui.RefreshButton.IsEnabled = $ready
    $ui.BulkButton.IsEnabled = ($ready -and !$ReadOnlySession -and $ui.ModsList.Items.Count -gt 0)
    
    $ui.OperationCancel.IsEnabled = (!$script:cancelRequested)
    $ui.OperationCancel.Visibility = if ($value -and $script:operationToken) {
        'Visible'
    }
    else {
        'Collapsed'
    }
    $ui.ExportButton.IsEnabled = ($ready -and @($script:state.mods).Count -gt 0)
    $ui.ExportListButton.IsEnabled = $ui.ExportButton.IsEnabled
    $ui.ImportListButton.IsEnabled = ($ready -and !$ReadOnlySession)
    $ui.DropSurface.AllowDrop = $ready
    $ui.InstallButton.IsEnabled = ($ready -and !$ReadOnlySession -and $null -ne $script:preview -and $script:preview.ready -gt 0)
    $ui.InstallButton.Visibility = if ($script:preview -and $script:preview.ready -gt 0) {
        'Visible'
    }
    else {
        'Collapsed'
    }
    $ui.PreviewSummary.Visibility = if ($script:preview) {
        'Visible'
    }
    else {
        'Collapsed'
    }
    Update-ImportActions
    if (Get-Command Update-DownloadActions -ErrorAction SilentlyContinue) {
        Update-DownloadActions
    }
    $ui.RemoveButton.IsEnabled = ($ready -and !$ReadOnlySession -and $null -ne $ui.ModsList.SelectedItem)
    $ui.RemoveButton.Visibility = if ($ui.ModsList.SelectedItem) { 'Visible' }else { 'Collapsed' }
    $ui.UndoButton.IsEnabled = ($ready -and !$ReadOnlySession -and [bool]$script:state.can_undo)
    $ui.UndoButton.Visibility = if ($script:state.can_undo) { 'Visible' }else { 'Collapsed' }
    $ui.RetryButton.IsEnabled = (!$value -and $null -ne $script:lastFailure)
    $ui.BusyProgress.Visibility = if ($value -and $script:motion) {
        'Visible'
    }
    else {
        'Hidden'
    }
    $ui.BusyProgress.IsIndeterminate = ($value -and $script:motion)
}
function Quote-Arg([string]$value) {
    return '"' + [regex]::Replace([regex]::Replace($value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"' 
}
function Show-Failure([string]$message) {
    Show-Detail (L 'Vorgang nicht ausgeführt') (L 'Bitte den Hinweis prüfen und anschließend erneut versuchen.') $message 'error'
    Set-Status (L 'Ein Problem ist aufgetreten. Details stehen rechts.') 'error'
    Add-Activity $message 'error'
    $ui.RetryButton.Visibility = if ($null -ne $script:lastFailure) {
        'Visible'
    }
    else {
        'Collapsed'
    }
}
function Begin-Operation([string]$kind, [string[]]$extra = @(), $payload = $null) {
    if ($script:busy) {
        return 
    }
    if ($kind -ne 'change-set' -and $script:pendingChanges.Count) {
        $script:afterSelection = @{Kind =$kind
            Extra                       =$extra
            Payload                     =$payload
        }
        $selectionTimer.Stop()
        $values = $script:pendingChanges
        $script:pendingChanges = @{}
        Begin-Operation 'change-set' @('--stdin') @{values = $values }
        return
    }
    if ($kind -in @('enable', 'remove', 'change-set', 'refresh', 'batch-install', 'list-install', 'play', 'repair-plugins')) {
        $script:operationToken = [guid]::NewGuid().ToString('N')
        $extra += @('--cancel-token', $script:operationToken)
    }
    else {
        $script:operationToken = $null
    }
    $script:cancelRequested = $false
    Set-Busy $true
    $message = switch ($kind) {
        'export' {
            (L 'Alle Mods werden als ZIP exportiert…')
        } 'bootstrap' {
            (L 'Deine Bibliothek wird geladen…')
        } 'list' {
            (L 'Deine Bibliothek wird geladen…')
        } 'setup' {
            (L 'Deine Bibliothek wird geladen…')
        } 'download-preview' {
            (L 'Downloads werden für die Importliste geprüft…')
        } 'batch-preview' {
            (L 'Mod-Auswahl wird geprüft…')
        } 'batch-install' {
            (L 'Stapel wird vorbereitet und installiert…')
        } 'inspect' {
            (L 'Die Mod wird geprüft…')
        }
        'install' {
            (L 'Mod wird installiert. Die erste Einrichtung kann einige Minuten dauern…')
        }
        'enable' {
            (L 'Aktivierung wird angewendet…')
        } 'change-set' {
            (L 'Auswahl wird gemeinsam angewendet…')
        } 'refresh' {
            (L 'Alle Dateien werden vollständig geprüft…')
        } 'batch-configure' {
            (L 'Importentscheidung wird übernommen…')
        } 'remove' {
            (L 'Mod wird aus dem Profil in die Rückgängig-Ablage verschoben…')
        }
        'undo' {
            (L 'Vorherige Auswahl wird wiederhergestellt…')
        } 'play' {
            (L 'OpenSmash wird gestartet…')
        } default {
            (L 'Vorgang läuft…')
        }
    }
    Set-Status $message
    Add-Activity $message
    $script:lastFailure = $null
    $ui.RetryButton.Visibility = 'Collapsed'
    $info = New-Object System.Diagnostics.ProcessStartInfo
    $info.FileName = $script:python
    $info.WorkingDirectory = $Repo
    $arguments = @($script:backend, '--repo', $Repo, $kind) + $extra
    $info.Arguments = ($arguments | ForEach-Object { Quote-Arg $_ }) -join ' '
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $info.StandardErrorEncoding = $info.StandardOutputEncoding
    $info.EnvironmentVariables['PYTHONUTF8'] = '1'
    try {
        $payloadText = if ($null -ne $payload) {
            $payload | ConvertTo-Json -Depth 5 -Compress
        }
        else {
            $null
        }
        $job = [OpenSmash.BackendJob]::Start($info, $payloadText)
        $script:operation = @{Kind =$kind
            Extra                  =$extra
            Payload                =$payload
            Job                    =$job
            Process                =$job.Process
            At                     =[datetime]::Now
            Message                =$message
            Result                 =$null
            LastSecond             =-1
            Noise                  =''
        }
        $timer.Start()
    }
    catch {
        $script:lastFailure = @{Kind =$kind
            Extra                    =$extra
            Payload                  =$payload
        }
        Set-Busy $false
        Show-Failure $_.Exception.Message 
    }

}
function Show-State($newState, [string]$preferId = '') {
    if (!$preferId -and $null -ne $ui.ModsList.SelectedItem) {
        $preferId = $ui.ModsList.SelectedItem.Id
    }
    $script:state = $newState
    $script:refreshing = $true
    try {
        $existing = @{}
        foreach ($row in $script:rows) {
            $existing[$row.Id] = $row
        }
        $wanted = @{}
        foreach ($mod in @($newState.mods)) {
            $id = [string]$mod.id
            $wanted[$id] = $true
            $isNew = !$existing.ContainsKey($id)
            if (!$isNew) {
                $row = $existing[$id]
            }
            else {
                $row = New-Object OpenSmash.ModRow
                $row.Id = $id
            }
            $row.Update([string]$mod.name, [bool]$mod.enabled, [int]$mod.files, [string[]]@($mod.warnings))
            $row.SetPreview([string]$mod.preview)
            if ($isNew) {
                $script:rows.Add($row)
            }
        }
        $removed = @($script:rows | Where-Object { !$wanted.ContainsKey($_.Id) })
        foreach ($row in $removed) {
            $script:rows.Remove($row) | Out-Null
        }
        $active = @($script:rows | Where-Object Active).Count
        $ui.ModCount.Text = ((L '{0} Mods · {1} aktiv') -f $script:rows.Count, $active)
        foreach ($row in $script:rows) {
            if ($row.Id -eq $preferId) {
                $ui.ModsList.SelectedItem = $row
                break
            }
        }
    }
    finally {
        $script:refreshing = $false
        Refresh-Empty
    }
    Start-LibraryImages
}
function Accept-Drop([string]$path) {
    Accept-Drops @($path)
}
function Open-Zip {
    if (!$ui.ZipButton.IsEnabled) {
        return
    }
    $dialog = New-Object Microsoft.Win32.OpenFileDialog
    $dialog.Title = (L 'Mod-Archive auswählen')
    $dialog.Filter = 'Mod-Archive (*.zip;*.rar;*.7z)|*.zip;*.rar;*.7z|ZIP (*.zip)|*.zip|RAR (*.rar)|*.rar|7z (*.7z)|*.7z'
    $dialog.Multiselect = $true
    try {
        if ($dialog.ShowDialog($window)) {
            Accept-Drops $dialog.FileNames
        }
    }
    catch {
        Show-Failure $_.Exception.Message
    }
}
function Open-Folder {
    if (!$ui.FolderButton.IsEnabled) {
        return
    }
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = (L 'Mod-Ordner mit fighter, ui, effect oder sound auswählen')
    try {
        if ($dialog.ShowDialog() -eq 'OK') {
            Accept-Drop $dialog.SelectedPath
        }
    }
    catch {
        Show-Failure $_.Exception.Message
    }
    finally {
        $dialog.Dispose()
    }
}
function Open-Logs {
    try {
        $build = Join-Path $Repo 'build'
        $location = Join-Path $Repo 'build_location.txt'
        if (Test-Path -LiteralPath $location) {
            $line = [Environment]::ExpandEnvironmentVariables(([IO.File]::ReadAllLines($location)[0]).Trim().Trim('"'))
            if ($line) {
                $build = if ([IO.Path]::IsPathRooted($line)) {
                    $line
                }
                else {
                    Join-Path $Repo $line
                }
            }
        }
        $managerLogs = Join-Path $Repo 'opensmash_mods\logs'
        $path = if (Test-Path -LiteralPath $managerLogs) {
            $managerLogs
        }
        else {
            Join-Path $build 'logs'
        }
        if (Test-Path -LiteralPath $path) {
            Start-Process -FilePath explorer.exe -ArgumentList (Quote-Arg $path)
        }
        else {
            Show-Detail (L 'Noch keine Spielprotokolle') (L 'Nach dem ersten Spielstart findest du hier die Protokolle.') $path
        }
    }
    catch {
        Show-Failure $_.Exception.Message
    }
}
function Install-Preview {
    if ($ui.InstallButton.IsEnabled -and $null -ne $script:preview) {
        $script:cancelRequested = $false
        if ($script:preview.kind -eq 'mod-list') {
            Begin-Operation 'list-install' @('--source', $script:preview.path, '--token', $script:preview.token); return
        }
        Begin-Operation 'batch-install' @('--job', $script:preview.job_id, '--token', $script:preview.token)
    }
}
function Remove-Selected {
    if ($ui.RemoveButton.IsEnabled) {
        Begin-Operation 'remove' @('--id', $ui.ModsList.SelectedItem.Id)
    }
}
function Undo-Change {
    if ($ui.UndoButton.IsEnabled) {
        Begin-Operation 'undo'
    }
}
function Play-Mods {
    if ($ui.PlayButton.IsEnabled) {
        Begin-Operation 'play'
    }
}
function Play-Vanilla {
    if ($ui.VanillaButton.IsEnabled) {
        Begin-Operation 'play' @('--vanilla')
    }
}

$ui.ExportButton.add_Click({ Export-Library })
$ui.ZipButton.add_Click({ Open-Zip })
$ui.FolderButton.add_Click({ Open-Folder })
$ui.InstallButton.add_Click({ Install-Preview })
$ui.RemoveButton.add_Click({ Remove-Selected })
$ui.UndoButton.add_Click({ Undo-Change })
$ui.PlayButton.add_Click({ Play-Mods })
$ui.VanillaButton.add_Click({ Play-Vanilla })
$ui.LogsButton.add_Click({ Open-Logs })
$ui.BatchCancel.add_Click({ Cancel-Batch })
$ui.MoreButton.add_Click({ Show-HeaderMenu $ui.MoreButton $ui.MoreMenu })
$ui.MoreMenu.add_Opened({ $ui.CoverButton.Visibility = if ($script:workspace -eq 'Library' -and $ui.ModsList.SelectedItem) { 'Visible' }else { 'Collapsed' }
        $ui.BulkButton.Visibility = if ($script:workspace -eq 'Library') {
            'Visible'
        }
        else {
            'Collapsed'
        }
        $visible = @($ui.ModsList.Items)
        $ui.BulkButton.Header = if (@($visible | Where-Object { !$_.Active }).Count) {
            (L 'Sichtbare Mods aktivieren')
        }
        else {
            (L 'Sichtbare Mods pausieren')
        } })
$ui.RetryButton.add_Click({ if (!$script:busy -and $null -ne $script:lastFailure) {
            $retry = $script:lastFailure
            Begin-Operation $retry.Kind $retry.Extra $retry.Payload
        } })
$ui.SearchBox.add_TextChanged({ if (!$script:refreshing) {
            $script:view.Refresh()
            Refresh-Empty
        } })
$ui.DetailTabs.add_SelectionChanged({
        if ($_.OriginalSource -ne $ui.DetailTabs -or !$script:motion) {
            return
        }
        $target = if ($ui.DetailTabs.SelectedIndex -eq 0) {
            $ui.DetailContent
        }
        else {
            $ui.ActivityText
        }
        $fade = New-Object System.Windows.Media.Animation.DoubleAnimation(.72, 1, [TimeSpan]::FromMilliseconds($timings.Panel))
        $target.BeginAnimation([System.Windows.UIElement]::OpacityProperty, $fade)
    })
$ui.ModsList.AddHandler([System.Windows.Controls.Primitives.ButtonBase]::ClickEvent, [System.Windows.RoutedEventHandler] {
        param($sender, $event)
        $check = $event.OriginalSource
        if ($check -is [System.Windows.Controls.CheckBox] -and !$script:refreshing -and !$script:busy -and !$ReadOnlySession) {
            $id = [string]$check.Tag
            if ($id) {
                $script:pendingChanges[$id] = [bool]$check.IsChecked
                foreach ($row in $script:rows) {
                    if ($row.Id -eq $id) {
                        $row.Active = [bool]$check.IsChecked
                        break
                    }
                }
                $selectionTimer.Stop()
                $selectionTimer.Start()
            }
            $event.Handled = $true
        }
    })
$ui.ModsList.add_SelectionChanged({
        if ($script:refreshing -or $script:busy) {
            return
        }
        $row = $ui.ModsList.SelectedItem
        $ui.RemoveButton.IsEnabled = (!$ReadOnlySession -and $null -ne $row)
        $ui.RemoveButton.Visibility = if ($row) { 'Visible' }else { 'Collapsed' }
        if ($null -ne $row) {
            $record = @($script:state.mods | Where-Object { $_.id -eq $row.Id })[0]
            $origin = $record.origin
            $sourceLines = @((L 'Kompatibilität: ') + $record.compatibility, (L 'Installationspfad: ') + $record.location)
            if ($origin.provider) {
                $sourceLines += @((L 'Quelle: ') + $origin.source_url, (L 'Autor: ') + $origin.author, (L 'Version: ') + $origin.version, 'GameBanana: ' + $origin.model + ' ' + $origin.submission_id + (L ' · Datei ') + $origin.file_id)
            }
            Show-Detail $row.Name ($row.FileCaption + ' · ' + $row.StatusText) ((@($row.Warnings)) -join "`r`n")
            $ui.DetailsText.ToolTip = $sourceLines -join "`r`n"
        }
    })
function Reset-Drop {
    $ui.DropTitle.Text = (L 'Mods hinzufügen')
    $ui.DropHint.Text = (L 'ZIP/RAR/7z oder Ordner hier ablegen')
    $ui.DropSurface.BorderThickness = New-Object System.Windows.Thickness(1)
    $ui.DropSurface.BorderBrush = $window.Resources['GlassEdge']
    Set-DropLight 0
}
function Set-DropLight([double]$opacity) {
    if ($script:motion) {
        $fade = New-Object System.Windows.Media.Animation.DoubleAnimation($opacity, [TimeSpan]::FromMilliseconds($timings.Hover))
        $ui.DropHalo.BeginAnimation([System.Windows.UIElement]::OpacityProperty, $fade)
    }
    else {
        $ui.DropHalo.Opacity = $opacity
    }
}
$ui.DropSurface.add_PreviewDragOver({
        if (!$script:busy -and $null -ne $script:state -and $_.Data.GetDataPresent([System.Windows.DataFormats]::FileDrop)) {
            $_.Effects = [System.Windows.DragDropEffects]::Copy
            $ui.DropTitle.Text = (L 'Hier ablegen')
            $ui.DropHint.Text = (L 'Die Mod wird zunächst geprüft.')
            $ui.DropSurface.BorderThickness = New-Object System.Windows.Thickness(2)
            $ui.DropSurface.BorderBrush = $window.Resources['Accent']
            Set-DropLight 1
        }
        else {
            $_.Effects = [System.Windows.DragDropEffects]::None
        }
        $_.Handled = $true
    })
$ui.DropSurface.add_DragLeave({ Reset-Drop })
$ui.DropSurface.add_Drop({
        Reset-Drop
        if (!$_.Data.GetDataPresent([System.Windows.DataFormats]::FileDrop)) {
            return
        }
        $paths = @($_.Data.GetData([System.Windows.DataFormats]::FileDrop))
        Accept-Drops $paths
        $_.Handled = $true
    })
$window.add_PreviewKeyDown({
        $key = $_.Key
        $ctrl = ([System.Windows.Input.Keyboard]::Modifiers -band [System.Windows.Input.ModifierKeys]::Control) -ne 0
        $shift = ([System.Windows.Input.Keyboard]::Modifiers -band [System.Windows.Input.ModifierKeys]::Shift) -ne 0
        if ($ctrl -and $key -eq 'O') {
            if ($shift) {
                Open-Folder
            }
            else {
                Open-Zip
            }
            $_.Handled = $true
        }
        elseif ($ctrl -and $key -eq 'I') {
            Install-Preview
            $_.Handled = $true
        }
        elseif ($ctrl -and $key -eq 'R') {
            if (!$script:busy) {
                Begin-Operation 'refresh'
            }
            $_.Handled = $true
        }
        elseif ($ctrl -and $key -eq 'F') {
            if ($script:workspace -eq 'Discover') {
                $ui.GBSearch.Focus() | Out-Null
                $ui.GBSearch.SelectAll()
            }
            else {
                Show-Workspace 'Library'
                $ui.SearchBox.Focus() | Out-Null
                $ui.SearchBox.SelectAll()
            }
            $_.Handled = $true
        }
        elseif ($ctrl -and $key -eq 'L') {
            Open-Logs
            $_.Handled = $true
        }
        elseif ($ctrl -and $key -eq 'Z' -and !([System.Windows.Input.Keyboard]::FocusedElement -is [System.Windows.Controls.Primitives.TextBoxBase])) {
            Undo-Change
            $_.Handled = $true
        }
        elseif ($key -eq 'F5') {
            Play-Mods
            $_.Handled = $true
        }
        elseif ($key -eq 'F6') {
            Play-Vanilla
            $_.Handled = $true
        }
        elseif ($key -eq 'Escape' -and $ui.SearchBox.IsKeyboardFocusWithin) {
            $ui.SearchBox.Clear()
            $_.Handled = $true
        }
    })
$timer = New-Object System.Windows.Threading.DispatcherTimer
. (Join-Path $PSScriptRoot 'Discover.ps1')
. (Join-Path $PSScriptRoot 'LibraryView.ps1')
. (Join-Path $PSScriptRoot 'ModLists.ps1')
$timer.Interval = [TimeSpan]::FromMilliseconds(75)
$timer.add_Tick({
        $op = $script:operation
        if ($null -eq $op) {
            $timer.Stop()
            return
        }
        $seconds = [int]([datetime]::Now - $op.At).TotalSeconds
        foreach ($line in $op.Job.Drain()) {
            try {
                $message = $line | ConvertFrom-Json
                Localize-Result $message
                if ($message.event -eq 'progress') {
                    if ($op.Kind -in @('batch-preview', 'download-preview', 'batch-install')) {
                        Set-BatchProgress $message
                    }
                    Set-OperationProgress $message $op
                }
                else {
                    $op.Result = $message
                }
            }
            catch {
                $op.Noise += ($line + "`n")
                if ($op.Noise.Length -gt 8000) {
                    $op.Noise = $op.Noise.Substring($op.Noise.Length - 8000)
                }
            }
        }
        if (!$op.Process.HasExited -or !$op.Job.OutputComplete -or !$op.Job.Error.IsCompleted -or $op.Job.PendingLines) {
            if ($seconds -ge 3 -and $op.LastSecond -ne $seconds) {
                $op.LastSecond = $seconds
                if (!$script:cancelRequested) {
                    Set-Status ($op.Message + '  ' + $seconds + ' s')
                }
            }
            return
        }
        $script:operation = $null
        $timer.Stop()
        $succeeded = $false
        try {
            $data = $op.Result
            if ($null -eq $data) {
                throw ((L 'Keine verwertbare Antwort vom Modmanager. ') + $op.Job.Error.Result + ' ' + $op.Noise)
            }
            if (!$data.ok) {
                throw [string]$data.error
            }
            if ($op.Process.ExitCode -ne 0) {
                throw ((L 'Modmanager wurde mit Fehlercode ') + $op.Process.ExitCode + (L ' beendet. ') + $op.Job.Error.Result)
            }
            $result = $data.result
            $succeeded = (!$result.cancelled)
            if ($result.cancelled -and !$result.state -and !$result.items) {
                Show-State $script:state
                Set-Status ([string]$result.message) 'warning'
            }
            elseif ($op.Kind -eq 'refresh') {
                Show-State $result
                $errors = @($result.validation_errors.PSObject.Properties | ForEach-Object { $_.Value })
                Show-Detail (L 'Vollständige Prüfung') ('Dauer: ' + [math]::Round($result.refresh_seconds, 2) + ' s') $(if ($errors.Count) {
                        $errors -join "`r`n"
                    }
                    else {
                        (L 'Alle Bibliotheks- und Profildateien stimmen mit ihren Prüfsummen überein.')
                    }) $(if ($errors.Count) {
                        'warning'
                    }
                    else {
                        'success'
                    })
                Set-Status (L 'Vollständige Prüfung abgeschlossen.')
            }
            elseif ($op.Kind -eq 'export-list') {
                Show-Detail (L 'Modliste gespeichert') ([string]$result.path) (((L '{0} Mods · {1} ohne Downloadquelle. Die Liste enthält keine Moddateien.') -f $result.mods, $result.manual)) 'success'
                Set-Status (L 'Modliste gespeichert.') 'success'
            }
            elseif ($op.Kind -eq 'list-preview') {
                $script:preview = $result; $script:batchJob = $null
                Set-BatchRows $result.items
                $ui.BatchSummary.Text = ((L '{0} fehlen · {1} vorhanden · {2} ohne Downloadquelle') -f $result.ready, $result.existing, $result.manual)
                $ui.InstallButton.Content = L 'Fehlende Mods installieren'
                Set-Status (L 'Liste prüfen. Bestätigung lädt fehlende Mods herunter und installiert sie; Konflikte bleiben pausiert.')
            }
            elseif ($op.Kind -eq 'export') {
                Set-Status ([string]$result.message) 'success'
                Show-Detail (L 'Export abgeschlossen') ($result.mods.ToString() + (L ' Mods in einer ZIP')) ([string]$result.path) 'success'
                Add-Activity ((L 'Export: ') + $result.path) 'success'
            }
            elseif ($op.Kind -in @('batch-preview', 'download-preview', 'batch-configure')) {
                $script:preview = $result
                $script:batchJob = $result.job_id
                Set-BatchRows $result.items
                $ui.BatchSummary.Text = ((L '{0} erkannt · {1} bereit · {2} übersprungen/ungültig') -f $result.total, $result.ready, ($result.total - $result.ready))
                $ui.PreviewSummary.Text = $result.ready.ToString() + (L ' Mods bereit')
                $ui.InstallButton.Content = if ($result.ready -eq 1) {
                    (L '1 Mod installieren')
                }
                else {
                    $result.ready.ToString() + (L ' Mods installieren')
                }
                Set-Status $(if ($result.cancelled) {
                        (L 'Prüfung abgebrochen.')
                    }
                    else {
                        (L 'Vorschau fertig. Konflikte und vorhandene Mods werden übersprungen.')
                    }) $(if ($result.cancelled) {
                        'warning'
                    }
                    else {
                        'success'
                    })
                Add-Activity $ui.BatchSummary.Text
            }
            elseif ($op.Kind -in @('batch-install', 'list-install')) {
                Show-State $result.state
                Set-BatchRows $result.items
                $ui.BatchSummary.Text = ((L '{0} installiert · {1} fehlgeschlagen · {2} übersprungen') -f $result.installed, $result.failed, $result.skipped)
                $ui.BatchProgress.Value = $ui.BatchProgress.Maximum
                $script:preview = $null
                $script:cancelRequested = $false
                Set-Status $ui.BatchSummary.Text $(if ($result.failed -or $result.cancelled) {
                        'warning'
                    }
                    else {
                        'success'
                    })
                Add-Activity $ui.BatchSummary.Text
                if ($script:motion -and $result.installed -gt 0) {
                    $flash = New-Object System.Windows.Media.Animation.DoubleAnimation(1, 0, [TimeSpan]::FromMilliseconds($timings.Success))
                    $ui.DropHalo.BeginAnimation([System.Windows.UIElement]::OpacityProperty, $flash)
                }
            }
            elseif ($op.Kind -eq 'inspect') {
                $script:preview = $result
                $body = @($result.warnings)
                if (@($result.ignored).Count -gt 0) {
                    $body += @('', (L 'Begleitdateien werden ausgelassen:'))
                    $body += @($result.ignored | Select-Object -First 80 | ForEach-Object { $_.path + ' – ' + $_.reason })
                }
                if ($body.Count -eq 0) {
                    $body = @((L 'Die Dateien sind für die Installation vorbereitet.'))
                }
                $size = [math]::Round($result.bytes / 1MB, 1)
                $ui.PreviewSummary.Text = $result.count.ToString() + (L ' Dateien · ') + $size + ' MB'
                $previewKind = if (@($result.warnings).Count -gt 0) {
                    'warning'
                }
                else {
                    'success'
                }
                Show-Detail (L 'Bereit zur Installation') ([string]$result.name) (($body + @('', (L 'Mit „Installieren und aktivieren“ zur Bibliothek hinzufügen.'))) -join "`r`n") $previewKind
                Set-Status (L 'Prüfung abgeschlossen. Du kannst die Mod jetzt installieren.') 'success'
                Add-Activity ((L 'Geprüft: ') + $result.name + ' · ' + $result.count + (L ' Dateien')) 'success'
            }
            elseif ($op.Kind -eq 'play') {
                Set-Status (L 'OpenSmash wurde gestartet.') 'success'
                Show-Detail (L 'Viel Spaß beim Spielen.') (L 'Änderungen an der Mod-Auswahl gelten nach einem Neustart.') ('Spielprotokoll:' + "`r`n" + $result.log) 'success'
                Add-Activity ((L 'Spiel gestartet. Protokoll: ') + $result.log) 'success'
            }
            else {
                if ($op.Kind -eq 'install') {
                    $name = $script:preview.name
                    $key = $script:preview.id
                    Show-State $result.state $key
                    $script:preview = $null
                    $ui.PreviewSummary.Text = ''
                    Show-Detail (L 'Mod ist in deiner Bibliothek') $name ([string]$result.message) 'success'
                    if ($script:motion) {
                        $flash = New-Object System.Windows.Media.Animation.DoubleAnimation(1, 0, [TimeSpan]::FromMilliseconds($timings.Success))
                        $ui.DropHalo.BeginAnimation([System.Windows.UIElement]::OpacityProperty, $flash)
                    }
                    Set-Status ([string]$result.message) 'success'
                }
                else {
                    Show-State $result
                    if ($op.Kind -in @('list', 'bootstrap', 'setup')) {
                        Show-Detail (L 'Mod auswählen') '' ''
                    }
                    else {
                        Show-Detail (L 'Auswahl gespeichert') (L 'Wirksam beim nächsten Spielstart.') (L 'Mit Rückgängig kannst du die vorherige Auswahl wiederherstellen.') 'success'
                    }
                    Set-Status (L 'Bereit.') 'success'
                }
                Add-Activity ((L 'Abgeschlossen: ') + $op.Kind) 'success'
            }
        }
        catch {
            $script:lastFailure = @{Kind =$op.Kind
                Extra                    =$op.Extra
                Payload                  =$op.Payload
            }
            if ($op.Kind -eq 'inspect') {
                $script:preview = $null
                $ui.PreviewSummary.Text = (L 'Prüfung nicht abgeschlossen')
            }
            $message = $_.Exception.Message
            if ($null -ne $script:state) {
                Show-State $script:state
            }
            Show-Failure $message
        }
        finally {
            $op.Job.Dispose()
            if ($script:operationToken) {
                $cancelFile = Join-Path $Repo ('opensmash_mods\incoming\operation-' + $script:operationToken + '.cancel')
                if (Test-Path -LiteralPath $cancelFile) {
                    Remove-Item -LiteralPath $cancelFile -Force
                }
                $script:operationToken = $null
            }
            Set-Busy $false
            if ($op.Kind -eq 'setup') {
                $ui.ZipButton.Focus() | Out-Null
            }
        }
        if ($op.Kind -eq 'change-set' -and $script:afterSelection) {
            $next = $script:afterSelection
            $script:afterSelection = $null
            if ($succeeded) {
                Begin-Operation $next.Kind $next.Extra $next.Payload
            }
        }
        if ($script:pendingDrop -and $null -ne $script:state -and !$script:busy) {
            $pending = @($script:pendingDrop)
            $script:pendingDrop = $null
            Accept-Drops $pending
        }
        elseif ($SmokeTest -and !$DropPath -and !$DropPaths.Count -and !$script:busy) {
            $window.UpdateLayout()
            $report = @{language  =[OpenSmash.Localizer]::Language
                unifiedButtons    =($ui.ZipButton.Template -eq $ui.PlayButton.Template -and $ui.MoreButton.Template -eq $ui.VanillaButton.Template)
                version           ='3.7.1'
                ready             =($null -ne $script:state)
                theme             =$VisualTestTheme
                dark              =$script:dark
                highContrast      =$script:highContrast
                motion            =$script:motion
                effects           =$script:effects
                backdrop          =$script:backdrop
                backdropStatus    =[OpenSmash.UiNative]::BackdropStatus
                renderTier        =$script:tier
                textScale         =$script:textScale
                font              =$window.FontFamily.Source
                logoLoaded        =($null -ne $ui.BrandLogo.Source)
                title             =$window.Title
                plainHeader       =($ui.ProjectPath.Background.Color.A -eq 0)
                opaque            =($window.Background.Color.A -eq 255 -and !$script:backdrop)
                logoReplacesTitle =($null -eq $window.FindName('AppTitle'))
                noTopmostControl  =($null -eq $window.FindName('OnTop'))
                themeChoices      =$glassMenu.Items.Count
                menuActions       =($ui.ExportButton -is [System.Windows.Controls.MenuItem] -and $ui.RefreshButton -is [System.Windows.Controls.MenuItem])
                controls          =$names.Count
                mods              =$script:rows.Count
                width             =$window.ActualWidth
                height            =$window.ActualHeight
                remote            =[OpenSmash.UiNative]::RemoteSession
                energySaver       =[OpenSmash.UiNative]::EnergySaver
            }
            if ($null -eq $script:state) {
                $report.error = $ui.DetailsText.Text
            }
            $reportPath = Join-Path $Repo 'opensmash_mods\logs'
            if (Test-Path -LiteralPath $reportPath) {
                # Application-owned integration checks; never toggle installed mods or start the game.
                $checks = New-Object 'System.Collections.Generic.List[object]'
                $filterClock = [Diagnostics.Stopwatch]::StartNew()
                $ui.SearchBox.Text = '__opensmash_no_match_9b2c__'
                $window.UpdateLayout()
                $filterClock.Stop()
                $report.filterMilliseconds = $filterClock.Elapsed.TotalMilliseconds
                $report.libraryWorkerMilliseconds = ([datetime]::Now - $op.At).TotalMilliseconds
                $report.filterOk = ($ui.ModsList.Items.Count -eq 0 -and $ui.EmptyLibrary.Visibility -eq 'Visible')
                $textBounds = $ui.SearchBox.GetRectFromCharacterIndex(0)
                $report.searchTextRectOk = (!$textBounds.IsEmpty -and $textBounds.Top -ge 0 -and $textBounds.Bottom -le $ui.SearchBox.ActualHeight)
                $ui.SearchBox.Clear()
                $originalScale = $script:textScale
                $originalWidth = $window.Width
                $originalHeight = $window.Height
                $script:gbLoaded = $true
                $netTimer.Stop()
                $report.comboTemplatesOk = ($null -ne $ui.GBCategory.ItemTemplate -and $null -ne $ui.GBSort.ItemTemplate -and $null -ne $ui.GBFiles.ItemTemplate)
                $report.noImplicitVariant = ($ui.GBFiles.SelectedIndex -eq -1)
                $originalView = $script:libraryView
                foreach ($surface in @('Library', 'LibraryTiles', 'Discover', 'Downloads')) {
                    if ($surface -eq 'LibraryTiles') { Show-Workspace 'Library'; Set-LibraryView 'Tiles' }else { Show-Workspace $surface; if ($surface -eq 'Library') { Set-LibraryView 'List' } }
                    foreach ($size in @(@(1120, 820, 1), @(840, 620, 1), @(1120, 820, 1.25), @(1120, 820, 1.5), @(1120, 820, 2))) {
                        $window.Width = $size[0]
                        $window.Height = $size[1]
                        $script:textScale = $size[2]
                        $ui.Layout.LayoutTransform = New-Object System.Windows.Media.ScaleTransform($script:textScale, $script:textScale)
                        $window.UpdateLayout()
                        Update-LayoutBounds
                        $window.UpdateLayout()
                        $ok = $true
                        $surfaceControls = switch ($surface) {
                            'Library' {
                                @('ZipButton', 'FolderButton', 'InstallButton', 'LibraryPanel', 'DetailsPanel', 'ListViewButton', 'TileViewButton', 'ActionSurface')
                            } 'LibraryTiles' {
                                @('ZipButton', 'FolderButton', 'InstallButton', 'LibraryPanel', 'DetailsPanel', 'ListViewButton', 'TileViewButton', 'ActionSurface')
                            } 'Discover' {
                                @('GBSearch', 'GBList', 'GBFiles', 'GBQueue', 'ActionSurface')
                            } 'Downloads' {
                                @('DQList', 'DQInspect', 'DQClear', 'DQSave', 'ActionSurface')
                            }
                        }
                        foreach ($name in $surfaceControls) {
                            $control = $ui[$name]
                            $rect = New-Object System.Windows.Rect(0, 0, $control.ActualWidth, $control.ActualHeight)
                            $bounds = $control.TransformToAncestor($ui.Layout).TransformBounds($rect)
                            if ($bounds.Left -lt -1 -or $bounds.Top -lt -1 -or $bounds.Right -gt $ui.Layout.ActualWidth + 1 -or $bounds.Bottom -gt $ui.Layout.ActualHeight + 1) {
                                $ok = $false
                            }
                        }
                        $checks.Add(@{surface =$surface
                                width         =$size[0]
                                height        =$size[1]
                                scale         =$size[2]
                                layoutOk      =$ok
                                extentWidth   =$ui.RootViewport.ExtentWidth
                                extentHeight  =$ui.RootViewport.ExtentHeight
                            })
                    }
                }
                Show-Workspace 'Library'
                Set-LibraryView $originalView
                $script:textScale = $originalScale
                $window.Width = $originalWidth
                $window.Height = $originalHeight
                $ui.Layout.LayoutTransform = New-Object System.Windows.Media.ScaleTransform($originalScale, $originalScale)
                $window.UpdateLayout()
                Update-LayoutBounds
                $window.UpdateLayout()
                $report.layouts = @($checks.ToArray())
                $report.listForegroundOk = ($ui.ModsList.Foreground.ToString() -eq $window.Resources['Text'].ToString())
                $bitmap = New-Object System.Windows.Media.Imaging.RenderTargetBitmap([int]$window.ActualWidth, [int]$window.ActualHeight, 96, 96, [System.Windows.Media.PixelFormats]::Pbgra32)
                $bitmap.Render($window)
                $encoder = New-Object System.Windows.Media.Imaging.PngBitmapEncoder
                $encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
                $stream = [IO.File]::Create((Join-Path $reportPath ('ui-preview-' + $VisualTestTheme + '.png')))
                try {
                    $encoder.Save($stream)
                }
                finally {
                    $stream.Dispose()
                }
                $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $reportPath ('ui-smoke-' + $VisualTestTheme + '.json')) -Encoding UTF8
            }
            $window.Close()
        }
    })
if ($SmokeTest -and ($DropPath -or $DropPaths.Count)) {
    # A real native OLE drag source for diagnostics, absent during ordinary use.
    $testSource = New-Object System.Windows.Controls.Button
    $testSource.Content = 'Testdatei ziehen'
    $testSource.Margin = New-Object System.Windows.Thickness(0, 0, 8, 0)
    $testSource.ToolTip = 'Diagnose: gedrückt auf die Importfläche ziehen'
    $testSource.add_PreviewMouseMove({
            if ($_.LeftButton -eq [System.Windows.Input.MouseButtonState]::Pressed -and !$script:busy) {
                $data = New-Object System.Windows.DataObject
                $paths = @($DropPaths) + @($DropPath) | Where-Object { $_ }
                $data.SetData([System.Windows.DataFormats]::FileDrop, [string[]]$paths)
                [System.Windows.DragDrop]::DoDragDrop($testSource, $data, [System.Windows.DragDropEffects]::Copy) | Out-Null
            }
        })
    $stack = $ui.HeaderTools
    $stack.Children.Insert(0, $testSource)
    $script:pendingDrop = $null
}
Initialize-Appearance
$window.add_SourceInitialized({ Apply-Theme })
$window.add_ContentRendered({ Update-LayoutBounds
        try {
            Save-Preferences
        }
        catch {
            Add-Activity $_.Exception.Message 'warning'
        }
        Begin-Operation $(if ($ReadOnlySession) {
                'list'
            }
            else {
                'bootstrap'
            }) })
$window.add_Closing({ if ($script:busy) {
            $_.Cancel = $true
            Set-Status (L 'Bitte den laufenden Vorgang beenden lassen, bevor du das Fenster schließt.') 'warning'
        } })
$window.add_Closed({ $timer.Stop()
        $ui.BusyProgress.IsIndeterminate = $false })
Set-Busy $false
[void]$window.ShowDialog()
