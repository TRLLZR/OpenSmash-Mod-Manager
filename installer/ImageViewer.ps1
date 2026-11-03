function Show-FullImage {
    if (!$script:gbDetail -or !@($script:gbDetail.images).Count) {
        return
    }
    if ($script:pictureViewer) {
        $script:pictureViewer.Window.Close()
    }
    $viewer = New-Object System.Windows.Window
    $viewer.Title = $script:gbDetail.title + (L ' – Bilder')
    $viewer.Owner = $window
    $viewer.WindowStyle = 'None'
    $viewer.ResizeMode = 'NoResize'
    $viewer.WindowState = 'Maximized'
    $viewer.ShowInTaskbar = $false
    $viewer.Background = Brush '#101821'
    $viewer.Foreground = Brush '#F0F7FA'
    $viewer.FontFamily = $window.FontFamily
    $viewer.FontSize = 14
    Initialize-DialogAppearance $viewer
    $viewer.Background = Brush '#101821'
    $viewer.Foreground = Brush '#F0F7FA'
    foreach ($pair in @(@('ControlBorder', '#7795A4'), @('Accent', '#58D9ED'), @('SoftSurface', '#263D4A'), @('SelectedSurface', '#254F51'))) {
        $viewer.Resources.Add($pair[0], (Brush $pair[1]))
    }
    $grid = New-Object System.Windows.Controls.Grid
    $grid.Margin = New-Object System.Windows.Thickness(22)
    $viewer.Content = $grid
    foreach ($height in @('Auto', '*', 'Auto')) {
        $row = New-Object System.Windows.Controls.RowDefinition
        $row.Height = [System.Windows.GridLengthConverter]::new().ConvertFromString($height)
        $grid.RowDefinitions.Add($row)
    }
    $header = New-Object System.Windows.Controls.DockPanel
    $header.Margin = New-Object System.Windows.Thickness(0, 0, 0, 14)
    $grid.Children.Add($header) | Out-Null
    $close = New-Object System.Windows.Controls.Button
    $close.Content = (L 'Schließen (Esc)')
    $close.Style = $window.Resources['QuietButton']
    [System.Windows.Controls.DockPanel]::SetDock($close, 'Right')
    $header.Children.Add($close) | Out-Null
    $title = New-Object System.Windows.Controls.TextBlock
    $title.Text = $script:gbDetail.title
    $title.FontSize = 18
    $title.FontWeight = 'SemiBold'
    $title.TextTrimming = 'CharacterEllipsis'
    $title.Margin = New-Object System.Windows.Thickness(0, 5, 18, 0)
    $header.Children.Add($title) | Out-Null
    $image = New-Object System.Windows.Controls.Image
    $image.Stretch = 'Uniform'
    [System.Windows.Controls.Grid]::SetRow($image, 1)
    $grid.Children.Add($image) | Out-Null
    $status = New-Object System.Windows.Controls.TextBlock
    $status.Foreground = $viewer.Foreground
    $status.HorizontalAlignment = 'Center'
    $status.VerticalAlignment = 'Center'
    $status.TextWrapping = 'Wrap'
    [System.Windows.Controls.Grid]::SetRow($status, 1)
    $grid.Children.Add($status) | Out-Null
    $footer = New-Object System.Windows.Controls.StackPanel
    $footer.Orientation = 'Horizontal'
    $footer.HorizontalAlignment = 'Center'
    $footer.Margin = New-Object System.Windows.Thickness(0, 14, 0, 0)
    [System.Windows.Controls.Grid]::SetRow($footer, 2)
    $grid.Children.Add($footer) | Out-Null
    $previous = New-Object System.Windows.Controls.Button
    $previous.Content = (L '‹ Zurück')
    $previous.Style = $window.Resources['QuietButton']
    $footer.Children.Add($previous) | Out-Null
    $counter = New-Object System.Windows.Controls.TextBlock
    $counter.Margin = New-Object System.Windows.Thickness(20, 8, 20, 0)
    $footer.Children.Add($counter) | Out-Null
    $next = New-Object System.Windows.Controls.Button
    $next.Content = (L 'Weiter ›')
    $next.Style = $previous.Style
    $footer.Children.Add($next) | Out-Null
    $script:pictureViewer = @{Window =$viewer
        Image                        =$image
        Status                       =$status
        Counter                      =$counter
        Previous                     =$previous
        Next                         =$next
        Urls                         =@($script:gbDetail.images)
        Index                        =$script:gbGallery
        Request                      =''
    }
    $close.add_Click({ if ($script:pictureViewer) {
                $script:pictureViewer.Window.Close()
            } })
    $previous.add_Click({ Step-FullImage -1 })
    $next.add_Click({ Step-FullImage 1 })
    $viewer.add_KeyDown({ if ($_.Key -in @('Escape', 'F11')) {
                $script:pictureViewer.Window.Close()
                $_.Handled = $true
            }
            elseif ($_.Key -eq 'Left') {
                Step-FullImage -1
                $_.Handled = $true
            }
            elseif ($_.Key -eq 'Right') {
                Step-FullImage 1
                $_.Handled = $true
            } })
    $viewer.add_Closed({ $script:pictureViewer = $null })
    $viewer.Show()
    $viewer.Activate() | Out-Null
    Load-FullImage
}
function Step-FullImage([int]$offset) {
    if (!$script:pictureViewer) {
        return
    }
    $index = $script:pictureViewer.Index + $offset
    if ($index -lt 0 -or $index -ge $script:pictureViewer.Urls.Count) {
        return
    }
    $script:pictureViewer.Index = $index
    Load-FullImage
}
function Load-FullImage {
    $view = $script:pictureViewer
    if (!$view) {
        return
    }
    $view.Image.Source = $null
    $view.Status.Text = (L 'Originalbild wird geladen…')
    $view.Status.Visibility = 'Visible'
    $view.Counter.Text = ('{0} / {1}' -f ($view.Index + 1), $view.Urls.Count)
    $view.Previous.IsEnabled = ($view.Index -gt 0)
    $view.Next.IsEnabled = ($view.Index + 1 -lt $view.Urls.Count)
    $view.Request = [guid]::NewGuid().ToString('N')
    Start-Net 'image' @{url =$view.Urls[$view.Index]
        full                =$true
    } 'full-image' $view.Request
}
function Accept-FullImage($op, $result) {
    $view = $script:pictureViewer
    if (!$view -or $view.Request -ne $op.Tag) {
        return
    }
    $bitmap = New-Object System.Windows.Media.Imaging.BitmapImage
    $bitmap.BeginInit()
    $bitmap.CacheOption = 'OnLoad'
    $bitmap.UriSource = [uri]::new($result.path, [UriKind]::Absolute)
    $bitmap.EndInit()
    $bitmap.Freeze()
    $view.Image.Source = $bitmap
    $view.Status.Visibility = 'Collapsed'
}
