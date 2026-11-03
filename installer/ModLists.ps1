# Lists contain provider IDs and content hashes; installation needs one explicit review.
function Export-ModList {
    if (!$ui.ExportListButton.IsEnabled) { return }
    $dialog = [Microsoft.Win32.SaveFileDialog]::new()
    $dialog.Title = L 'Modliste teilen'
    $dialog.Filter = 'OpenSmash-Modliste (*.opensmash-list.json)|*.opensmash-list.json'
    $dialog.FileName = 'OpenSmash-Modliste.opensmash-list.json'
    $dialog.AddExtension = $true; $dialog.DefaultExt = '.opensmash-list.json'
    if ($dialog.ShowDialog($window)) { Begin-Operation 'export-list' @('--destination', $dialog.FileName) }
}
function Import-ModList {
    if (!$ui.ImportListButton.IsEnabled) { return }
    $dialog = [Microsoft.Win32.OpenFileDialog]::new()
    $dialog.Title = L 'Modliste importieren'
    $dialog.Filter = 'OpenSmash-Modliste (*.json)|*.json'
    if ($dialog.ShowDialog($window)) { Show-Workspace 'Library'; Begin-Operation 'list-preview' @('--source', $dialog.FileName) }
}
$ui.ExportListButton.add_Click({ Export-ModList })
$ui.ImportListButton.add_Click({ Import-ModList })
