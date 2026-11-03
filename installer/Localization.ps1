# Localize presentation strings only. Identifiers, paths, mod titles and worker
# protocol fields always keep their original values.
function L([string]$text) {
    return [OpenSmash.Localizer]::Text($text)
}

function ConvertTo-LocalizedXaml([string]$source) {
    $document = [xml]$source
    foreach ($node in $document.SelectNodes('//*')) {
        foreach ($attribute in @($node.Attributes)) {
            if ($attribute.LocalName -in @('Text', 'Content', 'Header', 'ToolTip', 'AutomationProperties.Name') -and
                !$attribute.Value.StartsWith('{')) {
                $attribute.Value = L $attribute.Value
            }
        }
    }
    return $document
}

function Localize-Result($value) {
    if ($null -eq $value) {
        return 
    }
    if ($value -is [System.Array]) {
        foreach ($item in $value) {
            Localize-Result $item 
        }
    }
    elseif ($value -is [pscustomobject]) {
        foreach ($property in $value.PSObject.Properties) {
            if ($property.Name -in @('message', 'error', 'reason', 'evidence')) {
                if ($property.Value -is [string]) {
                    $property.Value = L $property.Value 
                }
            }
            elseif ($property.Name -in @('warnings', 'issues')) {
                $property.Value = @($property.Value | ForEach-Object { L ([string]$_) })
            }
            elseif ($property.Value -is [pscustomobject] -or $property.Value -is [System.Array]) {
                Localize-Result $property.Value
            }
        }
    }
}

function Initialize-DialogAppearance($dialog) {
    if ($script:window) {
        $dialog.Resources.MergedDictionaries.Add($script:window.Resources)
    }
    else {
        # The connection dialog opens before the main window. Reuse the same
        # trusted local templates with motion disabled, rather than a second skin.
        $markup = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'ModManager.xaml'), [Text.Encoding]::UTF8)
        $markup = [regex]::Replace($markup, '__(HOVER|PRESS|TOGGLE|PANEL|STATUS|SUCCESS)__', '0:0:0').Replace('__LIFT__', '0')
        $reader = [Xml.XmlNodeReader]::new([xml]$markup)
        try {
            $template = [Windows.Markup.XamlReader]::Load($reader) 
        }
        finally {
            $reader.Close() 
        }
        $dialog.Resources.MergedDictionaries.Add($template.Resources)
        $window = $dialog
        $colors = Get-ThemePalette ([OpenSmash.UiNative]::DarkTheme)
        if ($script:highContrast) {
            foreach ($key in @($colors.Keys)) {
                $colors[$key] = [Windows.SystemColors]::WindowColor.ToString()
            }
            foreach ($key in @('Text', 'SecondaryText', 'ControlBorder', 'PanelBorder', 'SelectionBorder')) {
                $colors[$key] = [Windows.SystemColors]::WindowTextColor.ToString()
            }
            $colors['Accent'] = [Windows.SystemColors]::HighlightColor.ToString()
            $colors['PlayText'] = [Windows.SystemColors]::HighlightTextColor.ToString()
        }
        foreach ($key in $colors.Keys) {
            $dialog.Resources[$key] = Brush $colors[$key] 
        }
        $dialog.Resources['ReflectionOpacity'] = [double]$(if($script:highContrast){0}else{1})
        Set-ButtonMaterials
    }
    $dialog.SetResourceReference([Windows.Controls.Control]::BackgroundProperty, 'ContentSurface')
    $dialog.SetResourceReference([Windows.Controls.Control]::ForegroundProperty, 'Text')
    $dialog.Language = [Windows.Markup.XmlLanguage]::GetLanguage([Globalization.CultureInfo]::CurrentUICulture.IetfLanguageTag)
    if ([OpenSmash.Localizer]::RightToLeft) {
        $dialog.FlowDirection = 'RightToLeft' 
    }
}
