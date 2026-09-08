using System.Collections.Generic;
using System.Collections.ObjectModel;

namespace ParserApp.Models;

public enum ScriptChoice
{
    Monitor,
    Crawler
}

/// <summary>
/// Способ авторизации для конкретного endpoint'а:
///  - "none"  — без авторизации (открытый/публичный API);
///  - "token" — собственный статический токен (поле Token);
///  - "login" — общий токен, полученный логином по Username/Password.
/// </summary>
public static class AuthModes
{
    public const string None = "none";
    public const string Token = "token";
    public const string Login = "login";

    public static readonly string[] All = { None, Token, Login };
}

public class EndpointSetting
{
    public string Path { get; set; } = string.Empty;
    public string Token { get; set; } = string.Empty;
    public string AuthMode { get; set; } = AuthModes.Login;

    // true -> автоматически обойти ВСЕ страницы (по page[number]/offset,
    // распознанным прямо в Path) и объединить элементы всех страниц.
    public bool Paginate { get; set; } = false;

    // Где в ответе лежит список элементов, если автоопределение не
    // справляется (например "data"). Пусто = автоопределение.
    public string ItemsPath { get; set; } = string.Empty;

    // Маппинг {выходное_поле: путь.в.json} — нормализует каждый элемент
    // к единому набору полей. Пусто = элементы сохраняются как есть.
    public Dictionary<string, string> Mapping { get; set; } = new();

    // Страховка от бесконечного обхода при Paginate = true.
    public int MaxPages { get; set; } = 50;
}

public class AppSettings
{
    public string SiteUrl { get; set; } = "https://example.com";
    public string ApiBaseUrl { get; set; } = "https://api.example.com/v1";
    public string Username { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
    public int CheckIntervalSeconds { get; set; } = 300;
    public bool HeadlessBrowser { get; set; } = true;
    public ScriptChoice SelectedScript { get; set; } = ScriptChoice.Monitor;
    public ObservableCollection<EndpointSetting> Endpoints { get; set; } = new();
}
