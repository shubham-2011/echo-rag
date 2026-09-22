using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using EcoRag.Desktop.Models;
using EcoRag.Desktop.Services;

namespace EcoRag.Desktop.ViewModels;

public partial class ChatViewModel : ObservableObject
{
    private readonly IEcoRagApiService _apiService;

    [ObservableProperty]
    private ObservableCollection<ChatMessage> _messages = [];

    [ObservableProperty]
    private string _inputQuery = string.Empty;

    [ObservableProperty]
    private bool _isGenerating;

    [ObservableProperty]
    private string _activeEnergySummary = "Ready for energy-efficient retrieval.";

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
            Content = "Hello! I am **EcoRAG Desktop**, your energy-efficient retrieval assistant. Ask any question based on your indexed documents, and I will generate an accurate answer while monitoring compute energy (Joules) in real-time.",
            HasTelemetry = true,
            Telemetry = new EnergyTelemetry
            {
                EnergyJoules = 12.0,
                BaselineJoules = 24.0,
                PromptTokens = 15,
                CompletionTokens = 35,
                RetrievalLatencyMs = 12.0,
                RerankLatencyMs = 25.0,
                LlmLatencyMs = 180.0
            }
        });
    }

    [RelayCommand]
    public async Task SendMessageAsync()
    {
        if (string.IsNullOrWhiteSpace(InputQuery) || IsGenerating)
            return;

        string query = InputQuery.Trim();
        InputQuery = string.Empty;

        // User message
        Messages.Add(new ChatMessage
        {
            Role = "User",
            Content = query
        });

        // Assistant streaming placeholder
        var assistantMsg = new ChatMessage
        {
            Role = "EcoRAG",
            Content = "",
            IsStreaming = true
        };
        Messages.Add(assistantMsg);
        IsGenerating = true;

        try
        {
            await foreach (var token in _apiService.StreamQueryAsync(
                query,
                telemetry =>
                {
                    assistantMsg.Telemetry = telemetry;
                    assistantMsg.HasTelemetry = true;
                    ActiveEnergySummary = telemetry.FormattedBadge;
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
        InitializeWelcomeMessage();
    }
}
