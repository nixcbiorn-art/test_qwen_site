using System;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using ParserApp.Models;
using ParserApp.Services;

namespace ParserApp;

public partial class MainWindow : Window
{
    // Всё завязано на единую структуру папок C:\parser — так же, как и
    // раньше было хардкожено для базы данных.
    private const string ParserRoot = @"C:\parser";
    private static readonly string MonitorScriptPath = Path.Combine(ParserRoot, "monitor.py");
    private static readonly string CrawlerScriptPath = Path.Combine(ParserRoot, "crawler.py");
    private static readonly string SettingsPath = Path.Combine(ParserRoot, "data", "settings.json");
    private static readonly string DbPath = Path.Combine(ParserRoot, "data", "changes.db");

    private readonly PythonRunner _runner = new();
    private readonly DatabaseService _db;
    private readonly SettingsService _settingsService;
    private AppSettings _settings = new();

    private ObservableCollection<SnapshotRecord> _snapshots = new();

    public MainWindow()
    {
        InitializeComponent();

        _db = new DatabaseService(DbPath);
        _settingsService = new SettingsService(SettingsPath);

        _runner.OutputReceived += msg => AppendLog(msg, "#4EC9B0");
        _runner.ErrorReceived += msg => AppendLog($"[ERR] {msg}", "#F44747");
        _runner.ProcessExited += code => Dispatcher.Invoke(() =>
        {
            BtnStart.IsEnabled = true;
            BtnStop.IsEnabled = false;
            LblStatus.Text = code == 0 ? "Завершён" : $"Ошибка (код {code})";
            LblStatus.Foreground = code == 0
                ? System.Windows.Media.Brushes.Gray
                : System.Windows.Media.Brushes.Red;
        });

        LoadSettingsIntoUi();
        LoadEndpoints();
    }

    // ---------- Настройки ----------

    private void LoadSettingsIntoUi()
    {
        _settings = _settingsService.Load();

        // Если это первый запуск и список эндпоинтов пуст — подставляем
        // те же примеры, что были захардкожены в исходном monitor.py.
        if (_settings.Endpoints.Count == 0)
        {
            _settings.Endpoints.Add(new EndpointSetting { Path = "/data/items", AuthMode = AuthModes.Login });
            _settings.Endpoints.Add(new EndpointSetting { Path = "/data/status", AuthMode = AuthModes.Login });
        }

        // Совместимость со старыми settings.json, где поля auth_mode ещё не
        // было: если значение отсутствует/некорректно, определяем режим по
        // наличию токена — так же, как это делает config.py на стороне Python.
        foreach (var ep in _settings.Endpoints)
        {
            if (Array.IndexOf(AuthModes.All, ep.AuthMode) < 0)
            {
                ep.AuthMode = string.IsNullOrEmpty(ep.Token) ? AuthModes.Login : AuthModes.Token;
            }
        }

        TxtSiteUrl.Text = _settings.SiteUrl;
        TxtApiBaseUrl.Text = _settings.ApiBaseUrl;
        TxtUsername.Text = _settings.Username;
        PwdPassword.Password = _settings.Password;
        TxtCheckInterval.Text = _settings.CheckIntervalSeconds.ToString();
        ChkHeadless.IsChecked = _settings.HeadlessBrowser;

        DgEndpoints.ItemsSource = _settings.Endpoints;

        foreach (ComboBoxItem item in CmbScriptChoice.Items)
        {
            if ((string)item.Tag == _settings.SelectedScript.ToString())
            {
                CmbScriptChoice.SelectedItem = item;
                break;
            }
        }

        UpdateScriptPathFromSelection();
    }

    private void CmbScriptChoice_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        UpdateScriptPathFromSelection();
    }

    private void UpdateScriptPathFromSelection()
    {
        if (TxtScriptPath == null) return; // ещё не инициализирован в момент первого срабатывания

        if (CmbScriptChoice.SelectedItem is ComboBoxItem item)
        {
            TxtScriptPath.Text = (string)item.Tag == "Crawler" ? CrawlerScriptPath : MonitorScriptPath;
        }
    }

    private void BtnAddEndpoint_Click(object sender, RoutedEventArgs e)
    {
        _settings.Endpoints.Add(new EndpointSetting { Path = "/new/endpoint", AuthMode = AuthModes.Login });
    }

    private void BtnEditMapping_Click(object sender, RoutedEventArgs e)
    {
        if (sender is not Button btn || btn.DataContext is not EndpointSetting endpoint) return;

        var dialog = new MappingDialog(endpoint) { Owner = this };
        dialog.ShowDialog();
    }

    private void BtnRemoveEndpoint_Click(object sender, RoutedEventArgs e)
    {
        if (DgEndpoints.SelectedItem is EndpointSetting selected)
        {
            _settings.Endpoints.Remove(selected);
        }
    }

    private void BtnSaveSettings_Click(object sender, RoutedEventArgs e)
    {
        if (!int.TryParse(TxtCheckInterval.Text.Trim(), out var interval) || interval <= 0)
        {
            MessageBox.Show("Интервал проверки должен быть положительным числом (в секундах).",
                "Некорректное значение", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        _settings.SiteUrl = TxtSiteUrl.Text.Trim();
        _settings.ApiBaseUrl = TxtApiBaseUrl.Text.Trim();
        _settings.Username = TxtUsername.Text.Trim();
        _settings.Password = PwdPassword.Password;
        _settings.CheckIntervalSeconds = interval;
        _settings.HeadlessBrowser = ChkHeadless.IsChecked == true;

        if (CmbScriptChoice.SelectedItem is ComboBoxItem item)
        {
            _settings.SelectedScript = (string)item.Tag == "Crawler" ? ScriptChoice.Crawler : ScriptChoice.Monitor;
        }

        try
        {
            _settingsService.Save(_settings);
            LblSettingsStatus.Text = $"Сохранено в {DateTime.Now:HH:mm:ss} -> {SettingsPath}";
            LblSettingsStatus.Foreground = System.Windows.Media.Brushes.Green;
        }
        catch (Exception ex)
        {
            LblSettingsStatus.Text = $"Ошибка сохранения: {ex.Message}";
            LblSettingsStatus.Foreground = System.Windows.Media.Brushes.Red;
        }
    }

    // ---------- Запуск / остановка ----------

    private void BtnStart_Click(object sender, RoutedEventArgs e)
    {
        var pythonPath = TxtPythonPath.Text.Trim();
        var scriptPath = TxtScriptPath.Text.Trim();

        if (string.IsNullOrEmpty(pythonPath) || string.IsNullOrEmpty(scriptPath))
        {
            MessageBox.Show("Укажите путь к Python и скрипту", "Ошибка",
                MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }

        BtnStart.IsEnabled = false;
        BtnStop.IsEnabled = true;
        LblStatus.Text = "Запуск...";
        LblStatus.Foreground = System.Windows.Media.Brushes.Green;

        _runner.Start(pythonPath, scriptPath);
    }

    private void BtnStop_Click(object sender, RoutedEventArgs e)
    {
        _runner.Stop();
        BtnStart.IsEnabled = true;
        BtnStop.IsEnabled = false;
        LblStatus.Text = "Остановлен";
        LblStatus.Foreground = System.Windows.Media.Brushes.Gray;
    }

    private void AppendLog(string message, string colorHex)
    {
        Dispatcher.Invoke(() =>
        {
            TxtLog.AppendText($"[{DateTime.Now:HH:mm:ss}] {message}\n");
            TxtLog.ScrollToEnd();
        });
    }

    // ---------- История ----------

    private void LoadEndpoints()
    {
        try
        {
            var endpoints = _db.GetEndpoints();
            CmbEndpoint.ItemsSource = endpoints;
            if (endpoints.Count > 0)
                CmbEndpoint.SelectedIndex = 0;
        }
        catch (Exception ex)
        {
            AppendLog($"Ошибка загрузки endpoints: {ex.Message}", "#F44747");
        }
    }

    private void CmbEndpoint_SelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        LoadHistory();
    }

    private void BtnRefreshHistory_Click(object sender, RoutedEventArgs e)
    {
        LoadEndpoints();
        LoadHistory();
    }

    private void LoadHistory()
    {
        try
        {
            _snapshots = _db.GetSnapshots(500);

            var selectedEndpoint = CmbEndpoint.SelectedItem as string;
            if (!string.IsNullOrEmpty(selectedEndpoint))
            {
                var filtered = new ObservableCollection<SnapshotRecord>(
                    _snapshots.Where(s => s.Endpoint == selectedEndpoint));
                DgSnapshots.ItemsSource = filtered;
            }
            else
            {
                DgSnapshots.ItemsSource = _snapshots;
            }
        }
        catch (Exception ex)
        {
            AppendLog($"Ошибка загрузки истории: {ex.Message}", "#F44747");
        }
    }

    protected override void OnClosed(EventArgs e)
    {
        _runner.Stop();
        _db.Dispose();
        base.OnClosed(e);
    }
}
