# Small presentation helpers; no mod activation or profile writes happen here.
function Read-Preferences {
    $defaults = @{app ='OpenSmashModsPreferences-v1'
        glass         ='Solid'
        theme         ='System'
        repo          =''
        install_dir   =''
        library_view  = 'List'
    }
    if (Test-Path -LiteralPath $script:settingsFile) {
        try {
            if ((Get-Item -LiteralPath $script:settingsFile).Length -gt 65536) {
                return $defaults
            }
            $value = [IO.File]::ReadAllText($script:settingsFile) | ConvertFrom-Json
            if ($value.app -eq $defaults.app) {
                if ($value.theme -in @('Light', 'Dark', 'System')) {
                    $defaults.theme = [string]$value.theme
                }
                if ($value.library_view -in @('List', 'Tiles')) { $defaults.library_view = [string]$value.library_view }
                $defaults.repo = [string]$value.repo
                $defaults.install_dir = [string]$value.install_dir
            }
        }
        catch {
        }
    }
    return $defaults
}
function Quote-Arg([string]$value) {
    return '"' + [regex]::Replace([regex]::Replace($value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
}
function Resolve-Python([string]$game) {
    $candidates = @((Join-Path $PSScriptRoot 'runtime\python.exe'))
    if ($script:preferences.install_dir) {
        $candidates += Join-Path $script:preferences.install_dir 'runtime\python.exe'
    }
    if ($game) {
        $candidates += Join-Path $game 'deps\python\python.exe'
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command -and $command.Source -notlike '*\WindowsApps\*') {
        return $command.Source
    }
    throw (L 'Python-Runtime fehlt. Bitte den vollstaendigen Installer verwenden.')
}
function Show-ConnectionDialog {
    $dialog = New-Object System.Windows.Window
    Initialize-DialogAppearance $dialog
    $dialog.Title = (L 'OpenSmash verbinden')
    $dialog.Width = 620
    $dialog.Height = 450
    $dialog.MinWidth = 540
    $dialog.MinHeight = 400
    $dialog.WindowStartupLocation = 'CenterScreen'
    $dialog.FontFamily = 'Trebuchet MS, Segoe UI'
    $dialog.FontSize = 14
    $grid = New-Object System.Windows.Controls.Grid
    $grid.Margin = New-Object System.Windows.Thickness(24)
    $dialog.Content = $grid
    foreach ($height in @('Auto', 'Auto', 'Auto', '*', 'Auto')) {
        $row = New-Object System.Windows.Controls.RowDefinition
        $row.Height = [System.Windows.GridLengthConverter]::new().ConvertFromString($height)
        $grid.RowDefinitions.Add($row)
    }
    $title = New-Object System.Windows.Controls.TextBlock
    $title.Text = (L 'Dein OpenSmash verbinden')
    $title.FontSize = 24
    $title.FontWeight = 'SemiBold'
    $title.Margin = New-Object System.Windows.Thickness(0, 0, 0, 12)
    $grid.Children.Add($title) | Out-Null
    $intro = New-Object System.Windows.Controls.TextBlock
    $intro.Text = (L 'Waehle deinen eingerichteten OpenSmash-Ordner mit Play SSBU.bat. Spiel und eigene Spieldaten werden separat bereitgestellt.')
    $intro.TextWrapping = 'Wrap'
    $intro.Margin = New-Object System.Windows.Thickness(0, 0, 0, 14)
    [System.Windows.Controls.Grid]::SetRow($intro, 1)
    $grid.Children.Add($intro) | Out-Null
    $picker = New-Object System.Windows.Controls.StackPanel
    [System.Windows.Controls.Grid]::SetRow($picker, 2)
    $grid.Children.Add($picker) | Out-Null
    $pathBox = New-Object System.Windows.Controls.TextBox
    $pathBox.Padding = New-Object System.Windows.Thickness(8)
    $pathBox.ToolTip = (L 'OpenSmash-Projektpfad hier einfuegen')
    $pathBox.SetValue([System.Windows.Automation.AutomationProperties]::NameProperty, (L 'OpenSmash-Pfad'))
    $picker.Children.Add($pathBox) | Out-Null
    $buttons = New-Object System.Windows.Controls.StackPanel
    $buttons.Orientation = 'Horizontal'
    $buttons.Margin = New-Object System.Windows.Thickness(0, 8, 0, 0)
    $picker.Children.Add($buttons) | Out-Null
    $pick = New-Object System.Windows.Controls.Button
    $pick.Content = (L 'Ordner auswaehlen…')
    $pick.Padding = New-Object System.Windows.Thickness(12, 8, 12, 8)
    $buttons.Children.Add($pick) | Out-Null
    $validate = New-Object System.Windows.Controls.Button
    $validate.Content = (L 'Pfad pruefen')
    $validate.Padding = $pick.Padding
    $validate.Margin = New-Object System.Windows.Thickness(8, 0, 0, 0)
    $buttons.Children.Add($validate) | Out-Null
    $details = New-Object System.Windows.Controls.TextBox
    $details.IsReadOnly = $true
    $details.TextWrapping = 'Wrap'
    $details.VerticalScrollBarVisibility = 'Auto'
    $details.Background = [Windows.Media.Brushes]::Transparent
    $details.BorderThickness = New-Object System.Windows.Thickness(0)
    $details.Margin = New-Object System.Windows.Thickness(0, 16, 0, 12)
    $details.Text = (L 'Der Manager prueft den Ordner und zeigt fehlende Voraussetzungen.')
    [System.Windows.Controls.Grid]::SetRow($details, 3)
    $grid.Children.Add($details) | Out-Null
    $connect = New-Object System.Windows.Controls.Button
    $connect.Content = (L 'Verbinden und oeffnen')
    $connect.IsEnabled = $false
    $connect.Padding = New-Object System.Windows.Thickness(12, 9, 12, 9)
    [System.Windows.Controls.Grid]::SetRow($connect, 4)
    $grid.Children.Add($connect) | Out-Null
    $probeTimer = New-Object System.Windows.Threading.DispatcherTimer
    $probeTimer.Interval = [TimeSpan]::FromMilliseconds(120)
    $dialog.Tag = @{Path =$null
        Job              =$null
        Result           =$null
    }
    function Start-ConnectionProbe([string]$chosen) {
        try {
            $chosen = $chosen.Trim().Trim('"')
            if (!(Test-Path -LiteralPath $chosen -PathType Container)) {
                throw (L 'Bitte einen vorhandenen OpenSmash-Ordner auswaehlen.')
            }
            $pathBox.Text = $chosen
            $dialog.Tag.Path = $chosen
            $connect.IsEnabled = $false
            $pick.IsEnabled = $false
            $validate.IsEnabled = $false
            $pathBox.IsEnabled = $false
            $details.Text = (L 'Installation wird geprueft…')
            $info = New-Object Diagnostics.ProcessStartInfo
            $info.FileName = Resolve-Python $chosen
            $info.WorkingDirectory = $chosen
            $info.StandardOutputEncoding = New-Object Text.UTF8Encoding($false)
            $info.StandardErrorEncoding = $info.StandardOutputEncoding
            $info.EnvironmentVariables['PYTHONUTF8'] = '1'
            $info.Arguments = (@((Join-Path $PSScriptRoot 'modmanager.py'), '--repo', $chosen, 'check') | ForEach-Object { Quote-Arg $_ }) -join ' '
            $dialog.Tag.Result = $null
            $dialog.Tag.Job = [OpenSmash.BackendJob]::Start($info, $null)
            $probeTimer.Start()
        }
        catch {
            $details.Text = $_.Exception.Message
            $pick.IsEnabled = $true
            $validate.IsEnabled = $true
            $pathBox.IsEnabled = $true
        }
    }
    $pathBox.add_TextChanged({ $connect.IsEnabled = $false })
    $validate.add_Click({ Start-ConnectionProbe $pathBox.Text })
    $pick.add_Click({
            $folder = New-Object System.Windows.Forms.FolderBrowserDialog
            $folder.Description = (L 'OpenSmash-Projektordner mit Play SSBU.bat')
            try {
                if ($folder.ShowDialog() -ne 'OK') {
                    return
                }
                Start-ConnectionProbe $folder.SelectedPath
            }
            catch {
                $details.Text = $_.Exception.Message
                $pick.IsEnabled = $true
            }
            finally {
                $folder.Dispose()
            }
        })
    $probeTimer.add_Tick({
            $job = $dialog.Tag.Job
            foreach ($line in $job.Drain()) {
                try {
                    $dialog.Tag.Result = $line | ConvertFrom-Json
                }
                catch {
                }
            }
            if (!$job.Process.HasExited -or !$job.OutputComplete -or $job.PendingLines) {
                return
            }
            $probeTimer.Stop()
            $pick.IsEnabled = $true
            $validate.IsEnabled = $true
            $pathBox.IsEnabled = $true
            $response = $dialog.Tag.Result
            if ($response.ok) {
                $result = $response.result
                $connect.IsEnabled = [bool]$result.manager_ready
                $details.Text = (@($result.issues) + @($result.warnings)) -join "`r`n`r`n"
                if (!$details.Text) {
                    $details.Text = (L 'OpenSmash ist bereit. Du kannst den Manager jetzt verbinden.')
                }
            }
            else {
                $details.Text = [string]$response.error
            }
            $job.Dispose()
            $dialog.Tag.Job = $null
        })
    $connect.add_Click({ $dialog.DialogResult = $true })
    $dialog.add_Closing({ if ($null -ne $dialog.Tag.Job) {
                $_.Cancel = $true
                $details.Text = (L 'Bitte die kurze Pruefung abschliessen lassen.')
            } })
    $dialog.add_Closed({ $probeTimer.Stop() })
    if ($dialog.ShowDialog()) {
        return $dialog.Tag.Path
    }
    return $null
}
function Save-Preferences {
    if ($SmokeTest -or $ReadOnlySession) {
        return
    }
    $value = Read-Preferences
    $value.glass = $script:glassPreset
    $value.theme = $script:themeChoice
    $value.library_view = $script:libraryView
    if ($Repo) {
        $value.repo = $Repo
    }
    if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'runtime\python.exe')) {
        $value.install_dir = $PSScriptRoot
    }
    $parent = Split-Path $script:settingsFile -Parent
    [IO.Directory]::CreateDirectory($parent) | Out-Null
    $temporary = Join-Path $parent ('preferences-' + [guid]::NewGuid().ToString('N') + '.tmp')
    try {
        [IO.File]::WriteAllText($temporary, ($value | ConvertTo-Json), (New-Object Text.UTF8Encoding($false)))
        if (Test-Path -LiteralPath $script:settingsFile) {
            [IO.File]::Replace($temporary, $script:settingsFile, [NullString]::Value)
        }
        else {
            [IO.File]::Move($temporary, $script:settingsFile)
        }
    }
    finally {
        if (Test-Path -LiteralPath $temporary) {
            [IO.File]::Delete($temporary)
        }
    }
}
function Set-Resource([string]$key, $value) {
    $window.Resources.Remove($key)
    $window.Resources.Add($key, $value)
}
function Brush([string]$color) {
    $value = New-Object System.Windows.Media.SolidColorBrush ([System.Windows.Media.ColorConverter]::ConvertFromString($color))
    $value.Freeze()
    return $value
}
function Apply-Glass {
    # Legacy preference values migrate to an opaque surface; no opt-in blur remains.
    $script:glassPreset = 'Solid'
    $script:effectiveGlass = 'Solid'
    $script:backdrop = [OpenSmash.UiNative]::Backdrop($window, $false, $script:dark)
    $window.Background = $window.Resources['WindowSurface']
    if ($script:glassMenu) {
        foreach ($entry in $script:glassMenu.Items) {
            if ($entry -is [System.Windows.Controls.MenuItem]) {
                $entry.IsChecked = ([string]$entry.Tag -eq 'theme:' + $script:themeChoice)
            }
        }
    }
}
function Show-HeaderMenu($button, $menu) {
    $menu.Measure([System.Windows.Size]::new([double]::PositiveInfinity, [double]::PositiveInfinity))
    $menu.PlacementTarget = $button
    $menu.Placement = 'Bottom'
    $menu.HorizontalOffset = $button.ActualWidth - $menu.DesiredSize.Width
    $menu.IsOpen = $true
}
function Initialize-Appearance {
    $script:glassMenu = New-Object System.Windows.Controls.ContextMenu
    $glassMenu.Style = $window.Resources['AppearanceMenu']
    $glassMenu.Background = $window.Resources['PopupSurface']
    $glassMenu.Foreground = $window.Resources['Text']
    foreach ($pair in @(@('Light', (L 'Heller Modus')), @('Dark', (L 'Dunkler Modus')), @('System', (L 'Wie Windows')))) {
        $entry = New-Object System.Windows.Controls.MenuItem
        $entry.Header = $pair[1]
        $entry.Tag = 'theme:' + $pair[0]
        $entry.IsCheckable = $true
        $entry.Padding = New-Object System.Windows.Thickness(12, 8, 12, 8)
        $entry.Style = $window.Resources['AppearanceItem']
        $entry.add_Click({ param($sender, $event) $script:themeChoice = ([string]$sender.Tag).Substring(6)
                Apply-Theme
                try {
                    Save-Preferences
                }
                catch {
                    Add-Activity $_.Exception.Message 'warning'
                } })
        $glassMenu.Items.Add($entry) | Out-Null
    }
    $ui.AppearanceButton.ContextMenu = $glassMenu
    $ui.AppearanceButton.add_Click({ Show-HeaderMenu $ui.AppearanceButton $glassMenu })
}
function Update-ImportActions {
    $selected = $ui.BatchList.SelectedItem
    $canChoose = (!$script:busy -and !$ReadOnlySession -and $script:preview -and $script:preview.kind -ne 'mod-list' -and $selected -and $selected.Raw.status -in @('ready', 'conflict'))
    $ui.ConflictActions.Visibility = if ($canChoose) {
        'Visible'
    }
    else {
        'Collapsed'
    }
    $ui.ConflictDisabled.IsEnabled = [bool]$canChoose
    $ui.ConflictReplace.IsEnabled = ([bool]$canChoose -and @($selected.Raw.conflict_ids).Count -gt 0)
    $ui.ConflictOverlay.IsEnabled = ($ui.ConflictReplace.IsEnabled -and !$selected.Raw.framework_conflict)
    $ui.ConflictUnderlay.IsEnabled = $ui.ConflictOverlay.IsEnabled
}
function Set-BatchRows($items) {
    $labels = @{ready =(L 'Bereit')
        invalid       =(L 'Ungueltig')
        existing      =(L 'Schon vorhanden')
        duplicate     =(L 'Doppelt')
        conflict      =(L 'Konflikt')
        installed     =(L 'Installiert')
        failed        =(L 'Fehlgeschlagen')
        cancelled     =(L 'Abgebrochen')
        working       =(L 'In Arbeit')
        skipped       =(L 'Ausgelassen')
    }
    $values = New-Object 'System.Collections.Generic.List[object]'
    foreach ($item in @($items)) {
        $values.Add([pscustomobject]@{Name =[string]$item.name
                Status                     =$labels[[string]$item.status]
                Message                    =([string]$item.message + $(if ($item.compatibility) {
                            ' · ' + $item.compatibility + ' — ' + $item.evidence
                        }
                        else {
                            ''
                        })); ItemId=[string]$item.item_id; Raw=$item
            })
    }
    $ui.BatchList.ItemsSource = $values.ToArray()
    $ui.BatchTab.Visibility = 'Visible'
    $ui.DetailTabs.SelectedIndex = 2
    Update-ImportActions
}
function Set-BatchProgress($event) {
    if ($event.job_id -match '^[0-9a-f]{32}$') {
        $script:batchJob = [string]$event.job_id
    }
    $ui.BatchTab.Visibility = 'Visible'
    $ui.DetailTabs.SelectedIndex = 2
    $ui.BatchCancel.IsEnabled = (!$script:cancelRequested)
    $ui.BatchProgress.Maximum = [math]::Max(1, [int]$event.total)
    $ui.BatchProgress.Value = [math]::Min($ui.BatchProgress.Maximum, [int]$event.current)
    $verb = switch ($event.phase) {
        'list_download' { (L 'Herunterladen') }
        'preview' {
            (L 'Pruefen')
        } 'preview_done' {
            (L 'Pruefung abgeschlossen')
        } 'install' {
            (L 'Vorbereiten')
        } 'commit' {
            (L 'Profil sicher umschalten')
        } 'done' {
            (L 'Abgeschlossen')
        } default {
            (L 'Import')
        }
    }
    $ui.BatchSummary.Text = ('{0}: {1}/{2} · {3}' -f $verb, $event.current, $event.total, $event.name)
    if ($null -ne $event.failed) {
        $ui.BatchSummary.Text += (L ' · Fehler: ') + $event.failed
    }
}
function Accept-Drops([string[]]$paths) {
    if (Get-Command Show-Workspace -ErrorAction SilentlyContinue) {
        Show-Workspace 'Library'
    }
    if ($script:busy -or $null -eq $script:state -or !$paths.Count) {
        return
    }
    $script:preview = $null
    if ($paths.Count -eq 1 -and [IO.Path]::GetExtension($paths[0]) -eq '.json') {
        Begin-Operation 'list-preview' @('--source', $paths[0]); return
    }
    $ui.InstallButton.IsEnabled = $false
    $script:cancelRequested = $false
    $payload = @{sources =@($paths)
        previous_job     =$script:batchJob
    }
    $script:batchJob = $null
    $ui.BatchSummary.Text = (L 'Auswahl wird geprueft. Fortschritt nach Quellen/Mods.')
    $ui.BatchList.ItemsSource = $null
    $ui.BatchTab.Visibility = 'Visible'
    $ui.DetailTabs.SelectedIndex = 2
    Begin-Operation 'batch-preview' @('--stdin') $payload
}
function Cancel-Batch {
    if (!$script:busy -or !$script:batchJob -or $script:batchJob -notmatch '^[0-9a-f]{32}$') {
        return
    }
    $file = Join-Path $Repo ('opensmash_mods\incoming\batch-' + $script:batchJob + '\cancel.request')
    try {
        [IO.File]::WriteAllText($file, 'cancel')
        $script:cancelRequested = $true
        $ui.BatchCancel.IsEnabled = $false
        Set-Status (L 'Abbruch angefordert. Ein laufender Profilwechsel wird sicher beendet.') 'warning'
    }
    catch {
        Show-Failure ((L 'Abbruch konnte nicht angefordert werden: ') + $_.Exception.Message)
    }
}

function Export-Library {
    if (!$ui.ExportButton.IsEnabled) {
        return
    }
    $dialog = New-Object Microsoft.Win32.SaveFileDialog
    $dialog.Title = (L 'Alle installierten Mods exportieren')
    $dialog.Filter = 'ZIP-Modpaket (*.zip)|*.zip'
    $dialog.DefaultExt = '.zip'
    $dialog.AddExtension = $true
    $dialog.OverwritePrompt = $true
    $dialog.FileName = 'OpenSmash-Modpaket-' + [datetime]::Now.ToString('yyyy-MM-dd') + '.zip'
    if ($dialog.ShowDialog($window)) {
        Begin-Operation 'export' @('--destination', $dialog.FileName)
    }
}
