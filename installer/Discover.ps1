# Native WPF browser. Network workers never take the deployment/UI busy lane.
. (Join-Path $PSScriptRoot 'ImageViewer.ps1')
$script:pictureViewer = $null
$script:netJobs = @{}
$script:gbPage = 1
$script:gbConfig = $null
$script:gbDetail = $null
$script:gbGallery = 0
$script:gbBatch = @()
$script:gbBatchTotal = 0
$script:gbChanging = $false
$script:gbLoaded = $false
$script:gbImageSeen = @{}
$script:workspace = 'Library'
$script:dqJobs = @()
$script:dqLast = [datetime]::MinValue
$script:dqRows = New-Object 'System.Collections.ObjectModel.ObservableCollection[OpenSmash.DownloadRow]'
foreach ($viewName in @('Discover', 'Downloads')) {
    $viewFile = Join-Path $PSScriptRoot ($viewName + '.xaml')
    # These trusted local view files share the established window resources.
    $xmlReader = [System.Xml.XmlNodeReader]::new((ConvertTo-LocalizedXaml ([IO.File]::ReadAllText($viewFile, [Text.Encoding]::UTF8))))
    try {
        $part = [System.Windows.Markup.XamlReader]::Load($xmlReader)
    }
    finally {
        $xmlReader.Close()
    }
    $ui[$viewName + 'Workspace'].Content = $part
    foreach ($node in ([xml][IO.File]::ReadAllText($viewFile)).SelectNodes('//*[@*[local-name()="Name"]]')) {
        $n = $node.GetAttribute('Name', 'http://schemas.microsoft.com/winfx/2006/xaml')
        $ui[$n] = $part.FindName($n)
    }
}
$ui.DQList.ItemsSource = $script:dqRows
function Show-Workspace([string]$name) {
    $script:workspace = $name
    foreach ($areaName in @('Library', 'Discover', 'Downloads')) {
        $ui[$areaName + 'Workspace'].Visibility = if ($areaName -eq $name) {
            'Visible'
        }
        else {
            'Collapsed'
        }
        $ui[$areaName + 'Nav'].FontWeight = if ($areaName -eq $name) {
            'Bold'
        }
        else {
            'Normal'
        }
        $ui[$areaName + 'Nav'].SetResourceReference([System.Windows.Controls.Control]::BackgroundProperty, $(if ($areaName -eq $name) {
                    'SelectedSurface'
                }
                else {
                    'ButtonSurface'
                }))
    }
    $ui.DropSurface.Visibility = if ($name -eq 'Library') {
        'Visible'
    }
    else {
        'Collapsed'
    }
    $ui.Layout.RowDefinitions[2].Height = if ($name -eq 'Library') {
        [System.Windows.GridLength]::new(78)
    }
    else {
        [System.Windows.GridLength]::new(0)
    }
    if ($name -eq 'Discover' -and !$script:gbLoaded) {
        $script:gbLoaded = $true
        Start-Net 'config' @{} 'config'
    }
    if ($name -eq 'Downloads') {
        Start-Net 'status' @{} 'status'
        Start-Transfers
    }
}
function Start-Net([string]$action, $payload, [string]$lane = $action, $tag = $null) {
    if ($script:netJobs.ContainsKey($lane)) {
        if ($lane -notin @('browse', 'detail', 'gallery', 'full-image')) {
            return
        }
        $old = $script:netJobs[$lane]
        try {
            if (!$old.Job.Process.HasExited) {
                $old.Job.Process.Kill()
            }
        }
        catch {
        }
        $old.Job.Dispose()
        $script:netJobs.Remove($lane)
    }
    try {
        $info = New-Object System.Diagnostics.ProcessStartInfo
        $info.FileName = $script:python
        $info.WorkingDirectory = $Repo
        $info.Arguments = (@((Join-Path $PSScriptRoot 'network.py'), '--repo', $Repo, $action) | ForEach-Object { Quote-Arg $_ }) -join ' '
        $info.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
        $info.StandardErrorEncoding = $info.StandardOutputEncoding
        $info.EnvironmentVariables['PYTHONUTF8'] = '1'
        $job = [OpenSmash.BackendJob]::Start($info, ($payload | ConvertTo-Json -Depth 7 -Compress))
        $script:netJobs[$lane] = @{Action =$action
            Job                           =$job
            Result                        =$null
            Payload                       =$payload
            Tag                           =$tag
            Noise                         =''
        }
    }
    catch {
        $ui.GBResults.Text = $_.Exception.Message
        Add-Activity $_.Exception.Message 'error'
    }
}
function Show-LinkDialog {
    $dialog = New-Object System.Windows.Window
    Initialize-DialogAppearance $dialog
    $dialog.Title = (L 'GameBanana-Link öffnen')
    $dialog.Owner = $window
    $dialog.Width = 600
    $dialog.Height = 220
    $dialog.ResizeMode = 'NoResize'
    $dialog.WindowStartupLocation = 'CenterOwner'
    $dialog.FontFamily = $window.FontFamily
    $dialog.FontSize = 14
    $dialog.Background = $window.Resources['ContentSurface']
    $dialog.Foreground = $window.Resources['Text']
    $panel = New-Object System.Windows.Controls.StackPanel
    $panel.Margin = New-Object System.Windows.Thickness(22)
    $dialog.Content = $panel
    $label = New-Object System.Windows.Controls.TextBlock
    $label.Text = (L 'Modseite oder kopierten 1-Click-Link einfügen:')
    $panel.Children.Add($label) | Out-Null
    $input = New-Object System.Windows.Controls.TextBox
    $input.Margin = New-Object System.Windows.Thickness(0, 10, 0, 12)
    $input.Padding = New-Object System.Windows.Thickness(8)
    $input.MaxLength = 2048
    $panel.Children.Add($input) | Out-Null
    $open = New-Object System.Windows.Controls.Button
    $open.Content = (L 'Öffnen')
    $open.Padding = New-Object System.Windows.Thickness(16, 8, 16, 8)
    $open.HorizontalAlignment = 'Right'
    $open.IsDefault = $true
    $panel.Children.Add($open) | Out-Null
    $dialog.Tag = @{Input =$input
        Value             =$null
    }
    $open.add_Click({ param($sender, $event) $d = [System.Windows.Window]::GetWindow($sender)
            if ($d.Tag.Input.Text.Trim()) {
                $d.Tag.Value = $d.Tag.Input.Text.Trim()
                $d.DialogResult = $true
            } })
    if ($dialog.ShowDialog() -and $dialog.Tag.Value) {
        $script:pendingLinks.Enqueue([string]$dialog.Tag.Value)
    }
}
function Start-Transfers {
    if (!$ReadOnlySession) {
        Start-Net 'run' @{} 'transfer'
    }
}
function Search-GameBanana([bool]$reset = $false) {
    if (!$script:gbConfig) {
        return
    }
    if ($reset) {
        $script:gbPage = 1
    }
    $category = $ui.GBCategory.SelectedItem
    if (!$category) {
        return
    }
    $character = if ($ui.GBCharacter.SelectedItem) {
        [int]$ui.GBCharacter.SelectedItem.id
    }
    else {
        0
    }
    $ui.GBSearch.IsEnabled = ($character -eq 0)
    $query = $ui.GBSearch.Text.Trim()
    $hasQuery = ($query.Length -gt 0)
    $ui.GBCategory.IsEnabled = (!$hasQuery)
    $ui.GBSort.IsEnabled = (!$hasQuery)
    $sort = if ($ui.GBSort.SelectedItem) {
        $ui.GBSort.SelectedItem.key
    }
    else {
        'newest'
    }
    $ui.GBResults.Text = if ($hasQuery) {
        (L 'Suche nach Relevanz · ') + $category.model + ' …'
    }
    else {
        (L 'Katalog wird geladen…')
    }
    Start-Net 'browse' @{query =$query
        model                  =$category.model
        category               =$category.id
        sort                   =$sort
        page                   =$script:gbPage
        character              =$character
    } 'browse'
}
function Show-GBDetail($detail) {
    $ui.GBDetailScroll.ScrollToTop()
    $script:gbDetail = $detail
    $script:gbGallery = 0
    $ui.GBTitle.Text = $detail.title
    $date = if ($detail.updated) {
        [DateTimeOffset]::FromUnixTimeSeconds([long]$detail.updated).LocalDateTime.ToString('d', [Globalization.CultureInfo]::CurrentCulture)
    }
    else {
        (L 'Datum unbekannt')
    }
    $ui.GBMeta.Text = $detail.author + ' · ' + $detail.category + ' · ' + $date + $(if ($detail.version) {
            ' · ' + $detail.version
        }
        else {
            ''
        }) + $(if ($null -ne $detail.downloads) {
            ' · ' + $detail.downloads + ' Downloads'
        }
        else {
            ''
        })
    $ui.GBDescription.Text = $detail.description
    $ui.GBInstructions.Text = $detail.dependencies + "`r`n`r`n" + $detail.instructions
    $ui.GBCompatibility.Text = (L 'Noch ungeprüft · Dateiprüfung nach dem Download.')
    $variants = @($detail.files | ForEach-Object { [pscustomobject]@{label =($_.name + ' · ' + [math]::Round($_.size / 1MB, 2) + ' MB' + $(if ($_.archived) {
                            (L ' · Archiviert')
                        }
                        else {
                            ''
                        }) + $(if (!$_.supported -and $_.downloadable) {
                            (L ' · Nur Download')
                        }
                        elseif (!$_.supported) {
                            (L ' · Gesperrt')
                        }
                        else {
                            ''
                        })); Raw                                           =$_
            } })
    $ui.GBFiles.ItemsSource = $variants
    $ui.GBFiles.SelectedIndex = -1
    $ui.GBFiles.IsEnabled = ($variants.Count -gt 0)
    $ui.GBFileHint.Text = if ($variants.Count) {
        (L 'Keine Variante vorausgewählt.')
    }
    else {
        (L 'Keine öffentlichen Dateivarianten verfügbar. Quellseite prüfen.')
    }
    $ui.GBQueue.IsEnabled = $false
    $ui.GBSource.IsEnabled = $true
    $ui.GBSkip.Visibility = if ($script:gbBatchTotal) {
        'Visible'
    }
    else {
        'Collapsed'
    }
    $ui.GBBatchHint.Text = if ($script:gbBatchTotal) {
        ((L 'Stapel {0}/{1}: Datei wählen oder überspringen') -f ($script:gbBatchTotal - $script:gbBatch.Count), $script:gbBatchTotal)
    }
    else {
        (L 'Dateivariante ausdrücklich auswählen:')
    }
    Show-GBImage
    $ui.GBDetailScroll.UpdateLayout()
    $ui.GBDetailScroll.ScrollToTop()
    # Layout requests can otherwise retain the previous mod's scroll position.
    $ui.GBDetailScroll.Dispatcher.BeginInvoke([Windows.Threading.DispatcherPriority]::ContextIdle, [Action] { $ui.GBDetailScroll.ScrollToTop() }) | Out-Null
}
function Show-GBImage {
    $ui.GBImage.Source = $null
    $ui.GBGalleryFrame.Visibility = if ($script:gbDetail -and @($script:gbDetail.images).Count) {
        'Visible'
    }
    else {
        'Collapsed'
    }
    $ui.GBImagePrevious.IsEnabled = ($script:gbGallery -gt 0)
    $ui.GBImageNext.IsEnabled = ($script:gbDetail -and $script:gbGallery + 1 -lt @($script:gbDetail.images).Count)
    if ($script:gbDetail -and @($script:gbDetail.images).Count) {
        $url = @($script:gbDetail.images)[$script:gbGallery]
        Start-Net 'image' @{url = $url } 'gallery' $script:gbDetail.id
    }
}
function Next-GBVariant {
    if ($script:gbBatch.Count) {
        $row = $script:gbBatch[0]
        $script:gbBatch = @($script:gbBatch | Select-Object -Skip 1)
        $ui.GBTitle.Text = (L 'Dateivarianten werden geladen…')
        $ui.GBQueue.IsEnabled = $false
        Start-Net 'detail' @{model =$row.Model
            id                     =$row.Id
        } 'detail'
    }
    else {
        $script:gbBatchTotal = 0
        $ui.GBSkip.Visibility = 'Collapsed'
        $ui.GBBatchHint.Text = (L 'Auswahl fertig. Downloads vor Installation prüfen.')
    }
}
function Show-DownloadState($result) {
    $script:dqJobs = @($result.items)
    $existing = @{}; foreach ($row in $script:dqRows) { $existing[$row.Id] = $row }
    $labels = @{queued =(L 'Wartet')
        downloading    ='Download'
        verifying      =(L 'Prüfung')
        downloaded     =(L 'Abgeschlossen')
        failed         =(L 'Fehlgeschlagen')
        cancelled      =(L 'Abgebrochen')
        interrupted    =(L 'Unterbrochen')
    }
    $rows = @($script:dqJobs | ForEach-Object { [pscustomobject]@{id =$_.id
                title                                                =$_.title
                status                                               =$_.status
                caption                                              =($labels[$_.status] + ' · ' + $_.file.name + ' · ' + [math]::Round($_.bytes / 1MB, 1) + ' / ' + [math]::Round($_.total / 1MB, 1) + ' MB' + $(if ($_.status -eq 'downloading') {
                            ' · ' + [math]::Round($_.speed / 1MB, 2) + ' MB/s'
                        }
                        else {
                            ''
                        }) + $(if ($_.compatibility -eq 'Experimental') {
                            (L ' · Experimentell')
                        }
                        elseif ($_.compatibility -eq 'DownloadOnly') {
                            (L ' · Nur Download')
                        }
                        elseif ($_.compatibility -eq 'Unsupported') {
                            (L ' · Nicht unterstützt')
                        }
                        else {
                            ''
                        })); percent=([math]::Min(100, 100 * $_.bytes / [math]::Max(1, $_.total))); message=$_.message; evidence=($_.compatibility + ' · ' + $_.evidence); Raw=$_
            } })
    # Keep row/container identities stable. Reassigning ItemsSource retriggers
    # selection animations, loses keyboard focus and needlessly rebuilds WPF.
    $wanted = @{}; $index = 0
    foreach ($value in $rows) {
        $wanted[$value.id] = $true
        $row = $existing[$value.id]
        if (!$row) { $row = New-Object OpenSmash.DownloadRow; $row.Id = $value.id; $script:dqRows.Insert($index, $row) }
        elseif ($script:dqRows[$index].Id -ne $value.id) { $script:dqRows.Move($script:dqRows.IndexOf($row), $index) }
        $row.Update($value.title, $value.status, $value.caption, $value.message, $value.evidence, $value.percent, $value.Raw)
        $index++
    }
    for ($index = $script:dqRows.Count - 1; $index -ge 0; $index--) { if (!$wanted.ContainsKey($script:dqRows[$index].Id)) { $script:dqRows.RemoveAt($index) } }
    $active = @($rows | Where-Object { $_.status -in @('queued', 'downloading', 'verifying') }).Count
    $ui.DQSummary.Text = ((L '{0} Downloads · {1} in Arbeit.') -f $rows.Count, $active)
    $ui.DownloadsNav.Content = (L 'Downloads') + $(if ($active) {
            ' (' + $active + ')'
        }
        else {
            ''
        })
    Update-DownloadActions
}
function Update-DownloadActions {
    $selected = @($ui.DQList.SelectedItems)
    $ui.DQInspect.IsEnabled = (!$ReadOnlySession -and !$script:busy -and @($selected | Where-Object { $_.status -eq 'downloaded' -and $_.Raw.compatibility -ne 'DownloadOnly' }).Count -gt 0)
    $ui.DQCancel.IsEnabled = (!$ReadOnlySession -and @($selected | Where-Object { $_.status -in @('queued', 'downloading', 'verifying') }).Count -gt 0)
    $ui.DQRemove.IsEnabled = (!$ReadOnlySession -and !$script:netJobs.ContainsKey('remove') -and $selected.Count -gt 0 -and @($selected | Where-Object { $_.status -notin @('downloaded', 'failed', 'cancelled', 'interrupted') }).Count -eq 0)
    $ui.DQRetry.IsEnabled = (!$ReadOnlySession -and @($selected | Where-Object { $_.status -in @('failed', 'cancelled', 'interrupted') }).Count -gt 0)
    $ui.DQClear.IsEnabled = (!$ReadOnlySession -and $script:dqRows.Count -gt 0 -and !$script:netJobs.ContainsKey('clear'))
    $ui.DQSave.Visibility = if ($selected.Count -eq 1 -and $selected[0].Raw.compatibility -eq 'DownloadOnly') { 'Visible' }else { 'Collapsed' }
    $ui.DQSave.IsEnabled = (!$ReadOnlySession -and $selected.Count -eq 1 -and $selected[0].status -eq 'downloaded' -and !$script:netJobs.ContainsKey('save'))
}
function Accept-NetResult($op, $result) {
    switch ($op.Action) {
        'save' { Set-Status (L 'Datei gespeichert.') 'success' }
        'clear' { Show-DownloadState $result; Set-Status $(if ($result.pending) { L 'Downloads werden abgebrochen und automatisch entfernt.' }else { L 'Alle Downloads entfernt. Installierte Mods bleiben erhalten.' }) 'success' }
        'remove' { Show-DownloadState $result; Set-Status (L 'Download entfernt. Installierte Mods bleiben erhalten.') 'success' }
        'set-preview' { Accept-LibraryImage $result }
        'library-images' { foreach ($entry in @($result.items)) { Accept-LibraryImage $entry }; Start-LibraryImages }
        'config' {
            $script:gbChanging = $true
            $script:gbConfig = $result
            foreach ($category in $result.categories) {
                $category.name = L $category.name
            }
            $ui.GBCharacter.ItemsSource = @([pscustomobject]@{id =0
                    name                                         =(L 'Alle Charaktere')
                }) + @($result.characters)
            $ui.GBCharacter.SelectedIndex = 0
            $ui.GBCharacter.IsEnabled = (@($result.characters).Count -gt 0)
            $ui.GBCategory.ItemsSource = @($result.categories)
            $ui.GBCategory.SelectedIndex = 0
            $script:gbChanging = $false
            Set-GBSort
            Search-GameBanana $true
        }
        'browse' {
            $values = New-Object 'System.Collections.Generic.List[OpenSmash.BrowserRow]'
            foreach ($item in @($result.items)) {
                $row = New-Object OpenSmash.BrowserRow
                $row.Id = $item.id
                $row.Model = $item.model
                $row.Title = $item.title
                $row.Data = $item
                $row.ImageUrl = $item.thumbnail
                $row.Meta = $item.author + ' · ' + $item.category + $(if ($null -ne $item.likes) {
                        ' · ♥ ' + $item.likes
                    }
                    else {
                        ''
                    }) + $(if ($null -ne $item.downloads) {
                        ' · ↓ ' + $item.downloads
                    }
                    else {
                        ''
                    })
                $row.Status = $(if ($item.installed) {
                        (L 'Installiert · ')
                    }
                    else {
                        ''
                    }) + (L 'Noch ungeprüft') + $(if ($item.updated) {
                        ' · ' + [DateTimeOffset]::FromUnixTimeSeconds([long]$item.updated).LocalDateTime.ToString('d', [Globalization.CultureInfo]::CurrentCulture)
                    }
                    else {
                        ''
                    })
                $values.Add($row)
            }
            $ui.GBList.ItemsSource = $values.ToArray()
            $ui.GBPrevious.IsEnabled = ($result.page -gt 1)
            $ui.GBNext.IsEnabled = [bool]$result.has_next
            $ui.GBResults.Text = if (!$values.Count) {
                (L 'Keine Ergebnisse. Anderen Suchbegriff versuchen.')
            }
            else {
                ((L 'Seite {0} · {1} Ergebnisse{2}') -f $result.page, $result.total, $(if ($result.ordering -eq 'relevance') {
                        (L ' · Relevanz (Kategorie/Sortierung nicht angewendet)')
                    }
                    else {
                        ''
                    }))
            }
            $script:gbImageSeen = @{}
        }
        'detail' {
            Show-GBDetail $result
        }
        'link' {
            if ($result.mode -eq 'queued') {
                Show-Workspace 'Downloads'
                Start-Transfers
                Start-Net 'status' @{} 'status'
                Set-Status (L 'Verlinkte Datei wird heruntergeladen. Installation anschließend prüfen.')
            }
            else {
                Show-Workspace 'Discover'
                Start-Net 'detail' @{model =$result.model
                    id                     =$result.id
                } 'detail'
            }
        }
        'image' {
            if ($op.Payload.full) {
                Accept-FullImage $op $result
            }
            elseif ($op.Tag -is [OpenSmash.BrowserRow]) {
                $op.Tag.Thumbnail = $result.path
            }
            elseif ($script:gbDetail -and $script:gbDetail.id -eq $op.Tag) {
                $ui.GBImage.Source = $result.path
            }
        }
        'enqueue' {
            $ui.GBFileHint.Text = (L 'Download eingereiht. Prüfung und Installation folgen separat.')
            Start-Transfers
            Start-Net 'status' @{} 'status'
            if ($script:gbBatchTotal) {
                Next-GBVariant
            }
        }
        'status' {
            Show-DownloadState $result
        }
        'control' {
            Start-Transfers
            Start-Net 'status' @{} 'status'
        }
        'updates' {
            Show-Workspace 'Library'
            $lines = @($result.items | ForEach-Object { $_.name + ' — ' + $_.status + "`r`n" + $_.message + "`r`n" + $_.source_url })
            Show-Detail 'GameBanana-Updates' (L 'Dateien und Anbieterprüfsummen verglichen; keine automatische Installation.') $(if ($lines.Count) {
                    $lines -join "`r`n`r`n"
                }
                else {
                    (L 'Keine Mods mit GameBanana-Herkunft installiert. Manuell importierte Mods erhalten keine erfundene Zuordnung.')
                })
            Add-Activity (L 'GameBanana-Updateprüfung abgeschlossen.')
        }
        'preview' {
            Apply-DownloadPreview $result
        }
    }
}
function Set-GBSort {
    if (!$script:gbConfig -or !$ui.GBCategory.SelectedItem) {
        return
    }
    $script:gbChanging = $true
    $labels = @{newest =(L 'Neueste')
        updated        =(L 'Zuletzt aktualisiert')
        downloads      =(L 'Downloads')
        likes          ='Likes'
    }
    $model = $ui.GBCategory.SelectedItem.model
    $ui.GBSort.ItemsSource = @($script:gbConfig.sorts.$model | ForEach-Object { [pscustomobject]@{key =$_
                label                                                                                 =$labels[$_]
            } })
    $ui.GBSort.SelectedIndex = 0
    $script:gbChanging = $false
}
function Apply-DownloadPreview($result) {
    Show-Workspace 'Library'
    $script:preview = $result
    $script:batchJob = $result.job_id
    Set-BatchRows $result.items
    $ui.BatchSummary.Text = ((L '{0} erkannt · {1} bereit · Konflikte vor Installation entscheiden') -f $result.total, $result.ready)
    $ui.PreviewSummary.Text = $result.ready.ToString() + (L ' Mods bereit')
    $ui.InstallButton.Content = $result.ready.ToString() + (L ' Mods installieren')
    Set-Busy $script:busy
    Set-Status (L 'Downloads geprüft. Importliste und Konflikte prüfen, dann Installation bestätigen.')
}
function Configure-Conflict([string]$choice) {
    if ($script:busy -or !$script:preview -or !$ui.BatchList.SelectedItem) {
        return
    }
    $item = $ui.BatchList.SelectedItem
    if ($item.Raw.status -notin @('ready', 'conflict')) {
        return
    }
    if ($choice -in @('overlay', 'underlay')) {
        $answer = [System.Windows.MessageBox]::Show($window, ((L 'Nur gleiche Asset-Dateien werden ueberlagert. Die vorhandene Basismod und ihre Gameplay-Plugins bleiben aktiv. Bitte nur fuer einen passenden Skin oder Patch verwenden.') + "`n" + $item.Raw.message), (L 'Als Skin/Patch ueberlagern'), 'OKCancel', 'Question')
        if ($answer -ne 'OK') { return }
    }
    if ($choice -eq 'replace') {
        $answer = [System.Windows.MessageBox]::Show($window, ((L 'Diese Konfliktpartner werden pausiert: ') + ($item.Raw.message) + ("`n" + (L 'Die neue Mod wird aktiviert. Rückgängig bleibt möglich.'))), (L 'Konfliktpartner ersetzen'), 'OKCancel', 'Question')
        if ($answer -ne 'OK') {
            return
        }
    }
    $choices = @{}
    $choices[$item.ItemId] = $choice
    Begin-Operation 'batch-configure' @('--job', $script:preview.job_id, '--token', $script:preview.token, '--stdin') @{choices = $choices }
}
function Set-OperationProgress($event, $op) {
    $phase = switch ($event.phase) {
        'plugin_prepare' {
            (L 'Plugin-Übersetzung erforderlich. Das kann mehrere Minuten dauern.')
        } 'loader_prepare' {
            (L 'Erste Loader-Einrichtung erforderlich. Das kann mehrere Minuten dauern.')
        } 'deploy_prepare' {
            (L 'Betroffene Profildateien vorbereiten')
        } 'refresh' {
            (L 'Prüfsummen vollständig prüfen')
        } default {
            ''
        }
    }
    if ($phase) {
        $op.Message = $phase
        Set-Status ($phase + ' ' + $event.name)
    }
}
$selectionTimer = New-Object System.Windows.Threading.DispatcherTimer
$selectionTimer.Interval = [TimeSpan]::FromMilliseconds(170)
$selectionTimer.add_Tick({ $selectionTimer.Stop()
        if (!$script:busy -and $script:pendingChanges.Count) {
            $values = $script:pendingChanges
            $script:pendingChanges = @{}
            Begin-Operation 'change-set' @('--stdin') @{values = $values }
        } })
$ui.BulkButton.add_Click({ if (!$script:busy -and !$ReadOnlySession) {
            $visible = @($ui.ModsList.Items)
            $enable = (@($visible | Where-Object { !$_.Active }).Count -gt 0)
            $values = @{}
            foreach ($row in $visible) {
                $values[$row.Id] = $enable
            }
            if ($values.Count) {
                Begin-Operation 'change-set' @('--stdin') @{values = $values }
            }
        } })
$ui.OperationCancel.add_Click({ if ($script:operationToken) {
            [IO.File]::WriteAllText((Join-Path $Repo ('opensmash_mods\incoming\operation-' + $script:operationToken + '.cancel')), 'cancel')
            $script:cancelRequested = $true
            $ui.OperationCancel.IsEnabled = $false
            Set-Status (L 'Abbruch angefordert. Ein Profilwechsel wird sicher beendet.') 'warning'
        } })
$ui.RefreshButton.add_Click({ if (!$script:busy) {
            Begin-Operation 'refresh'
        } })
$ui.ConflictDisabled.add_Click({ Configure-Conflict 'disabled' })
$ui.ConflictReplace.add_Click({ Configure-Conflict 'replace' })
$ui.ConflictOverlay.add_Click({ Configure-Conflict 'overlay' })
$ui.ConflictUnderlay.add_Click({ Configure-Conflict 'underlay' })
$ui.BatchList.add_SelectionChanged({ Update-ImportActions })
$ui.DQList.add_SelectionChanged({ Update-DownloadActions })
$ui.LibraryNav.add_Click({ Show-Workspace 'Library' })
$ui.DiscoverNav.add_Click({ Show-Workspace 'Discover' })
$ui.DownloadsNav.add_Click({ Show-Workspace 'Downloads' })
$ui.UpdatesButton.add_Click({ Start-Net 'updates' @{} 'updates'
        Set-Status (L 'GameBanana-Dateiversionen werden geprüft…') })
$gbSearchTimer = New-Object System.Windows.Threading.DispatcherTimer
$gbSearchTimer.Interval = [TimeSpan]::FromMilliseconds(350)
$gbSearchTimer.add_Tick({ $gbSearchTimer.Stop()
        Search-GameBanana $true })
$ui.GBSearch.add_TextChanged({ if (!$script:gbChanging) {
            $gbSearchTimer.Stop()
            $gbSearchTimer.Start()
        } })
$ui.GBReload.add_Click({ Search-GameBanana $true })
$ui.GBCategory.add_SelectionChanged({ if (!$script:gbChanging) {
            $script:gbChanging = $true
            if ($ui.GBCategory.SelectedItem.id -ne $script:gbConfig.skin_category) {
                $ui.GBCharacter.SelectedIndex = 0
            }
            $ui.GBCharacter.Visibility = if ($ui.GBCategory.SelectedItem.model -eq 'Mod' -and $ui.GBCategory.SelectedItem.id -in @(0, $script:gbConfig.skin_category)) {
                'Visible'
            }
            else {
                'Collapsed'
            }
            $script:gbChanging = $false
            Set-GBSort
            Search-GameBanana $true
        } })
$ui.GBCharacter.add_SelectionChanged({ if (!$script:gbChanging -and $script:gbConfig) {
            $gbSearchTimer.Stop()
            $script:gbChanging = $true
            if ($ui.GBCharacter.SelectedItem.id -gt 0) {
                $ui.GBSearch.Clear()
                $ui.GBCategory.SelectedItem = @($ui.GBCategory.Items | Where-Object { $_.id -eq $script:gbConfig.skin_category -and $_.model -eq 'Mod' })[0]
            }
            $script:gbChanging = $false
            Set-GBSort
            Search-GameBanana $true
        } })
$ui.GBSort.add_SelectionChanged({ if (!$script:gbChanging) {
            Search-GameBanana $true
        } })
$ui.GBPrevious.add_Click({ if ($script:gbPage -gt 1) {
            $script:gbPage--
            Search-GameBanana
        } })
$ui.GBNext.add_Click({ $script:gbPage++
        Search-GameBanana })
$ui.GBList.add_SelectionChanged({
        $ui.GBChoose.Visibility = if ($ui.GBList.SelectedItems.Count -gt 1) { 'Visible' }else { 'Collapsed' }
        if ($ui.GBList.SelectedItem -and !$script:gbBatchTotal) {
            $row = $ui.GBList.SelectedItem
            $ui.GBTitle.Text = (L 'Details werden geladen…')
            $ui.GBFiles.ItemsSource = $null
            $ui.GBSource.IsEnabled = $false
            Start-Net 'detail' @{model =$row.Model
                id                     =$row.Id
            } 'detail'
        } })
$ui.GBChoose.add_Click({ $script:gbBatch = @($ui.GBList.SelectedItems)
        $script:gbBatchTotal = $script:gbBatch.Count
        if ($script:gbBatchTotal) {
            Next-GBVariant
        } })
$ui.GBFiles.add_SelectionChanged({ $f = $ui.GBFiles.SelectedItem
        $ui.GBQueue.IsEnabled = (!$ReadOnlySession -and $null -ne $f -and ([bool]$f.Raw.supported -or [bool]$f.Raw.downloadable))
        $ui.CopyLinkButton.IsEnabled = ($null -ne $f -and [bool]$f.Raw.supported)
        $ui.GBFileHint.Text = if ($f) {
            ($f.Raw.description + ' ' + $f.Raw.reason).Trim()
        }
        else {
            (L 'Keine Variante vorausgewählt.')
        } })
$ui.GBQueue.add_Click({ if ($ui.GBQueue.IsEnabled -and $script:gbDetail) {
            $ui.GBQueue.IsEnabled = $false
            Start-Net 'enqueue' @{model =$script:gbDetail.model
                id                      =$script:gbDetail.id
                file_id                 =$ui.GBFiles.SelectedItem.Raw.id
            } 'enqueue'
        } })
$ui.GBSkip.add_Click({ Next-GBVariant })
$ui.CopyLinkButton.add_Click({
        if (!$script:gbDetail -or !$ui.GBFiles.SelectedItem) {
            return
        }
        $file = $ui.GBFiles.SelectedItem.Raw
        $extension = [IO.Path]::GetExtension($file.name).TrimStart('.').ToLowerInvariant()
        $link = ('opensmashmm:https://gamebanana.com/mmdl/{0},{1},{2},{3}' -f $file.id, $script:gbDetail.model, $script:gbDetail.id, $extension)
        [System.Windows.Clipboard]::SetText($link)
        Set-Status (L 'Manager-Link zur gewählten Datei kopiert.')
    })
$ui.OpenLinkButton.add_Click({ Show-LinkDialog })
$ui.GBSource.add_Click({ if ($script:gbDetail) {
            $url = $script:gbDetail.source_url
            if ($url -match '^https://gamebanana\.com/(mods|sounds)/[0-9]+$') {
                Start-Process $url
            }
        } })
$ui.GBFullImage.add_Click({ Show-FullImage })
$ui.GBImagePrevious.add_Click({ if ($script:gbDetail -and $script:gbGallery -gt 0) {
            $script:gbGallery--
            Show-GBImage
        } })
$ui.GBImageNext.add_Click({ if ($script:gbDetail -and $script:gbGallery + 1 -lt @($script:gbDetail.images).Count) {
            $script:gbGallery++
            Show-GBImage
        } })

$ui.DQCancel.add_Click({ foreach ($row in @($ui.DQList.SelectedItems)) {
            Start-Net 'control' @{id =$row.id
                action               ='cancel'
            } ('control-' + $row.id)
        } })
$ui.DQRemove.add_Click({ $ids = @($ui.DQList.SelectedItems | ForEach-Object { $_.id }); if ($ui.DQRemove.IsEnabled -and $ids.Count) { Start-Net 'remove' @{ids = $ids } 'remove'; Update-DownloadActions } })
function Confirm-ClearDownloads {
    $dialog = [Windows.Window]::new(); $dialog.Owner = $window
    Initialize-DialogAppearance $dialog
    $dialog.Title = L 'Alle Downloads löschen'
    $dialog.FontFamily = $window.FontFamily; $dialog.FontSize = $window.FontSize
    $dialog.Width = 520; $dialog.MinHeight = 190; $dialog.SizeToContent = 'Height'; $dialog.ResizeMode = 'NoResize'; $dialog.WindowStartupLocation = 'CenterOwner'
    $panel = [Windows.Controls.DockPanel]::new(); $panel.Margin = [Windows.Thickness]::new(22); $dialog.Content = $panel
    $actions = [Windows.Controls.StackPanel]::new(); $actions.Orientation = 'Horizontal'; $actions.HorizontalAlignment = 'Right'
    [Windows.Controls.DockPanel]::SetDock($actions, 'Bottom'); $panel.Children.Add($actions) | Out-Null
    $cancel = [Windows.Controls.Button]::new(); $cancel.Content = L 'Abbrechen'; $cancel.IsCancel = $true; $cancel.Margin = [Windows.Thickness]::new(0, 0, 8, 0)
    $yes = [Windows.Controls.Button]::new(); $yes.Content = L 'Alle löschen'; $yes.Style = $window.Resources['DangerButton']
    $actions.Children.Add($cancel) | Out-Null; $actions.Children.Add($yes) | Out-Null
    $text = [Windows.Controls.TextBlock]::new(); $text.TextWrapping = 'Wrap'; $text.Text = L 'Alle Download-Einträge und gespeicherten Archive löschen? Laufende Downloads werden abgebrochen. Installierte Mods bleiben erhalten.'
    $text.Margin = [Windows.Thickness]::new(0, 0, 0, 20); $panel.Children.Add($text) | Out-Null
    $cancel.add_Click({ $dialog.DialogResult = $false }); $yes.add_Click({ $dialog.DialogResult = $true })
    return $dialog.ShowDialog()
}
$ui.DQClear.add_Click({ if ($ui.DQClear.IsEnabled -and (Confirm-ClearDownloads)) { Start-Net 'clear' @{} 'clear'; Update-DownloadActions } })
$ui.DQSave.add_Click({
        $row = $ui.DQList.SelectedItem
        if (!$ui.DQSave.IsEnabled -or !$row) { return }
        $dialog = [Microsoft.Win32.SaveFileDialog]::new(); $dialog.Title = L 'Datei speichern'
        $dialog.FileName = [IO.Path]::GetFileName([string]$row.Raw.file.name); $dialog.Filter = 'Alle Dateien (*.*)|*.*'
        if ($dialog.ShowDialog($window)) { Start-Net 'save' @{id = $row.Id; destination = $dialog.FileName } 'save'; Update-DownloadActions }
    })
$ui.DQRetry.add_Click({ foreach ($row in @($ui.DQList.SelectedItems)) {
            Start-Net 'control' @{id =$row.id
                action               ='retry'
            } ('control-' + $row.id)
        } })
$ui.DQInspect.add_Click({ if ($script:busy -or $ReadOnlySession) {
            return
        }
        $ids = @($ui.DQList.SelectedItems | Where-Object { $_.status -eq 'downloaded' -and $_.Raw.compatibility -ne 'DownloadOnly' } | ForEach-Object { $_.id })
        if ($ids.Count) {
            Show-Workspace 'Library'
            Begin-Operation 'download-preview' @('--stdin') @{ids = $ids }
        } })
$netTimer = New-Object System.Windows.Threading.DispatcherTimer
$netTimer.Interval = [TimeSpan]::FromMilliseconds(100)
$netTimer.add_Tick({
        foreach ($incoming in [OpenSmash.LinkInbox]::Drain()) {
            if ($script:pendingLinks.Count -lt 32) {
                $script:pendingLinks.Enqueue($incoming)
            }
        }
        if ($ReadOnlySession) {
            $script:pendingLinks.Clear()
        }
        if (!$ReadOnlySession -and $script:state -and !$script:busy -and !$script:netJobs.ContainsKey('link') -and $script:pendingLinks.Count) {
            if ($script:pictureViewer) {
                $script:pictureViewer.Window.Close()
            }
            if ($window.WindowState -eq 'Minimized') {
                $window.WindowState = 'Normal'
            }
            $window.Activate() | Out-Null
            Set-Status (L 'GameBanana-Link wird geprüft…')
            Start-Net 'link' @{url = $script:pendingLinks.Dequeue() } 'link'
        }
        foreach ($lane in @($script:netJobs.Keys)) {
            $op = $script:netJobs[$lane]
            foreach ($line in $op.Job.Drain()) {
                try {
                    $data = $line | ConvertFrom-Json
                    if ($data.event -eq 'library-image') { Accept-LibraryImage $data }
                    Localize-Result $data
                    if (!$data.event) {
                        $op.Result = $data
                    }
                }
                catch {
                    $op.Noise = $line
                }
            }
            if (!$op.Job.Process.HasExited -or !$op.Job.OutputComplete -or !$op.Job.Error.IsCompleted -or $op.Job.PendingLines) {
                continue
            }
            $script:netJobs.Remove($lane)
            try {
                if (!$op.Result -or !$op.Result.ok) {
                    throw $(if ($op.Result) {
                            [string]$op.Result.error
                        }
                        else {
                            (L 'Netzwerk-Worker: ') + $op.Job.Error.Result + ' ' + $op.Noise
                        })
                }
                Accept-NetResult $op $op.Result.result
            }
            catch {
                $errorText = $_.Exception.Message
                if ($op.Payload.full -and $script:pictureViewer -and $script:pictureViewer.Request -eq $op.Tag) {
                    $script:pictureViewer.Status.Text = $errorText
                }
                if ($op.Action -ne 'image') {
                    $ui.GBResults.Text = $errorText
                    $ui.DQSummary.Text = $errorText
                    Add-Activity $errorText 'warning'
                }
                if ($op.Action -eq 'link') {
                    Show-Workspace 'Downloads'
                    $ui.DQSummary.Text = $errorText
                    Set-Status (L 'GameBanana-Link konnte nicht geöffnet werden.')
                }
                if ($op.Action -eq 'config') {
                    $script:gbLoaded = $false
                }
                if ($op.Action -eq 'enqueue') {
                    $ui.GBFileHint.Text = $errorText
                    $ui.GBQueue.IsEnabled = (!$ReadOnlySession -and $null -ne $ui.GBFiles.SelectedItem -and ($ui.GBFiles.SelectedItem.Raw.supported -or $ui.GBFiles.SelectedItem.Raw.downloadable))
                }
            }
            finally {
                $op.Job.Dispose()
            }
        }
        $hasTransfers = @($script:dqJobs | Where-Object { $_.status -in @('queued', 'downloading', 'verifying') }).Count -gt 0
        $pollSeconds = if ($hasTransfers) { 1 }else { 5 }
        if (($script:workspace -eq 'Downloads' -or $hasTransfers) -and ([datetime]::Now - $script:dqLast).TotalSeconds -ge $pollSeconds) {
            $script:dqLast = [datetime]::Now
            Start-Net 'status' @{} 'status'
        }
        if ($script:workspace -eq 'Discover' -and !$script:netJobs.ContainsKey('thumb')) {
            foreach ($row in @($ui.GBList.Items)) {
                $container = $ui.GBList.ItemContainerGenerator.ContainerFromItem($row)
                if ($container -and $container.IsVisible -and $row.ImageUrl -and !$script:gbImageSeen.ContainsKey($row.ImageUrl)) {
                    $script:gbImageSeen[$row.ImageUrl] = $true
                    Start-Net 'image' @{url = $row.ImageUrl } 'thumb' $row
                    break
                }
            }
        }
    })
$netTimer.Start()
$window.add_Closed({ if ($script:pictureViewer) {
            $script:pictureViewer.Window.Close()
        }
        $netTimer.Stop()
        $gbSearchTimer.Stop()
        $selectionTimer.Stop()
        foreach ($op in @($script:netJobs.Values)) {
            try {
                if ($op.Action -notin @('run', 'preview') -and !$op.Job.Process.HasExited) {
                    $op.Job.Process.Kill()
                }
            }
            catch {
            }
            $op.Job.Dispose()
        } })
Show-Workspace 'Library'
