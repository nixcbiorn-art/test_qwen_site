namespace ParserApp.Models;

public class MonitorSettings
{
    public string PythonPath { get; set; } = "python";
    public string ScriptPath { get; set; } = @"C:\parser\monitor.py";
    public int CheckIntervalSeconds { get; set; } = 300;
    public bool HeadlessBrowser { get; set; } = true;
}
