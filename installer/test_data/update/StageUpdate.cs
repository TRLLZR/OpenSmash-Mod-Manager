using System;
using System.IO;
using System.Threading;

internal static class StageUpdate
{
    static void Assert(bool value, string error)
    {
        if (!value) throw new InvalidOperationException(error);
    }

    static int Main(string[] args)
    {
        string metadata = File.ReadAllText(args[0]);
        var current = new Version("3.6.0");
        var release = OpenSmash.StartupUpdate.SelectRelease(metadata, current);
        Assert(release != null && release.Version == new Version("3.7.0"), "Stable update was not selected.");
        Assert(OpenSmash.StartupUpdate.SelectRelease(metadata, release.Version) == null, "Same-version update accepted.");
        Assert(OpenSmash.StartupUpdate.SelectRelease(metadata, new Version("3.7.1")) == null, "Downgrade accepted.");
        Assert(OpenSmash.StartupUpdate.SelectRelease(metadata.Replace("\"prerelease\": false",
            "\"prerelease\": true"), current) == null, "Prerelease accepted.");
        Assert(!OpenSmash.StartupUpdate.DownloadHost(new Uri("https://github.com.example/update")), "Foreign host accepted.");
        Assert(!OpenSmash.StartupUpdate.DownloadHost(new Uri("http://github.com/update")), "HTTP accepted.");

        string zip = args[2] + ".zip";
        string expectedDigest = release.Sha256;
        release.Sha256 = new string('0', 64);
        try
        {
            using (var input = File.OpenRead(args[1]))
                OpenSmash.StartupUpdate.StageSetup(release, input, zip, args[2], CancellationToken.None);
            throw new InvalidOperationException("Invalid SHA-256 accepted.");
        }
        catch (InvalidDataException)
        {
            Assert(!File.Exists(args[2]), "Invalid download extracted an installer.");
        }
        finally
        {
            File.Delete(zip);
        }
        release.Sha256 = expectedDigest;
        using (var input = File.OpenRead(args[1]))
            OpenSmash.StartupUpdate.StageSetup(release, input, zip, args[2], CancellationToken.None);
        File.Delete(zip);
        return 0;
    }
}
