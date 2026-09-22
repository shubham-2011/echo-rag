using System.Collections.ObjectModel;
using System.Windows;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using EcoRag.Desktop.Models;
using EcoRag.Desktop.Services;

namespace EcoRag.Desktop.ViewModels;

public partial class DashboardViewModel : ObservableObject
{
    private readonly IEcoRagApiService _apiService;

    [ObservableProperty]
    private int _totalDocuments = 3;

    [ObservableProperty]
    private int _totalChunks = 208;

    [ObservableProperty]
    private double _totalEnergySavedJoules = 1420.5;

    [ObservableProperty]
    private double _averageLatencyMs = 620.0;

    [ObservableProperty]
    private string _backendStatus = "Local Engine (Offline Simulation)";

    [ObservableProperty]
    private bool _isBackendHealthy = true;

    [ObservableProperty]
    private ObservableCollection<DocumentItem> _recentDocuments =
    [
        new() {
            FileName = "EcoRAG_Research_Paper_v2.pdf",
            FileSizeFormatted = "2.4 MB",
            ChunkCount = 148,
            EmbeddingModel = "bge-small-en-v1.5",
            Status = "Indexed",
            IndexingProgress = 100,
            IndexedAt = DateTime.Now.AddHours(-3),
            IndexingEnergyJoules = 68.4
        },
        new() {
            FileName = "FastAPI_Architecture_Spec.docx",
            FileSizeFormatted = "850 KB",
            ChunkCount = 42,
            EmbeddingModel = "bge-small-en-v1.5",
            Status = "Indexed",
            IndexingProgress = 100,
            IndexedAt = DateTime.Now.AddHours(-1),
            IndexingEnergyJoules = 21.1
        },
        new() {
            FileName = "Energy_Telemetry_Benchmarks.csv",
            FileSizeFormatted = "320 KB",
            ChunkCount = 18,
            EmbeddingModel = "bge-small-en-v1.5",
            Status = "Indexed",
            IndexingProgress = 100,
            IndexedAt = DateTime.Now.AddMinutes(-20),
            IndexingEnergyJoules = 9.8
        }
    ];

    public DashboardViewModel(IEcoRagApiService apiService)
    {
        _apiService = apiService;
    }

    [RelayCommand]
    public async Task RefreshAsync()
    {
        var docs = await _apiService.GetDocumentsAsync();
        bool online = await _apiService.CheckHealthAsync();

        Application.Current?.Dispatcher?.Invoke(() =>
        {
            RecentDocuments.Clear();
            int chunks = 0;
            foreach (var doc in docs)
            {
                RecentDocuments.Add(doc);
                chunks += doc.ChunkCount;
            }

            TotalDocuments = docs.Count;
            TotalChunks = chunks;
            BackendStatus = online ? "Online (FastAPI Backend)" : "Local Engine (Offline Simulation)";
        });
    }
}
