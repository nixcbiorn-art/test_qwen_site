using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;
using ParserApp.Models;

namespace ParserApp;

public partial class MappingDialog : Window
{
    private readonly EndpointSetting _endpoint;
    private readonly ObservableCollection<MappingRow> _rows;

    public MappingDialog(EndpointSetting endpoint)
    {
        InitializeComponent();
        _endpoint = endpoint;

        TxtItemsPath.Text = endpoint.ItemsPath;

        _rows = new ObservableCollection<MappingRow>(
            endpoint.Mapping.Select(kv => new MappingRow { OutputField = kv.Key, SourcePath = kv.Value }));
        DgMapping.ItemsSource = _rows;
    }

    private void BtnAddRow_Click(object sender, RoutedEventArgs e)
    {
        _rows.Add(new MappingRow { OutputField = "field", SourcePath = "path.to.value" });
    }

    private void BtnRemoveRow_Click(object sender, RoutedEventArgs e)
    {
        if (DgMapping.SelectedItem is MappingRow selected)
        {
            _rows.Remove(selected);
        }
    }

    private void BtnImport_Click(object sender, RoutedEventArgs e)
    {
        var text = TxtImportJson.Text.Trim();
        if (string.IsNullOrEmpty(text))
        {
            SetImportStatus("Вставьте JSON от нейросети в поле выше.", Brushes.OrangeRed);
            return;
        }

        try
        {
            using var doc = JsonDocument.Parse(text);
            var root = doc.RootElement;

            if (root.ValueKind != JsonValueKind.Object)
                throw new InvalidOperationException("Ожидался JSON-объект.");

            string itemsPath = "";
            JsonElement mappingElement = root;

            // Поддерживаем два формата: {"items_path":..., "mapping": {...}}
            // и просто {"поле": "путь", ...} без items_path.
            if (root.TryGetProperty("mapping", out var m) && m.ValueKind == JsonValueKind.Object)
            {
                mappingElement = m;
                if (root.TryGetProperty("items_path", out var ip) && ip.ValueKind == JsonValueKind.String)
                    itemsPath = ip.GetString() ?? "";
            }

            var newRows = new List<MappingRow>();
            foreach (var prop in mappingElement.EnumerateObject())
            {
                if (prop.Value.ValueKind != JsonValueKind.String) continue;
                newRows.Add(new MappingRow { OutputField = prop.Name, SourcePath = prop.Value.GetString() ?? "" });
            }

            if (newRows.Count == 0)
            {
                SetImportStatus("В JSON не найдено ни одного поля маппинга (ожидались строковые значения).", Brushes.OrangeRed);
                return;
            }

            if (!string.IsNullOrEmpty(itemsPath))
                TxtItemsPath.Text = itemsPath;

            _rows.Clear();
            foreach (var row in newRows) _rows.Add(row);

            SetImportStatus($"Импортировано полей: {newRows.Count}.", Brushes.Green);
        }
        catch (Exception ex)
        {
            SetImportStatus($"Ошибка разбора JSON: {ex.Message}", Brushes.Red);
        }
    }

    private void SetImportStatus(string text, Brush color)
    {
        LblImportStatus.Text = text;
        LblImportStatus.Foreground = color;
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        _endpoint.ItemsPath = TxtItemsPath.Text.Trim();

        _endpoint.Mapping = _rows
            .Where(r => !string.IsNullOrWhiteSpace(r.OutputField) && !string.IsNullOrWhiteSpace(r.SourcePath))
            .GroupBy(r => r.OutputField.Trim())
            .ToDictionary(g => g.Key, g => g.Last().SourcePath.Trim());

        DialogResult = true;
        Close();
    }

    private void BtnCancel_Click(object sender, RoutedEventArgs e)
    {
        DialogResult = false;
        Close();
    }
}
