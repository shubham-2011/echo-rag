using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;

namespace EcoRag.Desktop.Models;

public partial class ChatMessage : ObservableObject
{
    [ObservableProperty]
    private string _id = Guid.NewGuid().ToString("N");

    [ObservableProperty]
    private string _role = "User"; // "User" or "EcoRAG"

    [ObservableProperty]
    private string _content = string.Empty;

    [ObservableProperty]
    private DateTime _timestamp = DateTime.Now;

    [ObservableProperty]
    private bool _isStreaming;

    [ObservableProperty]
    private EnergyTelemetry? _telemetry;

    [ObservableProperty]
    private bool _hasTelemetry;

    [ObservableProperty]
    private ObservableCollection<Citation> _citations = [];

    [ObservableProperty]
    private bool _hasCitations;

    public bool IsUser => Role == "User";
    public bool IsAssistant => !IsUser;
}
