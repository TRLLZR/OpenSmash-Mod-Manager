using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;

namespace OpenSmash
{
internal static class StartupUpdate
{
    const string Repository = "TRLLZR/OpenSmash-Mod-Manager";
    const string PackagePrefix = "OpenSmash_Mod_Manager_Installer_v";
    const long PackageLimit = 128L * 1024 * 1024;
    static readonly string Data = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "OpenSmashMods");
    static readonly string Cache = Path.Combine(Data, "updates");

    internal sealed class Release
    {
        internal Version Version;
        internal Uri Url;
        internal long Size;
        internal string Sha256;
    }

    static object Field(Dictionary<string, object> json, string name)
    {
        object value;
        return json != null && json.TryGetValue(name, out value) ? value : null;
    }

    internal static Release SelectRelease(string json, Version installed)
    {
        var release = new JavaScriptSerializer().DeserializeObject(json) as Dictionary<string, object>;
        if (!Object.Equals(Field(release, "draft"), false) || !Object.Equals(Field(release, "prerelease"), false))
            return null;
        string tag = Field(release, "tag_name") as string;
        Version version;
        if (tag == null || !Regex.IsMatch(tag, @"\Av[0-9]+\.[0-9]+\.[0-9]+\z") ||
            !Version.TryParse(tag.Substring(1), out version) || tag != "v" + version || version <= installed)
            return null;
        string name = PackagePrefix + version + ".zip";
        var assets = Field(release, "assets") as object[];
        if (assets == null)
            return null;
        var matches = assets.OfType<Dictionary<string, object>>()
            .Where(asset => Object.Equals(Field(asset, "name"), name)).ToArray();
        if (matches.Length != 1)
            return null;
        var selected = matches[0];
        string url = "https://github.com/" + Repository + "/releases/download/" + tag + "/" + name;
        string digest = Field(selected, "digest") as string;
        object size = Field(selected, "size");
        if (!Object.Equals(Field(selected, "state"), "uploaded") ||
            !Object.Equals(Field(selected, "browser_download_url"), url) ||
            digest == null || !Regex.IsMatch(digest, @"\Asha256:[a-fA-F0-9]{64}\z") ||
            !(size is int || size is long))
            throw new InvalidDataException("The GitHub release has invalid installer metadata.");
        long length = Convert.ToInt64(size);
        if (length <= 0 || length > PackageLimit)
            throw new InvalidDataException("The GitHub installer has an invalid size.");
        return new Release { Version = version, Url = new Uri(url), Size = length, Sha256 = digest.Substring(7) };
    }

    internal static bool DownloadHost(Uri uri)
    {
        return uri.Scheme == "https" && uri.IsDefaultPort && uri.UserInfo.Length == 0 &&
            (uri.Host == "github.com" || uri.Host == "release-assets.githubusercontent.com" ||
             uri.Host == "objects.githubusercontent.com");
    }

    static T Fetch<T>(Uri uri, bool download, CancellationToken token, Func<Stream, T> consume)
    {
        for (int redirects = 0; redirects < 5; redirects++)
        {
            if (download && !DownloadHost(uri))
                throw new InvalidDataException("Unexpected GitHub download host.");
            token.ThrowIfCancellationRequested();
            var request = (HttpWebRequest)WebRequest.Create(uri);
            request.UserAgent = "OpenSmash-Mod-Manager";
            request.Accept = download ? "application/octet-stream" : "application/vnd.github+json";
            request.AllowAutoRedirect = false;
            request.Timeout = download ? 15000 : 3500;
            request.ReadWriteTimeout = request.Timeout;
            using (token.Register(request.Abort))
            using (var response = (HttpWebResponse)request.GetResponse())
            {
                int status = (int)response.StatusCode;
                if (download && (status == 301 || status == 302 || status == 303 || status == 307 || status == 308))
                {
                    Uri next;
                    if (!Uri.TryCreate(uri, response.Headers["Location"], out next))
                        throw new InvalidDataException("Invalid GitHub download redirect.");
                    uri = next;
                    continue;
                }
                if (response.StatusCode != HttpStatusCode.OK)
                    throw new InvalidDataException("Unexpected GitHub response status.");
                using (var stream = response.GetResponseStream())
                    return consume(stream);
            }
        }
        throw new InvalidDataException("Too many GitHub download redirects.");
    }

    static long Copy(Stream input, Stream output, long limit, CancellationToken token)
    {
        var buffer = new byte[64 * 1024];
        long total = 0;
        while (true)
        {
            token.ThrowIfCancellationRequested();
            int count = input.Read(buffer, 0, buffer.Length);
            if (count == 0)
                return total;
            total += count;
            if (total > limit)
                throw new InvalidDataException("The update exceeded its expected size.");
            output.Write(buffer, 0, count);
        }
    }

    static Release CheckLatest(Version installed)
    {
        // The launcher is compiled by the .NET Framework compiler. Opt into
        // the OS TLS policy before its first HTTPS request.
        AppContext.SetSwitch("Switch.System.Net.DontEnableSystemDefaultTlsVersions", false);
        using (var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(4)))
        {
            try
            {
                return Fetch(new Uri("https://api.github.com/repos/" + Repository + "/releases/latest"),
                    false, timeout.Token, stream =>
                    {
                        using (var json = new MemoryStream())
                        {
                            Copy(stream, json, 1024 * 1024, timeout.Token);
                            return SelectRelease(Encoding.UTF8.GetString(json.ToArray()), installed);
                        }
                    });
            }
            catch (WebException error)
            {
                using (var response = error.Response as HttpWebResponse)
                    if (response != null && response.StatusCode == HttpStatusCode.NotFound)
                        return null;
                throw;
            }
        }
    }

    internal static void StageSetup(Release release, Stream input, string zip, string exe, CancellationToken token)
    {
        using (var output = new FileStream(zip, FileMode.CreateNew))
            if (Copy(input, output, release.Size, token) != release.Size)
                throw new InvalidDataException("The installer download is incomplete.");
        using (var output = File.OpenRead(zip))
        using (var hash = SHA256.Create())
        {
            string digest = BitConverter.ToString(hash.ComputeHash(output)).Replace("-", "");
            if (!digest.Equals(release.Sha256, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("The installer SHA-256 does not match the GitHub release.");
        }
        using (var archive = ZipFile.OpenRead(zip))
        {
            string name = PackagePrefix + release.Version + "/Setup.exe";
            var entries = archive.Entries.Where(entry =>
                entry.FullName.Equals(name, StringComparison.OrdinalIgnoreCase)).ToArray();
            if (entries.Length != 1 || entries[0].FullName != name ||
                entries[0].Length <= 0 || entries[0].Length > PackageLimit)
                throw new InvalidDataException("The release ZIP has an invalid Setup.exe entry.");
            using (var installer = entries[0].Open())
            using (var output = new FileStream(exe, FileMode.CreateNew))
                if (Copy(installer, output, entries[0].Length, token) != entries[0].Length)
                    throw new InvalidDataException("The release ZIP contains an incomplete Setup.exe.");
        }
        var version = AssemblyName.GetAssemblyName(exe).Version;
        if (version != new Version(release.Version.Major, release.Version.Minor, release.Version.Build, 0))
            throw new InvalidDataException("The installer version does not match its release tag.");
    }

    static void Remove(string path)
    {
        try { File.Delete(path); }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
    }

    internal static void Log(string message)
    {
        try
        {
            Directory.CreateDirectory(Data);
            File.WriteAllText(Path.Combine(Data, "update.log"), DateTime.UtcNow.ToString("o") + " " + message);
        }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
    }

    static string Download(Release release, CancellationToken token)
    {
        Directory.CreateDirectory(Cache);
        string prefix = Path.Combine(Cache, "update-" + Guid.NewGuid().ToString("N"));
        string zip = prefix + ".zip", exe = prefix + ".exe";
        bool ready = false;
        try
        {
            Fetch(release.Url, true, token, stream =>
            {
                StageSetup(release, stream, zip, exe, token);
                return true;
            });
            token.ThrowIfCancellationRequested();
            ready = true;
            return exe;
        }
        finally
        {
            Remove(zip);
            if (!ready) Remove(exe);
        }
    }

    static string ShowDownload(Release release)
    {
        using (var deadline = new CancellationTokenSource(TimeSpan.FromMinutes(5)))
        using (var window = new Form { Text = "OpenSmash Mod Manager", Width = 420, Height = 155,
            StartPosition = FormStartPosition.CenterScreen, FormBorderStyle = FormBorderStyle.FixedDialog,
            MaximizeBox = false, MinimizeBox = false })
        {
            var label = new Label { Text = "Downloading OpenSmash Mod Manager " + release.Version + "…",
                Left = 16, Top = 16, Width = 375 };
            var bar = new ProgressBar { Left = 16, Top = 43, Width = 375, Style = ProgressBarStyle.Marquee };
            var cancel = new Button { Text = "Skip update", Left = 282, Top = 75, Width = 109 };
            window.Controls.AddRange(new Control[] { label, bar, cancel });
            window.CancelButton = cancel;
            cancel.DialogResult = DialogResult.None;
            bool finished = false;
            string exe = null;
            cancel.Click += delegate { deadline.Cancel(); cancel.Enabled = false; };
            window.FormClosing += delegate(object sender, FormClosingEventArgs args)
            {
                if (!finished) { args.Cancel = true; deadline.Cancel(); }
            };
            window.Shown += async delegate
            {
                try { exe = await Task.Run(() => Download(release, deadline.Token)); }
                catch (Exception error) { Log("Download skipped or failed. " + error.Message); }
                finally { finished = true; window.Close(); }
            };
            window.ShowDialog();
            return exe;
        }
    }

    internal static string Quote(string value)
    {
        return "\"" + Regex.Replace(Regex.Replace(value, @"(\\*)""", "$1$1\\\""), @"(\\+)$", "$1$1") + "\"";
    }

    static Dictionary<string, object> ReadInstall(string root)
    {
        string path = Path.Combine(root, "install-state.json");
        if (!File.Exists(path) || new FileInfo(path).Length > 1024 * 1024)
            return null;
        var state = new JavaScriptSerializer().DeserializeObject(File.ReadAllText(path)) as Dictionary<string, object>;
        return Object.Equals(Field(state, "app"), "OpenSmash.Mods.Desktop") && Field(state, "testRoot") == null
            ? state : null;
    }

    static bool ForwardGameLauncher(string exe, string repo)
    {
        string toolsExe = Path.GetFullPath(Path.Combine(repo, "opensmash_mods", "tools", "ModManager.exe"));
        if (!exe.Equals(toolsExe, StringComparison.OrdinalIgnoreCase))
            return false;
        using (var key = Registry.CurrentUser.OpenSubKey(
            @"Software\Microsoft\Windows\CurrentVersion\Uninstall\OpenSmashMods"))
        {
            string root = key == null ? null : key.GetValue("InstallLocation") as string;
            if (String.IsNullOrWhiteSpace(root) || ReadInstall(root) == null)
                return false;
            string launcher = Path.GetFullPath(Path.Combine(root, "ModManager.exe"));
            if (!File.Exists(launcher) || launcher.Equals(exe, StringComparison.OrdinalIgnoreCase))
                return false;
            using (var process = Process.Start(new ProcessStartInfo(launcher, "-Repo " + Quote(repo)) {
                UseShellExecute = false, WorkingDirectory = root
            }))
                return process != null;
        }
    }

    internal static bool TryStart(string[] args)
    {
        bool withRepo = args.Length == 2 &&
            (args[0].Equals("-Repo", StringComparison.OrdinalIgnoreCase) ||
             args[0].Equals("--repo", StringComparison.OrdinalIgnoreCase));
        if (args.Length != 0 && !withRepo)
            return false;
        try
        {
            string exe = Assembly.GetExecutingAssembly().Location;
            string root = Path.GetDirectoryName(exe);
            var install = ReadInstall(root);
            if (install == null)
                return withRepo && ForwardGameLauncher(exe, args[1]);
            Version installed;
            if (!Version.TryParse(Field(install, "version") as string, out installed) ||
                Assembly.GetExecutingAssembly().GetName().Version !=
                    new Version(installed.Major, installed.Minor, installed.Build, 0))
                return false;
            int pid = Process.GetCurrentProcess().Id;
            foreach (var process in Process.GetProcessesByName("ModManager"))
            {
                using (process)
                {
                    if (process.Id == pid) continue;
                    try
                    {
                        if (process.MainModule.FileName.Equals(exe, StringComparison.OrdinalIgnoreCase))
                            return false;
                    }
                    catch (System.ComponentModel.Win32Exception) { }
                    catch (InvalidOperationException) { }
                }
            }
            if (Directory.Exists(Cache))
                foreach (string path in Directory.EnumerateFiles(Cache, "update-*"))
                    if (Regex.IsMatch(Path.GetFileName(path), @"\Aupdate-[0-9a-f]{32}\.(exe|zip)\z") &&
                        File.GetLastWriteTimeUtc(path) < DateTime.UtcNow.AddDays(-1))
                        Remove(path);
            Release release = CheckLatest(installed);
            if (release == null)
                return false;
            string setup = ShowDownload(release);
            if (setup == null)
                return false;
            try
            {
                string arguments = "--install --update --no-desktop --dir " + Quote(root) +
                    " --wait-pid " + pid + " --expected-version " + release.Version +
                    (withRepo ? " --launch-repo " + Quote(args[1]) : "");
                using (var process = Process.Start(new ProcessStartInfo(setup, arguments) {
                    UseShellExecute = false, WorkingDirectory = Cache
                }))
                    if (process == null) throw new IOException("Could not start the update installer.");
                return true;
            }
            catch
            {
                Remove(setup);
                throw;
            }
        }
        catch (Exception error)
        {
            Log("Startup update failed. " + error.Message);
            return false;
        }
    }
}
}
