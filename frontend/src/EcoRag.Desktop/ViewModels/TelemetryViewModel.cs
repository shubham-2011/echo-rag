using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace EcoRag.Desktop.ViewModels;

public partial class TelemetryViewModel : ObservableObject
{
    [ObservableProperty]
    private double _cumulativeJoulesStandard = 3840.0;

    [ObservableProperty]
    private double _cumulativeJoulesEcoRag = 2360.0;

    public double CumulativeSavingsJoules => CumulativeJoulesStandard - CumulativeJoulesEcoRag;
    public double SavingsPercentage => CumulativeJoulesStandard > 0 
        ? ((CumulativeJoulesStandard - CumulativeJoulesEcoRag) / CumulativeJoulesStandard) * 100.0 
        : 0;

    [ObservableProperty]
    private double _carbonOffsetGrams = 0.65; // ~0.45g CO2 per Joule saved

    [ObservableProperty]
    private string _activeTierStrategy = "Tier 1: Small Chunks + BGE Rerank Gating";

    [ObservableProperty]
    private string _embeddingEfficiency = "1.24 J per 1k tokens";

    [ObservableProperty]
    private string _retrievalEfficiency = "0.08 J per query search";

    [RelayCommand]
    public void Recalculate()
    {
        CumulativeJoulesStandard += 180.0;
        CumulativeJoulesEcoRag += 105.0;
        OnPropertyChanged(nameof(CumulativeSavingsJoules));
        OnPropertyChanged(nameof(SavingsPercentage));
        CarbonOffsetGrams = Math.Round(CumulativeSavingsJoules * 0.00045, 2);
    }
}
