namespace ParserApp.Models;

/// <summary>Одна строка маппинга в диалоге: выходное поле -> путь в JSON элемента.</summary>
public class MappingRow
{
    public string OutputField { get; set; } = string.Empty;
    public string SourcePath { get; set; } = string.Empty;
}
