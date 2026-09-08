using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;
using ParserApp.Models;

namespace ParserApp.Services;

/// <summary>
/// Читает/пишет настройки в JSON-файл, который также читает Python
/// (config.py подхватывает этот файл как переопределение дефолтов).
/// Ключи намеренно snake_case, чтобы совпадать со стилем config.py.
/// </summary>
public class SettingsService
{
    private readonly string _path;
    private static readonly JsonSerializerOptions _options = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        Converters = { new JsonStringEnumConverter(JsonNamingPolicy.SnakeCaseLower) }
    };

    public SettingsService(string path)
    {
        _path = path;
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
        {
            Directory.CreateDirectory(dir);
        }
    }

    public AppSettings Load()
    {
        if (!File.Exists(_path))
        {
            return new AppSettings();
        }

        try
        {
            var json = File.ReadAllText(_path);
            var settings = JsonSerializer.Deserialize<AppSettings>(json, _options);
            return settings ?? new AppSettings();
        }
        catch
        {
            // Повреждённый или несовместимый файл — не роняем приложение,
            // просто стартуем с дефолтами.
            return new AppSettings();
        }
    }

    public void Save(AppSettings settings)
    {
        var json = JsonSerializer.Serialize(settings, _options);
        File.WriteAllText(_path, json);
    }
}
