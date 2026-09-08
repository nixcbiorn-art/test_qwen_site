namespace ParserApp.Models;

public class SnapshotRecord
{
    public int Id { get; set; }
    public string Timestamp { get; set; } = string.Empty;
    public string Endpoint { get; set; } = string.Empty;
    public bool HasChanged { get; set; }
    public string RawData { get; set; } = string.Empty;
}
