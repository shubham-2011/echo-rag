using System.Diagnostics;
using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using EcoRag.Desktop.Models;
using EcoRag.Desktop.Services;

namespace EcoRag.Desktop.ViewModels;

public partial class ChatViewModel : ObservableObject
{
    private readonly IEcoRagApiService _apiService;
    private string? _activeQueryRequestId;

    [ObservableProperty]
    private ObservableCollection<ChatMessage> _messages = [];

    [ObservableProperty]
    private string _inputQuery = string.Empty;

    [ObservableProperty]
    private bool _isGenerating;

    [ObservableProperty]
    private string _activeEnergySummary = "Ready for energy-efficient retrieval.";

    [ObservableProperty]
    private EnergyTelemetry _currentQueryTelemetry = new();

    [ObservableProperty]
    private EnergyTelemetry _sessionTelemetry = new() { QueryId = "session" };

    [ObservableProperty]
    private EnergyTelemetry _baselineTelemetry = new();

    public ChatViewModel(IEcoRagApiService apiService)
    {
        _apiService = apiService;
        InitializeWelcomeMessage();
    }

    private void InitializeWelcomeMessage()
    {
        Messages.Add(new ChatMessage
        {
            Role = "EcoRAG",
            Content = "Hello! I am **EcoRAG Desktop**, your energy-efficient retrieval assistant. Ask any question based on your indexed documents.",
            HasTelemetry = false
        });
        CurrentQueryTelemetry = new EnergyTelemetry();
        BaselineTelemetry = new EnergyTelemetry();
        ActiveEnergySummary = "No current query telemetry.";
    }

    [RelayCommand]
    public async Task SendMessageAsync()
    {
        if (string.IsNullOrWhiteSpace(InputQuery) || IsGenerating)
            return;

        string query = InputQuery.Trim();
        InputQuery = string.Empty;

        Messages.Add(new ChatMessage
        {
            Role = "User",
            Content = query
        });

        var assistantMsg = new ChatMessage
        {
            Role = "EcoRAG",
            Content = "",
            IsStreaming = true
        };
        Messages.Add(assistantMsg);
        IsGenerating = true;
        _activeQueryRequestId = null;

        try
        {
            await foreach (var token in _apiService.StreamQueryAsync(
                query,
                telemetry =>
                {
                    if (string.IsNullOrEmpty(telemetry.QueryId))
                    {
                        Debug.WriteLine("[UI_STATE] incoming_request= missing current_request= decision=IGNORED_EMPTY_ID");
                        return;
                    }
                    if (_activeQueryRequestId is null)
                        _activeQueryRequestId = telemetry.QueryId;
                    else if (!string.Equals(_activeQueryRequestId, telemetry.QueryId, StringComparison.Ordinal))
                    {
                        Debug.WriteLine(
                            $"[UI_STATE] incoming_request={telemetry.QueryId} current_request={_activeQueryRequestId} decision=IGNORED_STALE_UPDATE");
                        return;
                    }

                    assistantMsg.Telemetry = telemetry;
                    assistantMsg.HasTelemetry = true;
                    CurrentQueryTelemetry = telemetry;
                    BaselineTelemetry = telemetry;
                    OnPropertyChanged(nameof(CurrentQueryTelemetry));
                    OnPropertyChanged(nameof(BaselineTelemetry));
                    ActiveEnergySummary = telemetry.FormattedBadge;
                    Debug.WriteLine(
                        $"[CURRENT_QUERY] request_id={telemetry.RequestId} energy={telemetry.EnergyJoules}");
                    Debug.WriteLine(
                        $"[SESSION] total_energy={SessionTelemetry.EnergyJoules}");
                    Debug.WriteLine(
                        $"[BASELINE] request_id={telemetry.QueryId} energy={telemetry.BaselineJoules}");
                    Debug.WriteLine(
                        $"[UI_UPDATE] request_id={telemetry.QueryId} energy_j={telemetry.EnergyJoules}");
                },
                citations =>
                {
                    assistantMsg.Citations = new ObservableCollection<Citation>(citations);
                    assistantMsg.HasCitations = citations.Count > 0;
                }))
            {
                assistantMsg.Content += token;
            }
        }
        catch (Exception ex)
        {
            assistantMsg.Content += $"\n[Error during query processing: {ex.Message}]";
        }
        finally
        {
            assistantMsg.IsStreaming = false;
            IsGenerating = false;
        }
    }

    [RelayCommand]
    public void ClearChat()
    {
        Messages.Clear();
        SessionTelemetry = new EnergyTelemetry { QueryId = "session" };
        InitializeWelcomeMessage();
    }
}
