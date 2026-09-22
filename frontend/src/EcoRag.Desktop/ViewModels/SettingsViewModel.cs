using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using EcoRag.Desktop.Services;

namespace EcoRag.Desktop.ViewModels;

public partial class SettingsViewModel : ObservableObject
{
    private readonly IEcoRagApiService _apiService;

    [ObservableProperty]
    private string _backendUrl;

    [ObservableProperty]
    private string _connectionStatus = "Ready to test connection.";

    [ObservableProperty]
    private bool _isDarkTheme = true;

    [ObservableProperty]
    private string _embeddingModel = "BAAI/bge-small-en-v1.5";

    [ObservableProperty]
    private string _rerankerModel = "BAAI/bge-reranker-large";

    public SettingsViewModel(IEcoRagApiService apiService)
    {
        _apiService = apiService;
        _backendUrl = _apiService.BaseUrl;
    }

    [RelayCommand]
    public async Task TestConnectionAsync()
    {
        _apiService.BaseUrl = BackendUrl.Trim();
        ConnectionStatus = "Connecting to backend...";
        bool ok = await _apiService.CheckHealthAsync();
        ConnectionStatus = ok 
            ? "✅ Connected successfully to FastAPI backend!" 
            : "⚠️ Backend offline. EcoRAG Desktop is running in autonomous simulation mode.";
    }
}
