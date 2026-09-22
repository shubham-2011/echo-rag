using CommunityToolkit.Mvvm.ComponentModel;

namespace EcoRag.Desktop.Models;

public partial class DocumentItem : ObservableObject
{
    [ObservableProperty]
    private string _id = Guid.NewGuid().ToString("N");

    [ObservableProperty]
    private string _fileName = string.Empty;

    [ObservableProperty]
    private string _fileSizeFormatted = "0 KB";

    [ObservableProperty]
    private int _chunkCount;

    [ObservableProperty]
    private string _embeddingModel = "bge-small-en-v1.5";

    [ObservableProperty]
    private string _status = "Indexed"; // Indexed, Processing, Failed

    [ObservableProperty]
    private double _indexingProgress = 100.0;

    [ObservableProperty]
    private DateTime _indexedAt = DateTime.Now;

    [ObservableProperty]
    private double _indexingEnergyJoules = 45.2;
}
