using System.Collections.ObjectModel;
using System.IO;
using Microsoft.Data.Sqlite;
using ParserApp.Models;

namespace ParserApp.Services;

public class DatabaseService : IDisposable
{
    private readonly string _connectionString;

    public DatabaseService(string dbPath)
    {
        var dir = Path.GetDirectoryName(dbPath);
        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
        {
            Directory.CreateDirectory(dir);
        }

        _connectionString = $"Data Source={dbPath}";
        Initialize();
    }

    private void Initialize()
    {
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();

        var cmd = conn.CreateCommand();
        cmd.CommandText = @"
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                endpoint TEXT NOT NULL,
                data_hash TEXT NOT NULL,
                raw_data TEXT,
                has_changed BOOLEAN DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_endpoint ON snapshots(endpoint);
        ";
        cmd.ExecuteNonQuery();
    }

    public ObservableCollection<SnapshotRecord> GetSnapshots(int limit = 500)
    {
        var list = new ObservableCollection<SnapshotRecord>();
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();

        var cmd = conn.CreateCommand();
        cmd.CommandText = @"
            SELECT id, timestamp, endpoint, has_changed, raw_data 
            FROM snapshots 
            ORDER BY id DESC 
            LIMIT @limit";
        cmd.Parameters.AddWithValue("@limit", limit);

        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            list.Add(new SnapshotRecord
            {
                Id = reader.GetInt32(0),
                Timestamp = reader.GetString(1),
                Endpoint = reader.GetString(2),
                HasChanged = reader.GetBoolean(3),
                RawData = reader.IsDBNull(4) ? "" : reader.GetString(4)
            });
        }
        return list;
    }

    public List<string> GetEndpoints()
    {
        var endpoints = new List<string>();
        using var conn = new SqliteConnection(_connectionString);
        conn.Open();

        var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT DISTINCT endpoint FROM snapshots ORDER BY endpoint";

        using var reader = cmd.ExecuteReader();
        while (reader.Read())
            endpoints.Add(reader.GetString(0));

        return endpoints;
    }

    public void Dispose() { }
}
