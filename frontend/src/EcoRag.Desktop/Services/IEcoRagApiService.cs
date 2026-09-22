using EcoRag.Desktop.Models;

namespace EcoRag.Desktop.Services;

public interface IEcoRagApiService
{
    string BaseUrl { get; set; }
    bool IsConnected { get; }
    Task<bool> CheckHealthAsync();
    Task<List<DocumentItem>> GetDocumentsAsync();
    Task<DocumentItem> IngestDocumentAsync(string filePath, IProgress<double>? progress = null);
    IAsyncEnumerable<string> StreamQueryAsync(
        string query, 
        Action<EnergyTelemetry> onTelemetryReceived,
        Action<List<Citation>> onCitationsReceived,
        CancellationToken cancellationToken = default);
}
