function Get-ThemePalette([bool]$dark) {
    if ($dark) {
        return @{
            PopupSurface    ='#203746'
            WindowSurface   ='#111D27'
            ContentSurface  ='#1C303E'
            Text            ='#E9F6FA'
            SecondaryText   ='#BED2DC'
            Accent          ='#58D9ED'
            OnAccent        ='#10313D'
            ControlSurface  ='#263E4D'
            ControlBorder   ='#79ABB9'
            PanelBorder     ='#628A9B'
            SoftSurface     ='#2B4553'
            SelectedSurface ='#254F51'
            SelectionBorder ='#7ED4C0'
            Success         ='#B5EBB6'
            Danger          ='#FFAABC'
            Warning         ='#F0CE8E'
            GlassSurface    ='#1C303E'
            GlassEdge       ='#6C9BAB'
            HoverTint       ='#53D1E4'
            BrandSurface    ='#34C5EB'
            ImportSurface   ='#1C303E'
            PlaySurface     ='#497C3B'
            PlayText        ='#F0FFE8'
            RowSurface      ='#293F4C'
            SuccessSurface  ='#294E3C'
            DangerSurface   ='#572D3D'
            WarningSurface  ='#52442B'
            InfoSurface     ='#254654'
            Separator       ='#6E97A6'
            DropLight       ='#A5E77C'
        }
    }
    return @{
        PopupSurface    ='#F3FBFE'
        WindowSurface   ='#EAF9FF'
        ContentSurface  ='#F5FCFE'
        Text            ='#0D323C'
        SecondaryText   ='#1A3943'
        Accent          ='#58D9ED'
        OnAccent        ='#123F4C'
        ControlSurface  ='#FFFFFF'
        ControlBorder   ='#5A8E9B'
        PanelBorder     ='#BCDDE4'
        SoftSurface     ='#ECF9FA'
        SelectedSurface ='#DFF7E8'
        SelectionBorder ='#3B8F83'
        Success         ='#24643F'
        Danger          ='#9F2844'
        Warning         ='#7A4B11'
        GlassSurface    ='#F1FCFF'
        GlassEdge       ='#FFFFFF'
        HoverTint       ='#34C5EB'
        BrandSurface    ='#34C5EB'
        ImportSurface   ='#F1FCFF'
        PlaySurface     ='#B8ED75'
        PlayText        ='#204B32'
        RowSurface      ='#FFFFFF'
        SuccessSurface  ='#D6F4D8'
        DangerSurface   ='#FFF0F4'
        WarningSurface  ='#FFF3D5'
        InfoSurface     ='#DDF7FC'
        Separator       ='#B6D9DF'
        DropLight       ='#86D96C'
    }
}
function Gradient($stops) {
    $brush = New-Object System.Windows.Media.LinearGradientBrush
    $brush.StartPoint = New-Object System.Windows.Point(0, 0)
    $brush.EndPoint = New-Object System.Windows.Point(0, 1)
    foreach ($stop in $stops) {
        $brush.GradientStops.Add((New-Object System.Windows.Media.GradientStop ([System.Windows.Media.ColorConverter]::ConvertFromString($stop[0]), [double]$stop[1])))
    }
    $brush.Freeze()
    return $brush
}
function Set-ButtonMaterials {
    if ($script:highContrast) {
        Set-Resource 'ActionButtonSurface' $window.Resources['Accent']
        Set-Resource 'ButtonSurface' $window.Resources['ControlSurface']
        Set-Resource 'ButtonDepth' $window.Resources['ControlBorder']
        Set-Resource 'ButtonBevel' ([System.Windows.Media.Brushes]::Transparent)
    }
    elseif ($script:dark) {
        Set-Resource 'ActionButtonSurface' (Gradient @(@('#4F733D', 0), @('#456637', 0.48), @('#354F2A', 1)))
        Set-Resource 'ButtonSurface' (Gradient @(@('#3E6173', 0), @('#2A4858', 0.48), @('#203644', 1)))
        Set-Resource 'ButtonDepth' (Brush '#0A1720')
        Set-Resource 'ButtonBevel' (Gradient @(@('#14FFFFFF', 0), @('#04FFFFFF', 0.49), @('#00FFFFFF', 0.51), @('#40031420', 1)))
    }
    else {
        Set-Resource 'ActionButtonSurface' (Gradient @(@('#F0FFCF', 0), @('#C9EF94', 0.48), @('#A9DA69', 1)))
        Set-Resource 'ButtonSurface' (Gradient @(@('#F4FDFF', 0), @('#D6F5FA', 0.48), @('#B8E3EC', 1)))
        Set-Resource 'ButtonDepth' (Brush '#608F9B')
        Set-Resource 'ButtonBevel' (Gradient @(@('#B3FFFFFF', 0), @('#14FFFFFF', 0.49), @('#00FFFFFF', 0.51), @('#240B5565', 1)))
    }
}
function Apply-Theme {
    if ($VisualTestTheme -eq 'Dark') {
        $script:dark = $true
    }
    elseif ($VisualTestTheme -eq 'Light') {
        $script:dark = $false
    }
    else {
        $script:dark = ($script:themeChoice -eq 'Dark' -or ($script:themeChoice -eq 'System' -and [OpenSmash.UiNative]::DarkTheme))
    }
    if (!$script:highContrast) {
        $colors = Get-ThemePalette $script:dark
        foreach ($key in $colors.Keys) {
            Set-Resource $key (Brush $colors[$key])
        }
    }
    Set-ButtonMaterials
    $status = switch ($script:statusKind) {
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
    $detail = switch ($script:detailKind) {
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
    $surface = switch ($script:detailKind) {
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
    $ui.StatusSymbol.Foreground = $window.Resources[$status]
    $ui.DetailBadgeText.Foreground = $window.Resources[$detail]
    $ui.DetailBadge.Background = $window.Resources[$surface]
    foreach ($menu in @($script:glassMenu, $ui.MoreMenu)) {
        if (!$menu) {
            continue
        }
        $menu.Background = $window.Resources['PopupSurface']
        $menu.Foreground = $window.Resources['Text']
        foreach ($key in @('ControlBorder', 'SelectedSurface', 'Text', 'SecondaryText', 'PopupSurface')) {
            $menu.Resources[$key] = $window.Resources[$key]
        }
        foreach ($entry in $menu.Items) {
            if ($entry -is [System.Windows.Controls.MenuItem]) {
                $entry.Foreground = $window.Resources['Text']
            }
        }
    }
    Apply-Glass
}
