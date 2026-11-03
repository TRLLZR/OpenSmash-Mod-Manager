using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text;
using System.Web.Script.Serialization;

namespace OpenSmash
{
// Shared by setup and the WPF host. Catalogs are embedded so first-run and
// recovery messages do not depend on a successful installation or network.
public static class Localizer
{
    private static readonly Dictionary<string, Dictionary<string, string>> Messages;
    public static readonly string Language;

    static Localizer()
    {
        var serializer = new JavaScriptSerializer { MaxJsonLength = 4 * 1024 * 1024 };
        using (Stream resource = Assembly.GetExecutingAssembly().GetManifestResourceStream("OpenSmash.Locales.json"))
        using (var reader = new StreamReader(resource, Encoding.UTF8))
        {
            Messages = serializer.Deserialize<Dictionary<string, Dictionary<string, string>>>(reader.ReadToEnd());
        }
        Language =
            Resolve(Environment.GetEnvironmentVariable("OPENSMASH_UI_LANGUAGE") ?? CultureInfo.CurrentUICulture.Name);
    }

    public static string Resolve(string culture)
    {
        string code = (culture ?? "en").Replace('_', '-').ToLowerInvariant();
        if (code.StartsWith("zh"))
            return code.Contains("hant") || code.Contains("tw") || code.Contains("hk") ? "zh-TW" : "zh-CN";
        code = code.Split('-')[0];
        return Array.IndexOf(
                   new[] { "de", "en", "es", "fr", "it", "pt", "nl", "pl", "tr", "ru", "uk", "ja", "ko", "ar" },
                   code) >= 0
                   ? code
                   : "en";
    }

    public static bool RightToLeft
    {
        get {
            return Language == "ar";
        }
    }

    public static string Text(string source)
    {
        if (String.IsNullOrEmpty(source) || Language == "de")
            return source;
        Dictionary<string, string> translations;
        if (Messages.TryGetValue(source, out translations))
            return Select(translations, source);

        // Source messages may append a filename or upstream diagnostic.
        // Translate only known prose, preserving that untrusted suffix as data.
        int separator = source.IndexOf('\n');
        if (separator >= 0)
            return String.Join("\n", Array.ConvertAll(source.Split('\n'), Text));
        foreach (var entry in Messages)
        {
            if (entry.Key.EndsWith(": ", StringComparison.Ordinal) &&
                source.StartsWith(entry.Key, StringComparison.Ordinal))
                return Select(entry.Value, entry.Key) + source.Substring(entry.Key.Length);
        }
        return source;
    }

    private static string Select(Dictionary<string, string> translations, string source)
    {
        string value;
        if (translations.TryGetValue(Language, out value))
            return value;
        return translations.TryGetValue("en", out value) ? value : source;
    }
}
}
