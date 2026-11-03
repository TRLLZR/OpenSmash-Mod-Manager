param([string]$Source, [string]$Repo, [string]$Sources, [string]$Report)
$ErrorActionPreference = 'Stop'
$script:testReport = $Report; $script:testSources = [string[]]([IO.File]::ReadAllText($Sources) | ConvertFrom-Json)
$hook = @'
$script:testStage=0;$script:testChecks=@();$script:testDeadline=[datetime]::Now.AddSeconds(75)
function Check($ok,$label){if(!$ok){throw $label};$script:testChecks+=@($label)}
function Save-UiProof($visual,$suffix){
 $visual.UpdateLayout()
 $bitmap=[Windows.Media.Imaging.RenderTargetBitmap]::new([int]$visual.ActualWidth,[int]$visual.ActualHeight,96,96,[Windows.Media.PixelFormats]::Pbgra32);$bitmap.Render($visual)
 $encoder=[Windows.Media.Imaging.PngBitmapEncoder]::new();$encoder.Frames.Add([Windows.Media.Imaging.BitmapFrame]::Create($bitmap))
 $stream=[IO.File]::Create($script:testReport+$suffix+'.png');try{$encoder.Save($stream)}finally{$stream.Dispose()}
}
$script:testTimer=New-Object Windows.Threading.DispatcherTimer;$testTimer.Interval=[TimeSpan]::FromMilliseconds(80)
$testTimer.add_Tick({
 try{
  if([datetime]::Now -gt $script:testDeadline){throw 'Batch UI timeout'}
  if($script:busy){return}
  if($script:lastFailure){throw $ui.DetailsText.Text}
  switch($script:testStage){
   0 {
    Check ($script:rows.Count -eq 0) 'empty library ready'
    Check ($window.Background.Color.A -eq 255 -and !$script:backdrop) 'opaque client surface without desktop blur'
    Check ($null -eq $window.FindName('OnTop') -and $null -eq $window.FindName('AppTitle')) 'logo replaces duplicate title and foreground switch removed'
    Check ($ui.ExportButton -is [System.Windows.Controls.MenuItem] -and $ui.RefreshButton -is [System.Windows.Controls.MenuItem]) 'secondary actions remain accessible in More menu'
    Check ($glassMenu.Items.Count -eq 3) 'appearance menu contains only light dark and system'
    Show-HeaderMenu $ui.MoreButton $ui.MoreMenu;Check ($ui.MoreMenu.IsOpen) 'More menu opens through shared header action';$ui.MoreMenu.IsOpen=$false
    Check (!$ui.DQInspect.IsEnabled -and !$ui.DQCancel.IsEnabled -and !$ui.DQRetry.IsEnabled) 'download actions require suitable selection'
    Show-DownloadState ([pscustomobject]@{items=@([pscustomobject]@{id='own-ui-fixture';title='Own download';status='downloaded';file=[pscustomobject]@{name='own.zip'};bytes=1024;total=1024;speed=0;message='Ready';compatibility='Experimental';evidence='Own structure fixture, not gameplay verified'})})
    Check ($ui.DQList.Items[0].caption -match 'Experimentell' -and $ui.DQList.Items[0].caption -notmatch 'MB/s') 'completed downloads keep compatibility without irrelevant transfer speed'
    $ui.DQList.SelectedIndex=0
    $script:selectionEvents=0;$ui.DQList.add_SelectionChanged({$script:selectionEvents++})
    $downloadRow=$ui.DQList.SelectedItem;$source=$ui.DQList.ItemsSource
    $fixtureStatus=[pscustomobject]@{items=@($downloadRow.Raw)}
    $clock=[Diagnostics.Stopwatch]::StartNew()
    for($poll=0;$poll -lt 20;$poll++){Show-DownloadState $fixtureStatus}
    $clock.Stop();$script:downloadPollMilliseconds=$clock.Elapsed.TotalMilliseconds
    Check ([object]::ReferenceEquals($source,$ui.DQList.ItemsSource) -and [object]::ReferenceEquals($downloadRow,$ui.DQList.SelectedItem) -and $script:selectionEvents -eq 0) 'repeated download polling preserves selected row and never restarts selection'
    Check ($ui.DQRemove.IsEnabled) 'completed download can be removed'
    $ui.DQList.SelectedIndex=-1
    Check (!$ui.DQRemove.IsEnabled) 'download removal requires a selection'
    Show-DownloadState ([pscustomobject]@{items=@([pscustomobject]@{id='own-active-fixture';title='Own active download';status='downloading';file=[pscustomobject]@{name='own.zip'};bytes=0;total=1024;speed=0;message='Loading'})})
    $ui.DQList.SelectedIndex=0
    Check (!$ui.DQRemove.IsEnabled -and $ui.DQCancel.IsEnabled) 'active download cannot be removed until cancelled'
    Check ($ui.DQClear.IsEnabled -and $ui.DQClear.Template -eq $ui.PlayButton.Template) 'clear all downloads action shares standard button template'
    Show-DownloadState ([pscustomobject]@{items=@([pscustomobject]@{id='own-save-fixture';title='Own public data';status='downloaded';file=[pscustomobject]@{name='own.tar'};bytes=1024;total=1024;speed=0;message='Downloaded';compatibility='DownloadOnly';evidence='Own data'})})
    $ui.DQList.SelectedIndex=0
    Check (!$ui.DQInspect.IsEnabled -and $ui.DQSave.IsEnabled) 'download-only files can be saved without offering automatic installation'
    Show-Workspace 'Downloads';Save-UiProof $window '.downloads';Show-Workspace 'Library'
    Accept-NetResult @{Action='remove'} ([pscustomobject]@{items=@();removed=1})
    Check ($ui.DQList.Items.Count -eq 0) 'removed download result refreshes queue'


    $script:gbLoaded=$true;Show-Workspace 'Discover'
    $items=@();for($i=1;$i -le 20;$i++){$items+=@([pscustomobject]@{id=$i;model='Mod';title='Own UI fixture '+$i;author='QA';category='UI';updated=123;likes=4;downloads=$null;thumbnail=$null;installed=$false})}
    Accept-NetResult @{Action='browse'} ([pscustomobject]@{items=$items;page=1;has_next=$true;total=40;ordering='newest'})
    $script:gbBatchTotal=1;$ui.GBList.SelectedItems.Add($ui.GBList.Items[0])|Out-Null
    Check ($ui.GBChoose.Visibility -eq 'Collapsed') 'batch download action hidden for single selection'
    $ui.GBList.SelectedItems.Add($ui.GBList.Items[1])|Out-Null
    Check ($ui.GBChoose.Visibility -eq 'Visible') 'clearly named batch download action appears for multiple mods'
    $ui.GBList.SelectedItems.Clear();$script:gbBatchTotal=0
    Check ($ui.GBList.Items.Count -eq 20 -and $ui.GBNext.IsEnabled) 'native browser result bindings and pagination'
    $files=@([pscustomobject]@{id=1;name='one.zip';size=123;description='own fixture';supported=$true;reason='';archived=$false},[pscustomobject]@{id=2;name='own.tar';size=456;description='own fixture';supported=$false;downloadable=$true;reason='download only';archived=$false},[pscustomobject]@{id=3;name='blocked.zip';size=456;description='own fixture';supported=$false;downloadable=$false;reason='blocked';archived=$false})
    Show-GBDetail ([pscustomobject]@{id=1;model='Mod';title='Own fixture';author='QA';category='UI';updated=123;downloads=5;description='Plain text';dependencies='Read fixture';instructions='Choose variant';images=@();files=$files;source_url='https://gamebanana.com/mods/1'})
    Check ($ui.GBFiles.SelectedIndex -eq -1 -and !$ui.GBQueue.IsEnabled) 'explicit variant required with no automatic first file'
    $ui.GBFiles.SelectedIndex=1;Check ($ui.GBQueue.IsEnabled -and !$ui.CopyLinkButton.IsEnabled) 'public download-only variant can be queued in the manager'
    $ui.GBFiles.SelectedIndex=2;Check (!$ui.GBQueue.IsEnabled) 'provider-restricted variant remains blocked'
    $ui.GBFiles.SelectedIndex=0;Check ($ui.GBQueue.IsEnabled) 'supported variant enables queue confirmation'
    Check ($ui.CopyLinkButton.IsEnabled -and $null -ne $ui.OpenLinkButton) 'explicit variant enables own manager link and link dialog stays accessible'
    Check ($ui.GBCharacter.IsTextSearchEnabled -and $null -ne $ui.GBCharacter.ItemTemplate) 'character picker is searchable with readable provider labels'
    Check ($null -ne $ui.GBFiles.ItemTemplate -and $null -ne $ui.GBCategory.ItemTemplate) 'native combo labels use templates'
    $detail=$script:gbDetail;$detail.description=('Own long first description. '*1500)
    Show-GBDetail $detail;$window.UpdateLayout();$ui.GBDetailScroll.ScrollToVerticalOffset(400);$window.UpdateLayout()
    Check ($ui.GBDetailScroll.VerticalOffset -gt 100) 'detail scroll fixture is genuinely below the beginning'
    $detail.id=2;$detail.description=('Own different long description. '*1500)
    Show-GBDetail $detail;$window.UpdateLayout()
    Check ($ui.GBDetailScroll.VerticalOffset -eq 0) 'selecting another mod resets long details to the top'
    Show-Workspace 'Library'

    $script:glassPreset='Milk';Apply-Glass;Save-Preferences
    Check ((Read-Preferences).glass -eq 'Solid') 'legacy transparency preference migrates to opaque'
    $script:themeChoice='Dark';Apply-Theme;Save-Preferences
    Check ($script:dark -and (Read-Preferences).theme -eq 'Dark') 'dark mode applies and persists'
    Check ($window.Resources['Text'].Color.R -gt 200 -and $window.Background.Color.R -lt 60) 'dark text and surfaces have separate colors'
    $script:gbDetail.images=@('https://images.gamebanana.com/img/ss/mods/own-qa-1.png','https://images.gamebanana.com/img/ss/mods/own-qa-2.png');$script:gbGallery=0
    $ui.GBFullImage.RaiseEvent([System.Windows.RoutedEventArgs]::new([System.Windows.Controls.Primitives.ButtonBase]::ClickEvent))
    Check ($script:pictureViewer -and $script:pictureViewer.Window.WindowState -eq 'Maximized' -and $script:pictureViewer.Window.WindowStyle -eq 'None') 'detail image click opens borderless fullscreen'
    $script:testStage=90
   }
   90 {
    if(!$script:pictureViewer.Image.Source){return}
    Check ($script:pictureViewer.Image.Source.PixelWidth -eq 1600 -and !$script:pictureViewer.Previous.IsEnabled -and $script:pictureViewer.Next.IsEnabled) 'fullscreen uses original-resolution cache and bounded navigation'
    Step-FullImage 1;$script:testStage=91
   }
   91 {
    if(!$script:pictureViewer.Image.Source){return}
    Check ($script:pictureViewer.Image.Source.PixelWidth -eq 1200 -and $script:pictureViewer.Counter.Text -eq '2 / 2' -and !$script:pictureViewer.Next.IsEnabled) 'fullscreen next picture loads asynchronously'
    $viewer=$script:pictureViewer.Window
    $key=[System.Windows.Input.KeyEventArgs]::new([System.Windows.Input.Keyboard]::PrimaryDevice,[System.Windows.PresentationSource]::FromVisual($viewer),0,[System.Windows.Input.Key]::Escape);$key.RoutedEvent=[System.Windows.Input.Keyboard]::KeyDownEvent;$viewer.RaiseEvent($key)
    Check (!$script:pictureViewer -and !$viewer.IsVisible) 'escape closes fullscreen and returns to manager'
    Show-DownloadState ([pscustomobject]@{items=@([pscustomobject]@{id='own-clear-fixture';title='Own clear fixture';status='downloaded';file=[pscustomobject]@{name='own.zip'};bytes=1;total=1;speed=0;message='Ready'})})
    $script:confirmTimer=[Windows.Threading.DispatcherTimer]::new();$confirmTimer.Interval=[TimeSpan]::FromMilliseconds(60)
    $confirmTimer.add_Tick({
      foreach($dialog in $window.OwnedWindows){
        if($dialog.Title -eq 'Alle Downloads löschen'){
          $confirmTimer.Stop();$yes=$dialog.Content.Children[0].Children[1]
          Check ($yes.Content -eq 'Alle löschen' -and $yes.Style -eq $window.Resources['DangerButton']) 'clear all downloads requires the shared styled confirmation dialog'
          Save-UiProof $dialog '.clear-confirmation'
          $yes.RaiseEvent([Windows.RoutedEventArgs]::new([Windows.Controls.Primitives.ButtonBase]::ClickEvent));break
        }
      }
    })
    $script:testStage=92;$testTimer.Stop();$confirmTimer.Start()
    $ui.DQClear.RaiseEvent([Windows.RoutedEventArgs]::new([Windows.Controls.Primitives.ButtonBase]::ClickEvent));$testTimer.Start()
   }
   92 {
    if($script:netJobs.ContainsKey('clear')){return}
    Check ($ui.DQList.Items.Count -eq 0 -and !$ui.DQClear.IsEnabled) 'clear button invokes native worker and refreshes an empty queue'
    $script:testStage=1;Accept-Drops $script:testSources
   }
   1 {
    Check ($script:preview.ready -eq 2 -and $script:preview.items.Count -eq 5) 'mixed ZIP RAR 7z batch isolates invalid and duplicate'
    Check ($ui.BatchList.Items.Count -eq 5 -and $ui.InstallButton.IsEnabled) 'per-mod rows and confirmation enabled'
    $script:testStage=2;Install-Preview
   }
   2 {
    Check ($script:rows.Count -eq 2 -and $ui.BatchSummary.Text -match '2 installiert') 'two batch mods installed'
    Check ($ui.UndoButton.IsEnabled -and !$ui.BatchCancel.IsEnabled -and !$script:busy) 'undo ready and queue idle'
    $ui.SearchBox.Text='Skin A';Check ($ui.ModsList.Items.Count -eq 1) 'search after incremental update';$ui.SearchBox.Clear()
    $ui.ModsList.SelectedIndex=0;$script:testId=$ui.ModsList.SelectedItem.Id
    Check (@($script:rows | Where-Object { $null -ne $_.Thumbnail }).Count -eq 1) 'installed local cover is loaded without locking the source image'
    $ui.TileViewButton.RaiseEvent([Windows.RoutedEventArgs]::new([Windows.Controls.Primitives.ButtonBase]::ClickEvent))
    $window.UpdateLayout()
    Check ($script:libraryView -eq 'Tiles' -and (Read-Preferences).library_view -eq 'Tiles') 'tile view applies and persists'
    Check ($ui.ModsList.SelectedItem.Id -eq $script:testId -and $ui.ModsList.Items.Count -eq 2) 'tile switch preserves selection and rows'
    $ui.SearchBox.Text='Skin A';Check ($ui.ModsList.Items.Count -eq 1) 'search works in tile view';$ui.SearchBox.Clear()
    $ui.ModsList.SelectedIndex=0
    $ui.ListViewButton.RaiseEvent([Windows.RoutedEventArgs]::new([Windows.Controls.Primitives.ButtonBase]::ClickEvent))
    Check ($script:libraryView -eq 'List' -and (Read-Preferences).library_view -eq 'List' -and $ui.ModsList.SelectedItem.Id -eq $script:testId) 'list switch preserves selection and persists'
    Set-LibraryView 'Tiles'
    Check ($ui.ExportButton.IsEnabled) 'library export available'
    $script:testStage=20;Begin-Operation 'export' @('--destination',($script:testReport+'.mods.zip'))
   }
   20 {Check ((Test-Path -LiteralPath ($script:testReport+'.mods.zip')) -and $ui.DetailTitle.Text -eq 'Export abgeschlossen') 'export worker and result view';$script:testStage=21;Begin-Operation 'export-list' @('--destination',($script:testReport+'.list.json'))}
   21 {Check ((Test-Path -LiteralPath ($script:testReport+'.list.json')) -and $ui.DetailTitle.Text -eq 'Modliste gespeichert') 'lightweight list export worker and review';$script:testStage=22;Begin-Operation 'list-preview' @('--source',($script:testReport+'.list.json'))}
   22 {Check ($script:preview.kind -eq 'mod-list' -and $script:preview.existing -eq 2 -and $script:preview.ready -eq 0 -and !$ui.InstallButton.IsEnabled) 'mod list review skips installed content without downloading';$script:preview=$null;$script:testStage=3;Begin-Operation 'enable' @('--id',$script:testId,'--value','0')}
   3 {Check (!(@($script:rows|Where-Object Id -eq $script:testId)[0].Active)) 'incremental paused state';$script:testStage=4;Undo-Change}
   4 {Check (@($script:rows|Where-Object Id -eq $script:testId)[0].Active) 'undo restores paused state';$script:testStage=5;Undo-Change}
   5 {Check ($script:rows.Count -eq 0) 'single batch undo restores empty library';$script:testStage=6;Accept-Drops $script:testSources}
   6 {
    Check ($script:preview.ready -eq 2) 'second preview succeeds after undo'
    # Verify checkpoint cancellation through the real worker, not a killed process.
    $file=Join-Path $Repo ('opensmash_mods\incoming\batch-'+$script:batchJob+'\cancel.request');[IO.File]::WriteAllText($file,'cancel')
    $script:testStage=7;Install-Preview
   }
   7 {
    Check ($script:rows.Count -eq 0 -and $ui.BatchSummary.Text -match '0 installiert') 'cancelled queue leaves profile unchanged'
    Check (!$script:busy -and $ui.ZipButton.IsEnabled) 'controls recover after cancellation'
    @{ok=$true;version='3.7.0';checks=$script:testChecks;batchRows=$ui.BatchList.Items.Count;downloadPollMilliseconds=$script:downloadPollMilliseconds}|ConvertTo-Json -Depth 4|Set-Content -LiteralPath $script:testReport -Encoding UTF8
    $testTimer.Stop();$window.Close()
   }
  }
 }catch{
  @{ok=$false;stage=$script:testStage;error=$_.Exception.ToString();preview=$script:preview;checks=$script:testChecks}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $script:testReport -Encoding UTF8
  $testTimer.Stop();$window.Close()
 }
})
$window.add_ContentRendered({$testTimer.Start()})
[void]$window.ShowDialog()
'@
$text = [IO.File]::ReadAllText((Join-Path $Source 'ModManager.ps1')).Replace('[void]$window.ShowDialog()', $hook).Replace('$PSScriptRoot', ("'" + $Source.Replace("'", "''") + "'"))
& ([ScriptBlock]::Create($text)) -Repo $Repo -SafeVisuals -SettingsPath ($Report + '.settings.json')
$result = [IO.File]::ReadAllText($Report) | ConvertFrom-Json
if (!$result.ok) { throw $result.error }; $result | ConvertTo-Json -Depth 4
