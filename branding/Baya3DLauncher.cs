// Baya 3D launcher. Built with the Windows .NET Framework C# compiler.
// No registry changes, injected code, window manipulation, or binary patching.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Windows.Forms;

[assembly: AssemblyTitle("Baya 3D")]
[assembly: AssemblyDescription("Launch the local Baya 3D Blender customization")]
[assembly: AssemblyProduct("Baya 3D")]
[assembly: AssemblyCompany("Baya 3D")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

internal static class Baya3DLauncher
{
    private static string Json(string value)
    {
        return "\"" + value.Replace("\\", "\\\\").Replace("\"", "\\\"")
            .Replace("\r", "\\r").Replace("\n", "\\n").Replace("\t", "\\t") + "\"";
    }

    // Implements the CommandLineToArgvW quoting rules without passing a shell.
    private static string Quote(string argument)
    {
        StringBuilder result = new StringBuilder("\"");
        int slashes = 0;
        foreach (char value in argument)
        {
            if (value == '\\') { slashes++; continue; }
            if (value == '"')
            {
                result.Append('\\', slashes * 2 + 1);
                result.Append(value);
                slashes = 0;
                continue;
            }
            result.Append('\\', slashes);
            slashes = 0;
            result.Append(value);
        }
        result.Append('\\', slashes * 2);
        result.Append('"');
        return result.ToString();
    }

    [STAThread]
    private static int Main(string[] arguments)
    {
        try
        {
            string directory = AppDomain.CurrentDomain.BaseDirectory;
            string root = directory;
            string executable = Path.Combine(root, "blender.exe");
            DirectoryInfo candidate = new DirectoryInfo(directory);
            for (int depth = 0; depth <= 2 && candidate != null; ++depth)
            {
                string engine = Path.Combine(candidate.FullName, "blender.exe");
                if (File.Exists(engine)) { root = candidate.FullName; executable = engine; break; }
                candidate = candidate.Parent;
            }
            if (arguments.Length > 0 && arguments[0] == "--self-test")
            {
                string destination = arguments.Length > 1 ? Path.GetFullPath(arguments[1]) : Path.Combine(directory, "launcher_self_test.json");
                string report = "{\n  \"product\": \"Baya 3D\",\n  \"launcher_version\": \"1.0.0\",\n  \"engine\": \"Blender 5.3\",\n  \"engine_exists\": " + (File.Exists(executable) ? "true" : "false") +
                    ",\n  \"engine_path\": " + Json(executable) + ",\n  \"default_window_mode\": \"fullscreen\",\n  \"windowed_switch\": \"--windowed\",\n  \"uses_shell\": false,\n  \"modifies_engine_binary\": false\n}\n";
                File.WriteAllText(destination, report, new UTF8Encoding(false));
                return File.Exists(executable) ? 0 : 1;
            }
            if (!File.Exists(executable))
                throw new FileNotFoundException("The Blender engine was not found. Keep this launcher next to blender.exe or within two directory levels beneath the Blender installation.", executable);

            List<string> quotedArguments = new List<string>();
            bool background = false;
            bool windowed = false;
            foreach (string argument in arguments)
            {
                if (argument == "--windowed") { windowed = true; continue; }
                quotedArguments.Add(Quote(argument));
                if (argument == "--background" || argument == "-b") background = true;
            }
            if (!background) quotedArguments.Insert(0, windowed ? "--window-maximized" : "--window-fullscreen");
            ProcessStartInfo start = new ProcessStartInfo(executable, String.Join(" ", quotedArguments.ToArray()));
            start.WorkingDirectory = root;
            start.UseShellExecute = false;
            // Blender opens its own native GUI; there is no visible console window.
            start.CreateNoWindow = true;
            Process child = Process.Start(start);
            if (child == null) throw new IOException("The engine could not be started.");
            if (background) { child.WaitForExit(); return child.ExitCode; }
            return 0;
        }
        catch (Exception error)
        {
            MessageBox.Show(error.Message, "Baya 3D could not start", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
