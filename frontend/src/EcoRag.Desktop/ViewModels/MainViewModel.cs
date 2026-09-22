using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace EcoRag.Desktop.ViewModels;

public partial class MainViewModel : ObservableObject
{
    [ObservableProperty]
    private string _title = "EcoRAG — Energy-Efficient Desktop Client";

    [ObservableProperty]
    private ObservableObject _currentView;

    [ObservableProperty]
    private string _activeSection = "Dashboard";

    public DashboardViewModel DashboardVM { get; }
    public DocumentsViewModel DocumentsVM { get; }
    public ChatViewModel ChatVM { get; }
    public TelemetryViewModel TelemetryVM { get; }
    public SettingsViewModel SettingsVM { get; }

    public MainViewModel(
        DashboardViewModel dashboardVM,
        DocumentsViewModel documentsVM,
        ChatViewModel chatVM,
        TelemetryViewModel telemetryVM,
        SettingsViewModel settingsVM)
    {
        DashboardVM = dashboardVM;
        DocumentsVM = documentsVM;
        ChatVM = chatVM;
        TelemetryVM = telemetryVM;
        SettingsVM = settingsVM;

        _currentView = DashboardVM;
    }

    [RelayCommand]
    public void Navigate(string target)
    {
        ActiveSection = target;
        CurrentView = target switch
        {
            "Dashboard" => DashboardVM,
            "Documents" => DocumentsVM,
            "Chat" => ChatVM,
            "Telemetry" => TelemetryVM,
            "Settings" => SettingsVM,
            _ => DashboardVM
        };
    }
}
