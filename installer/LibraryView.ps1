# Both layouts share the same rows, search, selection and activation handlers.
$script:libraryView = $preferences.library_view
$script:coverRequested = @{}
$markup = ConvertTo-LocalizedXaml ([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'LibraryViews.xaml'), [Text.Encoding]::UTF8))
$reader = [Xml.XmlNodeReader]::new($markup)
try { $views = [Windows.Markup.XamlReader]::Load($reader) } finally { $reader.Close() }
$window.Resources.MergedDictionaries.Add($views)

function Update-TileWidth {
    if ($script:libraryView -ne 'Tiles') { return }
    $available = [math]::Max(170, $ui.ModsList.ActualWidth - 24)
    $columns = [math]::Max(1, [math]::Floor($available / 190))
    $style = [Windows.Style]::new([Windows.Controls.ListBoxItem], $window.Resources[[Windows.Controls.ListBoxItem]])
    $style.Setters.Add([Windows.Setter]::new([Windows.FrameworkElement]::WidthProperty, [double]([math]::Floor($available / $columns) - 12)))
    $style.Setters.Add([Windows.Setter]::new([Windows.FrameworkElement]::MarginProperty, [Windows.Thickness]::new(4)))
    $style.Setters.Add([Windows.Setter]::new([Windows.Controls.Control]::PaddingProperty, [Windows.Thickness]::new(6, 5, 6, 5)))
    $style.Setters.Add([Windows.Setter]::new([Windows.FrameworkElement]::VerticalAlignmentProperty, [Windows.VerticalAlignment]::Top))
    $ui.ModsList.ItemContainerStyle = $style
}

function Set-LibraryView([string]$mode) {
    $selected = $ui.ModsList.SelectedItem
    $script:libraryView = if ($mode -eq 'Tiles') { 'Tiles' } else { 'List' }
    $tiles = $script:libraryView -eq 'Tiles'
    $ui.ModsList.ItemsPanel = $window.Resources[$(if ($tiles) { 'LibraryTilePanel' } else { 'LibraryListPanel' })]
    $ui.ModsList.ItemTemplate = $window.Resources[$(if ($tiles) { 'LibraryTileView' } else { 'LibraryListView' })]
    [Windows.Controls.ScrollViewer]::SetCanContentScroll($ui.ModsList, !$tiles)
    if ($tiles) { Update-TileWidth } else { $ui.ModsList.ClearValue([Windows.Controls.ItemsControl]::ItemContainerStyleProperty) }
    foreach ($pair in @(@($ui.ListViewButton, !$tiles), @($ui.TileViewButton, $tiles))) {
        $pair[0].FontWeight = if ($pair[1]) { 'Bold' } else { 'Normal' }
        $pair[0].SetValue([Windows.Automation.AutomationProperties]::ItemStatusProperty, $(if ($pair[1]) { L 'Ausgewählt' } else { '' }))
    }
    if ($selected) { $ui.ModsList.SelectedItem = $selected; $ui.ModsList.ScrollIntoView($selected) }
}

function Accept-LibraryImage($result) {
    foreach ($row in $script:rows) {
        if ($row.Id -eq $result.id) { $row.SetPreview([string]$result.path); break }
    }
}

function Start-LibraryImages {
    if ($ReadOnlySession -or !$script:state -or $script:netJobs.ContainsKey('library-images')) { return }
    $ids = @($script:rows | Where-Object { !$script:coverRequested.ContainsKey($_.Id) } | Select-Object -First 32 | ForEach-Object { $_.Id })
    if (!$ids.Count) { return }
    foreach ($id in $ids) { $script:coverRequested[$id] = $true }
    Start-Net 'library-images' @{ids = $ids } 'library-images'
}

function Choose-Cover {
    $row = $ui.ModsList.SelectedItem
    if (!$row -or $ReadOnlySession) { return }
    $dialog = [Microsoft.Win32.OpenFileDialog]::new()
    $dialog.Title = L 'Titelbild auswählen'
    $dialog.Filter = 'Bilder (*.png;*.jpg;*.jpeg;*.webp)|*.png;*.jpg;*.jpeg;*.webp'
    if ($dialog.ShowDialog($window)) { Start-Net 'set-preview' @{id = $row.Id; source = $dialog.FileName } 'set-preview' }
}

$ui.ListViewButton.add_Click({ Set-LibraryView 'List'; Save-Preferences })
$ui.TileViewButton.add_Click({ Set-LibraryView 'Tiles'; Save-Preferences })
$ui.CoverButton.add_Click({ Choose-Cover })
$ui.ModsList.add_SizeChanged({ Update-TileWidth })
Set-LibraryView $script:libraryView
