using System;
using System.IO;
using System.Management.Automation;
using System.Management.Automation.Runspaces;
using System.Threading;
using System.Windows.Forms;
using System.Runtime.InteropServices;
using System.Reflection;
using Microsoft.Win32;
using System.ComponentModel;
using System.Collections.Generic;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.Threading.Tasks;
using System.Linq;
using System.IO.Pipes;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;

[assembly:AssemblyVersion("3.7.2.0")]
[assembly:AssemblyFileVersion("3.7.2.0")]
[assembly:AssemblyProduct("OpenSmash Mod Manager")]

namespace OpenSmash
{
public static class LinkInbox
{
    static readonly ConcurrentQueue<string> pending = new ConcurrentQueue<string>();
    static volatile bool stopping;
    static NamedPipeServerStream active;
    static string PipeName
    {
        get {
            using (var sha = SHA256.Create()) return "OpenSmashLinks-" +
                BitConverter
                    .ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(
                        WindowsIdentity.GetCurrent().User.Value +
                        Path.GetDirectoryName(typeof(LinkInbox).Assembly.Location).ToLowerInvariant())))
                    .Replace("-", "")
                    .Substring(0, 28);
        }
    }
    public static bool IsSupported(string value)
    {
        if (String.IsNullOrEmpty(value) || value.Length > 2048 ||
            value.Any(c => Char.IsControl(c) || c == '"' || c == '\'' || c == '\\'))
            return false;
        return Regex.IsMatch(value,
                             @"\Aopensmashmm:(https://gamebanana\.com/(mmdl|dl)/" +
                                 @"[1-9][0-9]{0,7},(Mod|Sound),[1-9][0-9]{0,7},(zip|rar|7z)|//gamebanana/(Mod|Sound)/" +
                                 @"[1-9][0-9]{0,7}\?file=[1-9][0-9]{0,7})\z") ||
               Regex.IsMatch(value, @"\Ahttps://gamebanana\.com/(mods|sounds)/[1-9][0-9]{0,7}/?\z");
    }
    public static bool Forward(string value)
    {
        if (!IsSupported(value))
            throw new ArgumentException("Ungueltiger OpenSmash-/GameBanana-Link.");
        try
        {
            using (var pipe = new NamedPipeClientStream(".", PipeName, PipeDirection.Out, PipeOptions.Asynchronous))
            {
                pipe.Connect(600);
                using (var writer = new StreamWriter(pipe, new UTF8Encoding(false)))
                {
                    writer.WriteLine(value);
                    writer.Flush();
                }
                return true;
            }
        }
        catch (TimeoutException)
        {
            return false;
        }
        catch (IOException)
        {
            return false;
        }
    }
    public static void Start()
    {
        stopping = false;
        var thread = new Thread(delegate() {
            while (!stopping)
            {
                try
                {
                    var security = new PipeSecurity();
                    security.SetAccessRuleProtection(true, false);
                    security.AddAccessRule(new PipeAccessRule(WindowsIdentity.GetCurrent().User,
                                                              PipeAccessRights.FullControl, AccessControlType.Allow));
                    using (var pipe =
                               new NamedPipeServerStream(PipeName, PipeDirection.In, 1, PipeTransmissionMode.Byte,
                                                         PipeOptions.Asynchronous, 4096, 4096, security))
                    {
                        active = pipe;
                        if (stopping)
                            return;
                        pipe.WaitForConnection();
                        using (var reader = new StreamReader(pipe, Encoding.UTF8, false, 4096))
                        {
                            var read = Task.Run(delegate() {
                                var buffer = new char[2049];
                                int n = 0;
                                while (n < buffer.Length)
                                {
                                    int c = reader.Read();
                                    if (c < 0 || c == '\n')
                                        break;
                                    buffer[n++] = (char)c;
                                }
                                return new string(buffer, 0, n).TrimEnd('\r');
                            });
                            if (read.Wait(2000))
                            {
                                if (IsSupported(read.Result))
                                    pending.Enqueue(read.Result);
                            }
                            else
                                pipe.Dispose();
                        }
                    }
                }
                catch (IOException)
                {
                    if (!stopping)
                        Thread.Sleep(250);
                }
                catch (ObjectDisposedException)
                {
                }
                catch (OperationCanceledException)
                {
                }
                catch (UnauthorizedAccessException)
                {
                    return;
                }
                catch (System.Security.SecurityException)
                {
                    return;
                }
                catch (AggregateException)
                {
                }
            }
        });
        thread.IsBackground = true;
        thread.Name = "OpenSmash link inbox";
        thread.Start();
    }
    public static void Stop()
    {
        stopping = true;
        try
        {
            if (active != null)
                active.Dispose();
        }
        catch (IOException)
        {
        }
    }
    public static string[] Drain()
    {
        var values = new List<string>();
        string value;
        while (values.Count < 8 && pending.TryDequeue(out value))
            values.Add(value);
        return values.ToArray();
    }
}
public sealed class BrowserRow : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler PropertyChanged;
    public int Id { get; set; }
    public string Model { get; set; }
    public string Title { get; set; }
    public string Meta { get; set; }
    public string Status { get; set; }
    public string ImageUrl { get; set; }
    public object Data { get; set; }
    string thumbnail;
    public string Thumbnail
    {
        get {
            return thumbnail;
        }
        set {
            thumbnail = value;
            var h = PropertyChanged;
            if (h != null)
                h(this, new PropertyChangedEventArgs("Thumbnail"));
        }
    }
}
public sealed class DownloadRow : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler PropertyChanged;
    public string Id { get; set; }
    public string Title { get; private set; }
    public string Status { get; private set; }
    public string Caption { get; private set; }
    public string Message { get; private set; }
    public string Evidence { get; private set; }
    public double Percent { get; private set; }
    public object Raw { get; private set; }
    void Changed(string name)
    {
        var handler = PropertyChanged;
        if (handler != null)
            handler(this, new PropertyChangedEventArgs(name));
    }
    public void Update(string title, string status, string caption, string message, string evidence, double percent,
                       object raw)
    {
        if (Title != title)
        {
            Title = title;
            Changed("Title");
        }
        if (Status != status)
        {
            Status = status;
            Changed("Status");
        }
        if (Caption != caption)
        {
            Caption = caption;
            Changed("Caption");
        }
        if (Message != message)
        {
            Message = message;
            Changed("Message");
        }
        if (Evidence != evidence)
        {
            Evidence = evidence;
            Changed("Evidence");
        }
        if (Percent != percent)
        {
            Percent = percent;
            Changed("Percent");
        }
        Raw = raw;
    }
}

public sealed class ModRow : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler PropertyChanged;
    string name;
    bool active;
    int files;
    public string Id { get; set; }
    public string Name
    {
        get {
            return name;
        }
        set {
            if (name != value)
            {
                name = value;
                Changed();
            }
        }
    }
    public bool Active
    {
        get {
            return active;
        }
        set {
            if (active != value)
            {
                active = value;
                Changed();
            }
        }
    }
    public int Files
    {
        get {
            return files;
        }
        set {
            if (files != value)
            {
                files = value;
                Changed();
            }
        }
    }
    public string FileCaption
    {
        get {
            return Files.ToString() + Localizer.Text(" Dateien");
        }
    }
    public string StatusText
    {
        get {
            return Localizer.Text(Active ? "Aktiv" : "Pausiert");
        }
    }
    private string previewPath;
    private long previewStamp;
    public System.Windows.Media.ImageSource Thumbnail { get; private set; }
    public void SetPreview(string path)
    {
        long stamp = !String.IsNullOrEmpty(path) && File.Exists(path) ? File.GetLastWriteTimeUtc(path).Ticks : 0;
        if (path == previewPath && stamp == previewStamp)
            return;
        previewPath = path;
        previewStamp = stamp;
        Thumbnail = null;
        if (stamp != 0)
        {
            try
            {
                using (var stream = File.OpenRead(path))
                {
                    var image = new System.Windows.Media.Imaging.BitmapImage();
                    image.BeginInit();
                    image.CacheOption = System.Windows.Media.Imaging.BitmapCacheOption.OnLoad;
                    image.DecodePixelWidth = 480;
                    image.StreamSource = stream;
                    image.EndInit();
                    image.Freeze();
                    Thumbnail = image;
                }
            }
            catch (IOException)
            {
            }
            catch (NotSupportedException)
            {
            }
            catch (FormatException)
            {
            }
        }
        Changed();
    }
    public string[] Warnings { get; set; }
    void Changed()
    {
        var handler = PropertyChanged;
        if (handler != null)
            handler(this, new PropertyChangedEventArgs(null));
    }
    public void Update(string label, bool enabled, int count, string[] warnings)
    {
        bool changed = name != label || active != enabled || files != count;
        name = label;
        active = enabled;
        files = count;
        Warnings = warnings;
        if (changed)
            Changed();
    }
}

// All stream callbacks execute managed C#, never a PowerShell script block on a pool thread.
public sealed class BackendJob : IDisposable
{
    readonly ConcurrentQueue<string> lines = new ConcurrentQueue<string>();
    public Process Process { get; private set; }
    public Task<string> Error { get; private set; }
    public volatile bool OutputComplete;
    public bool PendingLines
    {
        get {
            return !lines.IsEmpty;
        }
    }
    public static BackendJob Start(ProcessStartInfo info, string input)
    {
        var job = new BackendJob();
        info.UseShellExecute = false;
        info.CreateNoWindow = true;
        info.RedirectStandardOutput = true;
        info.RedirectStandardError = true;
        info.RedirectStandardInput = input != null;
        var process = new Process { StartInfo = info };
        job.Process = process;
        process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e)
        {
            if (e.Data == null)
                job.OutputComplete = true;
            else
                job.lines.Enqueue(e.Data);
        };
        try
        {
            process.Start();
            job.Error = process.StandardError.ReadToEndAsync();
            process.BeginOutputReadLine();
            if (input != null)
                process.StandardInput.WriteAsync(input + "\n").ContinueWith(delegate(Task t) {
                    try
                    {
                        process.StandardInput.Close();
                    }
                    catch (InvalidOperationException)
                    {
                    }
                    catch (IOException)
                    {
                    }
                });
            return job;
        }
        catch
        {
            process.Dispose();
            throw;
        }
    }
    public string[] Drain()
    {
        var result = new List<string>();
        string line;
        while (result.Count < 128 && lines.TryDequeue(out line))
            result.Add(line);
        return result.ToArray();
    }
    public void Dispose()
    {
        Process.Dispose();
    }
}

public static class UiNative
{
    [DllImport("user32.dll")]
    static extern bool SetProcessDpiAwarenessContext(IntPtr value);
    [DllImport("user32.dll")]
    static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")]
    static extern int GetSystemMetrics(int index);
    [DllImport("kernel32.dll")]
    static extern bool GetSystemPowerStatus(out PowerStatus status);
    [DllImport("dwmapi.dll")]
    static extern int DwmSetWindowAttribute(IntPtr handle, int key, ref int value, int size);
    [DllImport("dwmapi.dll")]
    static extern int DwmIsCompositionEnabled(out bool enabled);
    [DllImport("dwmapi.dll")]
    static extern int DwmExtendFrameIntoClientArea(IntPtr handle, ref Margins margins);
    [StructLayout(LayoutKind.Sequential)]
    struct Margins
    {
        public int Left, Right, Top, Bottom;
    }
    [StructLayout(LayoutKind.Sequential)]
    struct PowerStatus
    {
        public byte ACLineStatus, BatteryFlag, BatteryLifePercent, SystemStatusFlag;
        public uint BatteryLifeTime, BatteryFullLifeTime;
    }
    public static bool RemoteSession
    {
        get {
            return GetSystemMetrics(0x1000) != 0;
        }
    }
    public static bool EnergySaver
    {
        get {
            PowerStatus status;
            return GetSystemPowerStatus(out status) && status.SystemStatusFlag == 1;
        }
    }
    public static string BackdropStatus { get; private set; }

    public static void ConfigureDpi()
    {
        AppContext.SetSwitch("Switch.System.Windows.DoNotScaleForDpiChanges", false);
        AppContext.SetSwitch("Switch.System.Windows.DoNotUsePresentationDpiCapabilityTier2OrGreater", false);
        try
        {
            if (SetProcessDpiAwarenessContext(new IntPtr(-4)))
                return;
        }
        catch (EntryPointNotFoundException)
        {
        }
        try
        {
            SetProcessDPIAware();
        }
        catch (EntryPointNotFoundException)
        {
        }
    }
    static int Preference(string path, string key, int fallback)
    {
        try
        {
            return Convert.ToInt32(Registry.GetValue(path, key, fallback));
        }
        catch
        {
            return fallback;
        } // Optional appearance preferences must never prevent starting the manager.
    }
    public static double TextScale
    {
        get {
            return Math.Max(1.0, Math.Min(2.25, Preference(@"HKEY_CURRENT_USER\Software\Microsoft\Accessibility",
                                                           "TextScaleFactor", 100) /
                                                    100.0));
        }
    }
    public static bool DarkTheme
    {
        get {
            return Preference(@"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                              "AppsUseLightTheme", 1) == 0;
        }
    }
    public static bool TransparencyAllowed
    {
        get {
            return Preference(@"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                              "EnableTransparency", 1) != 0;
        }
    }
    public static bool Backdrop(System.Windows.Window window, bool enabled, bool dark)
    {
        try
        {
            IntPtr handle = new System.Windows.Interop.WindowInteropHelper(window).Handle;
            // Aqua Glass deliberately stays luminous even when Windows apps use dark mode.
            int mode = dark ? 1 : 0;
            DwmSetWindowAttribute(handle, 20, ref mode, 4);
            int caption = dark ? 0x003E301C : 0x00F8EAC9, captionText = dark ? 0x00FAF6E9 : 0x00594B17;
            DwmSetWindowAttribute(handle, 35, ref caption, 4);
            DwmSetWindowAttribute(handle, 36, ref captionText, 4);
            bool composition;
            BackdropStatus = "Solid: visual policy";
            if (!enabled || !TransparencyAllowed)
            {
                int solid = 1;
                DwmSetWindowAttribute(handle, 38, ref solid, 4);
                Margins plain = new Margins();
                DwmExtendFrameIntoClientArea(handle, ref plain);
                return false;
            }
            if (RemoteSession)
            {
                BackdropStatus = "Solid: remote session";
                return false;
            }
            if (EnergySaver)
            {
                BackdropStatus = "Solid: energy saver";
                return false;
            }
            if (Environment.OSVersion.Version.Build < 22621)
            {
                BackdropStatus = "Solid: Windows version";
                return false;
            }
            if (DwmIsCompositionEnabled(out composition) != 0 || !composition)
            {
                BackdropStatus = "Solid: no composition";
                return false;
            }
            // Documented DWMSBT_TRANSIENTWINDOW = Desktop Acrylic on Windows 11.
            // One compositor backdrop supplies LIVE desktop blur; Mica is not a substitute.
            int kind = 3;
            int result = DwmSetWindowAttribute(handle, 38, ref kind, 4);
            if (result != 0)
            {
                BackdropStatus = "Solid: DWM " + result;
                return false;
            }
            Margins margins = new Margins { Left = -1, Right = -1, Top = -1, Bottom = -1 };
            if (DwmExtendFrameIntoClientArea(handle, ref margins) != 0)
            {
                kind = 1;
                DwmSetWindowAttribute(handle, 38, ref kind, 4);
                BackdropStatus = "Solid: frame extension";
                return false;
            }
            System.Windows.Interop.HwndSource source = System.Windows.Interop.HwndSource.FromHwnd(handle);
            if (source == null || source.CompositionTarget == null)
            {
                BackdropStatus = "Solid: no WPF target";
                return false;
            }
            source.CompositionTarget.BackgroundColor = System.Windows.Media.Colors.Transparent;
            BackdropStatus = "Desktop Acrylic (DWM type 3)";
            return true;
        }
        catch (DllNotFoundException)
        {
            BackdropStatus = "Solid: API unavailable";
            return false;
        }
        catch (EntryPointNotFoundException)
        {
            BackdropStatus = "Solid: API unavailable";
            return false;
        }
        catch (InvalidOperationException)
        {
            BackdropStatus = "Solid: WPF target unavailable";
            return false;
        }
    }
}
}

// Small first-party GUI host. Windows supplies PowerShell, WPF and native dialogs.
internal static class ModManagerLauncher
{
    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            bool skipUpdate = args.Length > 0 && args[0] == "--skip-update";
            if (skipUpdate)
                args = args.Skip(1).ToArray();
            string incoming = null;
            if (args.Any(a => a == "--gamebanana-link"))
            {
                if (args.Length != 2 || args[0] != "--gamebanana-link" || !OpenSmash.LinkInbox.IsSupported(args[1]) ||
                    !args[1].StartsWith("opensmashmm:", StringComparison.Ordinal))
                    throw new ArgumentException("Ungueltiger OpenSmash-Linkaufruf.");
                incoming = args[1];
                if (OpenSmash.LinkInbox.Forward(incoming))
                    return 0;
                args = new string[0];
            }
            if (!skipUpdate && incoming == null && OpenSmash.StartupUpdate.TryStart(args))
                return 0;
            OpenSmash.LinkInbox.Start();
            OpenSmash.UiNative.ConfigureDpi();
            string script = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "ModManager.ps1");
            InitialSessionState initial = InitialSessionState.CreateDefault();
            initial.ExecutionPolicy = Microsoft.PowerShell.ExecutionPolicy.Bypass;
            using (Runspace runspace = RunspaceFactory.CreateRunspace(initial))
            {
                runspace.ApartmentState = ApartmentState.STA;
                runspace.ThreadOptions = PSThreadOptions.UseCurrentThread;
                runspace.Open();
                Runspace.DefaultRunspace = runspace;
                using (PowerShell shell = PowerShell.Create())
                {
                    shell.Runspace = runspace;
                    shell.AddCommand(script);
                    if (incoming != null)
                        shell.AddParameter("GameBananaLink", incoming);
                    var drops = new List<string>();
                    for (int i = 0; i < args.Length; i++)
                    {
                        string arg = args[i].ToLowerInvariant();
                        if (arg == "-repo" || arg == "--repo" || arg == "-droppath" || arg == "-visualtesttheme" ||
                            arg == "-settingspath" || arg == "-gamebananalink")
                        {
                            if (++i >= args.Length)
                                throw new ArgumentException("Pfad fehlt.");
                            if (arg == "-droppath")
                                drops.Add(args[i]);
                            else if (arg == "-gamebananalink")
                            {
                                if (!OpenSmash.LinkInbox.IsSupported(args[i]))
                                    throw new ArgumentException("Ungueltiger GameBanana-Link.");
                                shell.AddParameter("GameBananaLink", args[i]);
                            }
                            else
                                shell.AddParameter(arg == "-visualtesttheme" ? "VisualTestTheme"
                                                   : arg == "-settingspath"  ? "SettingsPath"
                                                                             : "Repo",
                                                   args[i]);
                        }
                        else if (arg == "-smoketest")
                            shell.AddParameter("SmokeTest", true);
                        else if (arg == "-safevisuals")
                            shell.AddParameter("SafeVisuals", true);
                        else if (arg == "-backdroptest")
                            shell.AddParameter("BackdropTest", true);
                        else if (arg == "-readonlysession")
                            shell.AddParameter("ReadOnlySession", true);
                        else if (!arg.StartsWith("-"))
                            drops.Add(args[i]);
                        else
                            throw new ArgumentException("Unbekannte Option: " + args[i]);
                    }
                    if (drops.Count == 1)
                        shell.AddParameter("DropPath", drops[0]);
                    else if (drops.Count > 1)
                        shell.AddParameter("DropPaths", drops.ToArray());
                    shell.Invoke();
                    if (shell.Streams.Error.Count != 0)
                        throw new InvalidOperationException(shell.Streams.Error[0].ToString());
                }
            }
            return 0;
        }
        catch (Exception error)
        {
            MessageBox.Show(OpenSmash.Localizer.Text(error.Message), "OpenSmash Mod Manager", MessageBoxButtons.OK,
                            MessageBoxIcon.Error);
            return 1;
        }
        finally
        {
            OpenSmash.LinkInbox.Stop();
        }
    }
}
