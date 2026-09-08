using System.Diagnostics;
using System.IO;
using System.Text;

namespace ParserApp.Services;

public class PythonRunner
{
    private Process? _process;
    public event Action<string>? OutputReceived;
    public event Action<string>? ErrorReceived;
    public event Action<int>? ProcessExited;

    public void Start(string pythonPath, string scriptPath)
    {
        if (_process != null && !_process.HasExited)
            return;

        var psi = new ProcessStartInfo
        {
            FileName = pythonPath,
            Arguments = $"\"{scriptPath}\"",
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
            // Без этого python наследует cwd от ParserApp.exe (папка сборки),
            // а не C:\parser. config.py читает "data/settings.json" как путь
            // ОТНОСИТЕЛЬНО cwd, поэтому без WorkingDirectory он никогда не
            // находит реальный settings.json и молча использует дефолты.
            WorkingDirectory = Path.GetDirectoryName(Path.GetFullPath(scriptPath))
        };

        // Заставляем Python писать в stdout/stderr в UTF-8 независимо от
        // кодовой страницы консоли Windows (иначе кириллица превращается
        // в кракозябры при чтении через RedirectStandardOutput).
        psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
        psi.EnvironmentVariables["PYTHONUTF8"] = "1";

        _process = new Process { StartInfo = psi, EnableRaisingEvents = true };
        _process.OutputDataReceived += (s, e) =>
        {
            if (e.Data != null) OutputReceived?.Invoke(e.Data);
        };
        _process.ErrorDataReceived += (s, e) =>
        {
            if (e.Data != null) ErrorReceived?.Invoke(e.Data);
        };
        _process.Exited += (s, e) =>
        {
            ProcessExited?.Invoke(_process?.ExitCode ?? -1);
        };

        _process.Start();
        _process.BeginOutputReadLine();
        _process.BeginErrorReadLine();
    }

    public void Stop()
    {
        if (_process == null || _process.HasExited) return;

        try
        {
            _process.Kill(entireProcessTree: true);
        }
        catch { /* Процесс уже завершён */ }

        _process.Dispose();
        _process = null;
    }

    public bool IsRunning => _process != null && !_process.HasExited;
}
