using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly:AssemblyVersion("3.7.0.0")]
[assembly:AssemblyProduct("OpenSmash Mod Manager Setup")]
[assembly:System.Runtime.Versioning.TargetFramework(".NETFramework,Version=v4.8")]

internal static class Setup
{
    internal const string App = "OpenSmash.Mods.Desktop", Version = "3.7.0";
    internal const string DisplayName = "OpenSmash Mod Manager";
    internal const bool DefaultDesktopShortcut = true;
    static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 16 * 1024 * 1024 };
    static readonly string OwnExe = Assembly.GetExecutingAssembly().Location;
    internal static string LastWarnings = "";
    static string Full(string p)
    {
        return Path.GetFullPath(p).TrimEnd(Path.DirectorySeparatorChar);
    }
    static bool Under(string p, string root)
    {
        return Full(p).StartsWith(Full(root) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
    }
    static string Hash(string file)
    {
        using (var s = File.OpenRead(file)) using (var h = SHA256.Create()) return BitConverter
            .ToString(h.ComputeHash(s))
            .Replace("-", "")
            .ToLowerInvariant();
    }
    static string HashText(string text)
    {
        using (var h = SHA256.Create()) return BitConverter
            .ToString(h.ComputeHash(System.Text.Encoding.UTF8.GetBytes(text)))
            .Replace("-", "")
            .ToLowerInvariant();
    }
    static Dictionary<string, object> Read(string file)
    {
        return Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(file));
    }
    static void Write(string file, object value)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(file));
        string temp = file + ".new-" + Guid.NewGuid().ToString("N");
        File.WriteAllText(temp, Json.Serialize(value), new System.Text.UTF8Encoding(false));
        if (File.Exists(file))
            File.Replace(temp, file, null);
        else
            File.Move(temp, file);
    }
    static string Arg(string value)
    {
        return "\"" +
               System.Text.RegularExpressions.Regex.Replace(
                   System.Text.RegularExpressions.Regex.Replace(value, @"(\\*)""", "$1$1\\\""), @"(\\+)$", "$1$1") +
               "\"";
    }
    internal sealed class Context
    {
        public string Root, TestRoot, Settings, Menu, Desktop, Reg, Protocol;
        public Context(string root, string test)
        {
            Root = Full(root);
            TestRoot = test == null ? null : Full(test);
            if (TestRoot != null)
            {
                if (!Under(Root, TestRoot))
                    throw new Exception("Testinstallation muss innerhalb des Testordners liegen.");
                string marker = Path.Combine(TestRoot, "installer-test.json");
                if (Directory.Exists(TestRoot) && Directory.EnumerateFileSystemEntries(TestRoot).Any() &&
                    !File.Exists(marker))
                    throw new Exception("Testordner ist nicht leer oder nicht gekennzeichnet.");
                if (File.Exists(marker) && Convert.ToString(Read(marker)["app"]) != App)
                    throw new Exception("Fremder Testordner.");
                Write(marker, new { app = App });
                Settings = Path.Combine(TestRoot, "settings.json");
                Menu = Path.Combine(TestRoot, "Start Menu");
                Desktop = Path.Combine(TestRoot, "Desktop");
                Reg = @"Software\OpenSmashModsInstallerTests\" + HashText(TestRoot).Substring(0, 16);
                Protocol = Reg + @"\Protocols\opensmashmm";
            }
            else
            {
                Settings = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                                        "OpenSmashMods", "settings.json");
                Menu = Environment.GetFolderPath(Environment.SpecialFolder.Programs);
                Desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
                Reg = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenSmashMods";
                Protocol = @"Software\Classes\opensmashmm";
            }
        }
    }
    static void SafeRoot(string root)
    {
        if (root.Length < 8 || root.Length > 200 || root.StartsWith(@"\\") ||
            Path.GetPathRoot(root).TrimEnd('\\') == root)
            throw new Exception("Bitte einen lokalen Anwendungs-Unterordner waehlen.");
        foreach (string system in new[] { Environment.GetFolderPath(Environment.SpecialFolder.Windows),
                                          Environment.GetFolderPath(Environment.SpecialFolder.System),
                                          Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                                          Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86) })
            if (!String.IsNullOrEmpty(system) &&
                (Full(system).Equals(root, StringComparison.OrdinalIgnoreCase) || Under(root, system)))
                throw new Exception("Benutzerbezogene Installation ausserhalb von Windows und Programme erforderlich.");
        if (File.Exists(Path.Combine(root, "scripts", "run.py")))
            throw new Exception("Anwendung und OpenSmash-Spielordner muessen getrennte Ordner sein.");
        for (var d = new DirectoryInfo(root); d != null; d = d.Parent)
            if (d.Exists && (d.Attributes & FileAttributes.ReparsePoint) != 0)
                throw new Exception("Installationspfad darf keine Verknuepfung/Junction enthalten.");
    }
    static void PlatformCheck()
    {
        if (!Environment.Is64BitOperatingSystem || Environment.OSVersion.Version.Major < 10 ||
            Environment.OSVersion.Version.Build < 19041)
            throw new Exception("Windows 10 ab Version 2004 oder Windows 11, jeweils x64, wird benoetigt.");
        using (var key = Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full")) if (
            key == null ||
            Convert.ToInt32(key.GetValue("Release", 0)) <
                528040) throw new Exception(".NET Framework 4.8 fehlt. Offizielle Bezugsquelle: " +
                                            "https://dotnet.microsoft.com/download/dotnet-framework/net48");
    }
    static string Run(string python, string arguments, string cwd)
    {
        var info = new ProcessStartInfo(python, arguments) { WorkingDirectory = cwd,
                                                             UseShellExecute = false,
                                                             CreateNoWindow = true,
                                                             RedirectStandardOutput = true,
                                                             RedirectStandardError = true,
                                                             StandardOutputEncoding = System.Text.Encoding.UTF8,
                                                             StandardErrorEncoding = System.Text.Encoding.UTF8 };
        info.EnvironmentVariables["PYTHONUTF8"] = "1";
        info.EnvironmentVariables["PYTHONDONTWRITEBYTECODE"] = "1";
        using (var p = Process.Start(info))
        {
            var stdout = p.StandardOutput.ReadToEndAsync();
            var stderr = p.StandardError.ReadToEndAsync();
            if (!p.WaitForExit(30000))
            {
                p.Kill();
                throw new Exception("Die Voraussetzungen-Pruefung hat zu lange gedauert.");
            }
            Task.WaitAll(stdout, stderr);
            if (p.ExitCode != 0)
                throw new Exception("Pruefung fehlgeschlagen: " + stdout.Result + "\n" + stderr.Result);
            return stdout.Result;
        }
    }
    internal static Dictionary<string, object> CheckGame(string app, string repo)
    {
        if (String.IsNullOrWhiteSpace(repo))
            return new Dictionary<string, object> {
                { "manager_ready", false },
                { "warnings", new object[] { "OpenSmash kann beim ersten Start verbunden werden." } }
            };
        repo = Full(repo);
        if (!Directory.Exists(repo) || !File.Exists(Path.Combine(repo, "scripts", "run.py")))
            throw new Exception("Kein eingerichteter OpenSmash-Ordner: scripts\\run.py fehlt.");
        var data = Json.Deserialize<Dictionary<string, object>>(
            Run(Path.Combine(app, "runtime", "python.exe"),
                Arg(Path.Combine(app, "modmanager.py")) + " --repo " + Arg(repo) + " check", app));
        if (!Convert.ToBoolean(data["ok"]))
            throw new Exception(Convert.ToString(data["error"]));
        return (Dictionary<string, object>)data["result"];
    }
    static void Extract(string destination, CancellationToken token, Action<string> progress)
    {
        using (var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("OpenSmash.Payload.zip"))
        {
            if (stream == null)
                throw new Exception("Installationsdaten fehlen.");
            using (var archive = new ZipArchive(stream, ZipArchiveMode.Read))
            {
                var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                long total = 0;
                foreach (var entry in archive.Entries)
                {
                    token.ThrowIfCancellationRequested();
                    string name = entry.FullName.Replace('/', '\\');
                    string path = Path.GetFullPath(Path.Combine(destination, name));
                    if (!Under(path, destination) || name.Contains(":") ||
                        name.Split('\\').Any(p => p == ".." || p == "." || p.EndsWith(" ") || p.EndsWith(".")) ||
                        !seen.Add(path))
                        throw new Exception("Ungueltiger Pfad im Installationspaket.");
                    total += entry.Length;
                    if (total > 1024L * 1024 * 1024)
                        throw new Exception("Installationspaket ueberschreitet 1 GiB.");
                    if (String.IsNullOrEmpty(entry.Name))
                    {
                        Directory.CreateDirectory(path);
                        continue;
                    }
                    Directory.CreateDirectory(Path.GetDirectoryName(path));
                    using (var input = entry.Open()) using (var output = File.Create(path))
                    {
                        var buffer = new byte[1024 * 1024];
                        int n;
                        while ((n = input.Read(buffer, 0, buffer.Length)) > 0)
                        {
                            token.ThrowIfCancellationRequested();
                            output.Write(buffer, 0, n);
                        }
                    }
                }
            }
        }
        var manifest = Read(Path.Combine(destination, "PAYLOAD.json"));
        var files = (Dictionary<string, object>)manifest["files"];
        foreach (var file in files)
        {
            token.ThrowIfCancellationRequested();
            string path = Path.GetFullPath(Path.Combine(destination, file.Key));
            if (!Under(path, destination) || !File.Exists(path) || Hash(path) != Convert.ToString(file.Value))
                throw new Exception("Pruefsumme ungueltig: " + file.Key);
        }
        progress("Python und Bibliotheken werden geprueft …");
        Run(Path.Combine(destination, "runtime", "python.exe"),
            "-B -c \"import numpy,zstandard,capstone,PIL; print('ok')\"", destination);
    }
    static void Owned(string root)
    {
        string file = Path.Combine(root, "install-state.json");
        if (!File.Exists(file) || Convert.ToString(Read(file)["app"]) != App)
            throw new Exception("Zielordner gehoert nicht diesem Installer. Bitte einen leeren Ordner verwenden.");
    }
    static string ShortcutTarget(string file)
    {
        dynamic shell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));
        dynamic link = shell.CreateShortcut(file);
        return Convert.ToString(link.TargetPath);
    }
    static void MakeShortcut(string file, string root)
    {
        string exe = Path.Combine(root, "ModManager.exe");
        if (File.Exists(file) && !Full(ShortcutTarget(file)).Equals(Full(exe), StringComparison.OrdinalIgnoreCase))
            throw new Exception("Eine fremde Verknuepfung gleichen Namens wird nicht ersetzt: " + file);
        Directory.CreateDirectory(Path.GetDirectoryName(file));
        dynamic shell = Activator.CreateInstance(Type.GetTypeFromProgID("WScript.Shell"));
        dynamic link = shell.CreateShortcut(file);
        link.TargetPath = exe;
        link.Arguments = "";
        link.WorkingDirectory = root;
        link.Description = DisplayName;
        link.IconLocation = Path.Combine(root, "BrandIcon.ico") + ",0";
        link.Save();
    }
    static string[] OldLinks(Context c)
    {
        return new[] { Path.Combine(c.Menu, "OpenSmash Mods.lnk"), Path.Combine(c.Desktop, "OpenSmash Mods.lnk") };
    }
    static bool OwnLink(string file, Context c)
    {
        return File.Exists(file) &&
               Full(ShortcutTarget(file))
                   .Equals(Full(Path.Combine(c.Root, "ModManager.exe")), StringComparison.OrdinalIgnoreCase);
    }
    static void Register(Context c)
    {
        using (var key = Registry.CurrentUser.CreateSubKey(c.Reg))
        {
            key.SetValue("DisplayName", DisplayName);
            key.SetValue("DisplayVersion", Version);
            key.SetValue("Publisher", DisplayName);
            key.SetValue("InstallLocation", c.Root);
            key.SetValue("UninstallString", Arg(Path.Combine(c.Root, "Uninstall.exe")) + " --uninstall --dir " +
                                                Arg(c.Root) +
                                                (c.TestRoot == null ? "" : " --test-root " + Arg(c.TestRoot)));
            key.SetValue("DisplayIcon", Path.Combine(c.Root, "ModManager.exe"));
            key.SetValue("NoModify", 1, RegistryValueKind.DWord);
            key.SetValue("NoRepair", 1, RegistryValueKind.DWord);
        }
    }
    static void Preferences(Context c, string repo)
    {
        Dictionary<string, object> value = new Dictionary<string, object> { { "app", "OpenSmashModsPreferences-v1" },
                                                                            { "glass", "Solid" },
                                                                            { "repo", "" } };
        if (File.Exists(c.Settings))
        {
            try
            {
                var old = Read(c.Settings);
                if (Convert.ToString(old["app"]) != "OpenSmashModsPreferences-v1")
                    throw new Exception("Fremde Einstellungsdatei wird nicht ersetzt.");
                value = old;
            }
            catch (System.ArgumentException)
            {
                File.Copy(c.Settings, c.Settings + ".backup-" + Guid.NewGuid().ToString("N"));
            }
        }
        value["install_dir"] = c.Root;
        if (!String.IsNullOrWhiteSpace(repo))
            value["repo"] = Full(repo);
        Write(c.Settings, value);
    }
    static Dictionary<string, object> RegistrySnapshot(string path)
    {
        using (var key = Registry.CurrentUser.OpenSubKey(path)) return key == null
            ? null
            : key.GetValueNames().ToDictionary(n => n, n => key.GetValue(n));
    }
    sealed class RegistryTree
    {
        public Dictionary<string, object> Values = new Dictionary<string, object>();
        public Dictionary<string, RegistryValueKind> Kinds = new Dictionary<string, RegistryValueKind>();
        public Dictionary<string, RegistryTree> Children = new Dictionary<string, RegistryTree>();
    }
    static RegistryTree ProtocolSnapshot(string path, int depth = 0)
    {
        if (depth > 8)
            throw new Exception("Unerwartet tiefe Protokollregistrierung.");
        using (var key = Registry.CurrentUser.OpenSubKey(path))
        {
            if (key == null)
                return null;
            var state = new RegistryTree();
            foreach (string name in key.GetValueNames())
            {
                state.Values[name] = key.GetValue(name, null, RegistryValueOptions.DoNotExpandEnvironmentNames);
                state.Kinds[name] = key.GetValueKind(name);
            }
            foreach (string name in key.GetSubKeyNames())
                state.Children[name] = ProtocolSnapshot(path + "\\" + name, depth + 1);
            return state;
        }
    }
    static void RestoreProtocol(string path, RegistryTree state)
    {
        if (state == null)
            return;
        using (var key = Registry.CurrentUser.CreateSubKey(path)) foreach (var pair in state.Values)
            key.SetValue(pair.Key, pair.Value, state.Kinds[pair.Key]);
        foreach (var child in state.Children)
            RestoreProtocol(path + "\\" + child.Key, child.Value);
    }
    static string ProtocolCommand(Context c)
    {
        return Arg(Path.Combine(c.Root, "ModManager.exe")) + " --gamebanana-link \"%1\"";
    }
    static bool OwnProtocol(Context c)
    {
        using (var key = Registry.CurrentUser.OpenSubKey(c.Protocol)) using (
            var command = Registry.CurrentUser.OpenSubKey(c.Protocol + @"\shell\open\command")) return key != null &&
            command != null && Convert.ToString(key.GetValue("OpenSmashOwner")) == App &&
            Convert.ToString(command.GetValue("")) == ProtocolCommand(c);
    }
    static bool ProtocolExists(string path)
    {
        using (var key = Registry.CurrentUser.OpenSubKey(path)) return key != null;
    }
    static void RegisterProtocol(Context c)
    {
        using (var key = Registry.CurrentUser.CreateSubKey(c.Protocol))
        {
            key.SetValue("", "URL:OpenSmash Mod Manager");
            key.SetValue("URL Protocol", "");
            key.SetValue("OpenSmashOwner", App);
        }
        using (var key = Registry.CurrentUser.CreateSubKey(c.Protocol + @"\DefaultIcon"))
            key.SetValue("", Arg(Path.Combine(c.Root, "BrandIcon.ico")) + ",0");
        using (var key = Registry.CurrentUser.CreateSubKey(c.Protocol + @"\shell\open\command"))
            key.SetValue("", ProtocolCommand(c));
    }
    internal static void Install(Context c, string repo, bool desktop, CancellationToken token, Action<string> progress)
    {
        PlatformCheck();
        SafeRoot(c.Root);
        var protocol = ProtocolSnapshot(c.Protocol);
        if (protocol != null && !OwnProtocol(c))
            throw new Exception("Das opensmashmm-Protokoll gehoert bereits einer anderen Installation. Vorhandene " +
                                "Zuordnung bleibt erhalten.");
        LastWarnings = "";
        string parent = Path.GetDirectoryName(c.Root);
        Directory.CreateDirectory(parent);
        if (Directory.Exists(c.Root) && Directory.EnumerateFileSystemEntries(c.Root).Any())
            Owned(c.Root);
        foreach (var p in Process.GetProcessesByName("ModManager"))
        {
            try
            {
                if (Under(p.MainModule.FileName, c.Root))
                    throw new InvalidOperationException(
                        "Bitte den installierten Modmanager vor dem Update schliessen.");
            }
            catch (System.ComponentModel.Win32Exception)
            {
            }
            finally
            {
                p.Dispose();
            }
        }
        string stage = c.Root + ".staging-" + Guid.NewGuid().ToString("N"),
               backup = c.Root + ".backup-" + DateTime.Now.ToString("yyyyMMdd-HHmmss") + "-" +
                        Guid.NewGuid().ToString("N").Substring(0, 6);
        byte[] settings = File.Exists(c.Settings) ? File.ReadAllBytes(c.Settings) : null;
        var reg = RegistrySnapshot(c.Reg);
        var shortcutCopies = new Dictionary<string, byte[]>();
        string menuLink = Path.Combine(c.Menu, DisplayName + ".lnk"),
               desktopLink = Path.Combine(c.Desktop, DisplayName + ".lnk");
        bool preserveDesktop = OwnLink(desktopLink, c) || OwnLink(OldLinks(c)[1], c);
        foreach (string link in new[] { menuLink, desktopLink }.Concat(OldLinks(c)))
            shortcutCopies[link] = File.Exists(link) ? File.ReadAllBytes(link) : null;
        bool moved = false, published = false;
        try
        {
            Directory.CreateDirectory(stage);
            progress("Anwendung und private Laufzeit werden entpackt …");
            Extract(stage, token, progress);
            if (!String.IsNullOrWhiteSpace(repo))
            {
                progress("OpenSmash wird geprueft …");
                var check = CheckGame(stage, repo);
                if (!Convert.ToBoolean(check["manager_ready"]))
                    throw new Exception("OpenSmash ist unvollstaendig: " + Json.Serialize(check["issues"]));
                LastWarnings = String.Join("\r\n", ((System.Collections.IEnumerable)check["warnings"])
                                                       .Cast<object>()
                                                       .Select(x => Convert.ToString(x)));
            }
            token.ThrowIfCancellationRequested();
            progress("Installation wird abgeschlossen …");
            if (Directory.Exists(c.Root))
            {
                Directory.Move(c.Root, backup);
                moved = true;
            }
            Directory.Move(stage, c.Root);
            published = true;
            var manifest = Read(Path.Combine(c.Root, "PAYLOAD.json"));
            Write(Path.Combine(c.Root, "install-state.json"),
                  new { app = App, version = Version, files = manifest["files"], settings = c.Settings,
                        testRoot = c.TestRoot, created = DateTime.UtcNow.ToString("o") });
            Preferences(c, repo);
            MakeShortcut(menuLink, c.Root);
            if (desktop || preserveDesktop)
                MakeShortcut(desktopLink, c.Root);
            Register(c);
            RegisterProtocol(c);
            foreach (string link in OldLinks(c))
                if (OwnLink(link, c))
                    File.Delete(link);
            progress("Fertig. Vorhandene Mods, Spiel-Einstellungen und Saves bleiben erhalten.");
        }
        catch
        {
            if (published && Directory.Exists(c.Root))
                Directory.Move(c.Root, c.Root + ".failed-" + Guid.NewGuid().ToString("N"));
            if (moved && Directory.Exists(backup))
                Directory.Move(backup, c.Root);
            if (published)
            {
                if (settings != null)
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(c.Settings));
                    File.WriteAllBytes(c.Settings, settings);
                }
                else if (File.Exists(c.Settings))
                    File.Delete(c.Settings);
                foreach (var link in shortcutCopies)
                {
                    if (link.Value != null)
                    {
                        Directory.CreateDirectory(Path.GetDirectoryName(link.Key));
                        File.WriteAllBytes(link.Key, link.Value);
                    }
                    else if (File.Exists(link.Key) && Full(ShortcutTarget(link.Key))
                                                          .Equals(Full(Path.Combine(c.Root, "ModManager.exe")),
                                                                  StringComparison.OrdinalIgnoreCase))
                        File.Delete(link.Key);
                }
                Registry.CurrentUser.DeleteSubKeyTree(c.Reg, false);
                if (reg != null)
                    using (var key = Registry.CurrentUser.CreateSubKey(c.Reg)) foreach (var v in reg)
                        key.SetValue(v.Key, v.Value);
                if (OwnProtocol(c) || !ProtocolExists(c.Protocol))
                {
                    Registry.CurrentUser.DeleteSubKeyTree(c.Protocol, false);
                    RestoreProtocol(c.Protocol, protocol);
                }
            }
            throw;
        }
        finally
        {
            if (Directory.Exists(stage))
            {
                SafeRoot(stage);
                Directory.Delete(stage, true);
            }
        }
    }
    internal static void Uninstall(Context c)
    {
        SafeRoot(c.Root);
        Owned(c.Root);
        foreach (var p in Process.GetProcessesByName("ModManager"))
        {
            try
            {
                if (Under(p.MainModule.FileName, c.Root))
                    throw new Exception("Bitte den Modmanager vor der Deinstallation schliessen.");
            }
            catch (System.ComponentModel.Win32Exception)
            {
            }
            finally
            {
                p.Dispose();
            }
        }
        var state = Read(Path.Combine(c.Root, "install-state.json"));
        var files = (Dictionary<string, object>)state["files"];
        foreach (var item in files)
        {
            string file = Path.GetFullPath(Path.Combine(c.Root, item.Key));
            if (!Under(file, c.Root))
                throw new Exception("Ungueltiger Eigentumsnachweis.");
            for (var d = new DirectoryInfo(Path.GetDirectoryName(file)); d != null && Under(d.FullName, c.Root);
                 d = d.Parent)
                if (d.Exists && (d.Attributes & FileAttributes.ReparsePoint) != 0)
                    throw new Exception("Verknuepfung im Installationsordner; keine Dateien entfernt.");
            if (File.Exists(file) && (File.GetAttributes(file) & FileAttributes.ReparsePoint) != 0)
                throw new Exception("Verknuepfung statt Programmdatei; keine Dateien entfernt.");
        }
        foreach (string link in new[] { Path.Combine(c.Menu, DisplayName + ".lnk"),
                                        Path.Combine(c.Desktop, DisplayName + ".lnk") }
                     .Concat(OldLinks(c)))
            if (File.Exists(link) &&
                Full(ShortcutTarget(link))
                    .Equals(Full(Path.Combine(c.Root, "ModManager.exe")), StringComparison.OrdinalIgnoreCase))
                File.Delete(link);
        if (OwnProtocol(c))
            Registry.CurrentUser.DeleteSubKeyTree(c.Protocol, false);
        using (var key = Registry.CurrentUser.OpenSubKey(
                   c.Reg)) if (key != null && String.Equals(Convert.ToString(key.GetValue("InstallLocation")), c.Root,
                                                            StringComparison.OrdinalIgnoreCase))
            Registry.CurrentUser.DeleteSubKeyTree(c.Reg, false);
        foreach (var item in files)
        {
            string file = Path.GetFullPath(Path.Combine(c.Root, item.Key));
            if (!Under(file, c.Root))
                throw new Exception("Ungueltiger Eigentumsnachweis.");
            if (File.Exists(file) && Hash(file) == Convert.ToString(item.Value))
                File.Delete(file);
        }
        foreach (string file in new[] { "install-state.json", "PAYLOAD.json" })
        {
            string p = Path.Combine(c.Root, file);
            if (File.Exists(p))
                File.Delete(p);
        }
        var directories = new List<string>();
        var pending = new Stack<string>();
        pending.Push(c.Root);
        while (pending.Count > 0)
            foreach (string dir in Directory.GetDirectories(pending.Pop()))
                if ((File.GetAttributes(dir) & FileAttributes.ReparsePoint) == 0)
                {
                    directories.Add(dir);
                    pending.Push(dir);
                }
        foreach (string dir in directories.OrderByDescending(p => p.Length))
            if ((File.GetAttributes(dir) & FileAttributes.ReparsePoint) == 0 &&
                !Directory.EnumerateFileSystemEntries(dir).Any())
                Directory.Delete(dir);
        if (!Directory.EnumerateFileSystemEntries(c.Root).Any())
            Directory.Delete(c.Root);
        // Preferences and all OpenSmash profiles/backups intentionally remain outside the app folder.
    }
    static string DefaultRoot()
    {
        using (
            var key = Registry.CurrentUser.OpenSubKey(
                @"Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenSmashMods")) if (key != null &&
                                                                                           key.GetValue(
                                                                                               "InstallLocation")
                                                                                               is string) return Convert
            .ToString(key.GetValue("InstallLocation"));
        return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs",
                            DisplayName);
    }
    static string DetectGame(Context c)
    {
        try
        {
            var prefs = Read(c.Settings);
            string saved = Convert.ToString(prefs["repo"]);
            if (File.Exists(Path.Combine(saved, "scripts", "run.py")))
                return saved;
        }
        catch
        {
        }
        var candidates = new List<string>();
        string parent = Path.GetDirectoryName(OwnExe);
        candidates.Add(parent);
        candidates.Add(Path.GetDirectoryName(parent));
        foreach (var drive in DriveInfo.GetDrives().Where(d => d.IsReady && d.DriveType == DriveType.Fixed))
        {
            string games = Path.Combine(drive.RootDirectory.FullName, "Games");
            try
            {
                if (Directory.Exists(games))
                    candidates.AddRange(Directory.GetDirectories(games).Take(100));
            }
            catch (UnauthorizedAccessException)
            {
            }
        }
        return candidates.FirstOrDefault(p => !String.IsNullOrEmpty(p) &&
                                              File.Exists(Path.Combine(p, "scripts", "run.py"))) ??
               "";
    }
    static void Open(string path)
    {
        Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
    }
    [STAThread]
    static int Main(string[] args)
    {
        AppContext.SetSwitch("Switch.System.IO.UseLegacyPathHandling", false);
        AppContext.SetSwitch("Switch.System.IO.BlockLongPaths", false);
        try
        {
            var options = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            bool install = false, uninstall = false, desktop = DefaultDesktopShortcut, quiet = false;
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == "--install")
                    install = true;
                else if (args[i] == "--uninstall")
                    uninstall = true;
                else if (args[i] == "--desktop")
                    desktop = true;
                else if (args[i] == "--no-desktop")
                    desktop = false;
                else if (args[i] == "--quiet")
                    quiet = true;
                else if (args[i].StartsWith("--") && i + 1 < args.Length)
                    options[args[i]] = args[++i];
                else
                    throw new Exception("Unbekanntes Setup-Argument.");
            }
#if UNINSTALL
            uninstall = true;
#endif
            string root = options.ContainsKey("--dir") ? options["--dir"] : DefaultRoot();
            string test = options.ContainsKey("--test-root") ? options["--test-root"] : null;
            string repo = options.ContainsKey("--repo") ? options["--repo"] : "";
            var context = new Context(root, test);
            if (uninstall && !quiet &&
                MessageBox.Show(DisplayName +
                                    " deinstallieren? Mods, Spiel-Einstellungen und Saves bleiben erhalten.",
                                DisplayName, MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
                return 0;
            if (options.ContainsKey("--wait-pid"))
            {
                try
                {
                    Process.GetProcessById(Int32.Parse(options["--wait-pid"])).WaitForExit(15000);
                }
                catch (ArgumentException)
                {
                }
            }
            if (uninstall && Under(OwnExe, context.Root))
            {
                string helper =
                    Path.Combine(Path.GetTempPath(), "OpenSmash-Uninstall-" + Guid.NewGuid().ToString("N") + ".exe");
                File.Copy(OwnExe, helper);
                Process.Start(new ProcessStartInfo(helper, "--uninstall --quiet --dir " + Arg(context.Root) +
                                                               " --wait-pid " + Process.GetCurrentProcess().Id +
                                                               (test == null ? "" : " --test-root " + Arg(test))) {
                    UseShellExecute = false, CreateNoWindow = true
                });
                return 0;
            }
            using (var mutex = new Mutex(false, @"Local\OpenSmashModsSetup-" +
                                                    HashText(test ?? Environment.UserName).Substring(0, 16)))
            {
                if (!mutex.WaitOne(0))
                    throw new Exception("Ein weiterer Installer ist bereits aktiv.");
                try
                {
                    if (uninstall)
                    {
                        Uninstall(context);
                        return 0;
                    }
                    if (install)
                    {
                        Install(context, repo, desktop, CancellationToken.None, Console.WriteLine);
                        return 0;
                    }
                    Application.EnableVisualStyles();
                    Application.SetCompatibleTextRenderingDefault(false);
                    Application.Run(
                        new SetupWindow(context, String.IsNullOrWhiteSpace(repo) ? DetectGame(context) : repo));
                    return 0;
                }
                finally
                {
                    mutex.ReleaseMutex();
                }
            }
        }
        catch (Exception error)
        {
            string message =
                error is OperationCanceledException
                    ? OpenSmash.Localizer.Text("Installation abgebrochen. Vorheriger Zustand bleibt erhalten.")
                    : error.Message;
            if (args.Contains("--install") || args.Contains("--uninstall"))
                Console.Error.WriteLine(Environment.GetEnvironmentVariable("OPENSMASH_SETUP_DIAGNOSTICS") == "1"
                                            ? error.ToString()
                                            : message);
            else
                MessageBox.Show(message, DisplayName + " Setup", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
    sealed class SetupWindow : Form
    {
        readonly Context context;
        readonly TextBox game = new TextBox(), status = new TextBox();
        readonly Button install = new AeroButton(), cancel = new AeroButton();
        readonly CheckBox desktop = new CheckBox();
        CancellationTokenSource cancellation;
        bool installed;
        public SetupWindow(Context c, string initial)
        {
            context = c;
            RightToLeft = OpenSmash.Localizer.RightToLeft ? RightToLeft.Yes : RightToLeft.No;
            RightToLeftLayout = OpenSmash.Localizer.RightToLeft;
            Icon = Icon.ExtractAssociatedIcon(OwnExe);
            Text = DisplayName + " einrichten";
            Width = 680;
            Height = 510;
            MinimumSize = new Size(600, 470);
            StartPosition = FormStartPosition.CenterScreen;
            Font = new Font("Trebuchet MS", 10);
            BackColor = SystemInformation.HighContrast ? SystemColors.Window : Color.FromArgb(239, 251, 255);
            ForeColor = SystemInformation.HighContrast ? SystemColors.WindowText : Color.FromArgb(13, 50, 60);
            var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(26), ColumnCount = 2,
                                                RowCount = 8 };
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            Controls.Add(layout);
            var title =
                new Label { Text = OpenSmash.Localizer.Text("Deine Mods. Dein Spiel."), AutoSize = true,
                            Font = new Font("Trebuchet MS", 22, FontStyle.Bold), Margin = new Padding(0, 0, 0, 10) };
            layout.Controls.Add(title, 0, 0);
            layout.SetColumnSpan(title, 2);
            var intro = new Label {
                Text = OpenSmash.Localizer.Text(
                    "Installiert den Manager für dein Benutzerkonto. Deine Mods und Spieldaten bleiben erhalten."),
                AutoSize = true, MaximumSize = new Size(590, 0), Margin = new Padding(0, 0, 0, 16)
            };
            layout.Controls.Add(intro, 0, 1);
            layout.SetColumnSpan(intro, 2);
            layout.Controls.Add(
                new Label { Text = OpenSmash.Localizer.Text("OpenSmash-Ordner (optional, spaeter waehlbar)"),
                            AutoSize = true },
                0, 2);
            layout.SetColumnSpan(layout.GetControlFromPosition(0, 2), 2);
            game.Text = initial;
            game.Dock = DockStyle.Fill;
            layout.Controls.Add(game, 0, 3);
            var browse = new AeroButton { Text = OpenSmash.Localizer.Text("Auswaehlen …"), AutoSize = true };
            layout.Controls.Add(browse, 1, 3);
            browse.Click += delegate
            {
                using (var d = new FolderBrowserDialog {
                    Description = OpenSmash.Localizer.Text("OpenSmash-Ordner mit Play SSBU.bat")
                }) if (d.ShowDialog(this) == DialogResult.OK) game.Text = d.SelectedPath;
            };
            desktop.Text = OpenSmash.Localizer.Text("Desktop-Verknuepfung mit Programmlogo erstellen");
            desktop.Checked = DefaultDesktopShortcut;
            desktop.AutoSize = true;
            desktop.Margin = new Padding(0, 12, 0, 10);
            layout.Controls.Add(desktop, 0, 4);
            layout.SetColumnSpan(desktop, 2);
            status.Multiline = true;
            status.ReadOnly = true;
            status.ScrollBars = ScrollBars.Vertical;
            status.Dock = DockStyle.Fill;
            status.BackColor = BackColor;
            status.BorderStyle = BorderStyle.None;
            status.Text = OpenSmash.Localizer.Text("Ziel: ") + c.Root +
                          "\r\nZusätzliche Voraussetzungen werden bei Bedarf geprüft.";
            layout.Controls.Add(status, 0, 5);
            layout.SetColumnSpan(status, 2);
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            var help = new LinkLabel { Text = OpenSmash.Localizer.Text("Offizielle C++ Build Tools / Windows SDK"),
                                       AutoSize = true, Margin = new Padding(0, 8, 0, 12) };
            help.LinkClicked += delegate
            {
                Open("https://aka.ms/vs/17/release/vs_BuildTools.exe");
            };
            layout.Controls.Add(help, 0, 6);
            layout.SetColumnSpan(help, 2);
            ((AeroButton)install).Primary = true;
            install.Text = OpenSmash.Localizer.Text("Installieren");
            install.AutoSize = true;
            install.Padding = new Padding(16, 7, 16, 7);
            install.BackColor = SystemInformation.HighContrast ? SystemColors.Control : Color.FromArgb(184, 237, 117);
            install.FlatStyle = FlatStyle.Flat;
            cancel.Text = OpenSmash.Localizer.Text("Schliessen");
            cancel.AutoSize = true;
            cancel.Padding = new Padding(12, 7, 12, 7);
            layout.Controls.Add(install, 0, 7);
            layout.Controls.Add(cancel, 1, 7);
            cancel.Click += delegate
            {
                if (cancellation != null)
                    cancellation.Cancel();
                else
                    Close();
            };
            install.Click += async delegate
            {
                if (installed)
                {
                    var info = new ProcessStartInfo(Path.Combine(c.Root, "ModManager.exe")) { UseShellExecute = true };
                    Process.Start(info);
                    Close();
                    return;
                }
                try
                {
                    cancellation = new CancellationTokenSource();
                    install.Enabled = false;
                    game.Enabled = false;
                    browse.Enabled = false;
                    desktop.Enabled = false;
                    cancel.Text = OpenSmash.Localizer.Text("Abbrechen");
                    string chosen = game.Text;
                    bool onDesktop = desktop.Checked;
                    await Task.Run(() => Install(c, chosen, onDesktop, cancellation.Token,
                                                 text => BeginInvoke((Action)(() => status.Text = text))));
                    installed = true;
                    install.Text = OpenSmash.Localizer.Text("Manager oeffnen");
                    status.Text = OpenSmash.Localizer.Text(
                                      "Der Manager ist eingerichtet. Deine Mods und Spieldaten bleiben erhalten.") +
                                  (String.IsNullOrEmpty(LastWarnings)
                                       ? ""
                                       : "\r\n\r\nFuer den ersten Skin-Import beachten:\r\n" + LastWarnings);
                }
                catch (Exception error)
                {
                    status.Text = error is OperationCanceledException
                                      ? OpenSmash.Localizer.Text("Installation sicher abgebrochen.")
                                      : error.Message;
                }
                finally
                {
                    cancellation = null;
                    install.Enabled = true;
                    game.Enabled = true;
                    browse.Enabled = true;
                    desktop.Enabled = true;
                    cancel.Text = OpenSmash.Localizer.Text("Schliessen");
                }
            };
            FormClosing += delegate(object sender, FormClosingEventArgs e)
            {
                if (cancellation != null)
                {
                    e.Cancel = true;
                    cancellation.Cancel();
                    status.Text = OpenSmash.Localizer.Text("Abbruch wird am sicheren Punkt ausgefuehrt …");
                }
            };
        }
    }
}
