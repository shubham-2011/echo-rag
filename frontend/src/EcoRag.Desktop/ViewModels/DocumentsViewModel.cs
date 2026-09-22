using System.Collections.ObjectModel;
using System.Windows;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using EcoRag.Desktop.Models;
using EcoRag.Desktop.Services;
using Microsoft.Win32;

namespace EcoRag.Desktop.ViewModels;

public partial class DocumentsViewModel : ObservableObject
{
    private readonly IEcoRagApiService _apiService;

    [ObservableProperty]
    private ObservableCollection<DocumentItem> _documents =
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

    [ObservableProperty]
    private bool _isUploading;

    [ObservableProperty]
    private double _uploadProgress;

    [ObservableProperty]
    private string _statusMessage = "Ready to ingest documents.";

    public DocumentsViewModel(IEcoRagApiService apiService)
    {
        _apiService = apiService;
    }

    [RelayCommand]
    public async Task BrowseAndUploadAsync()
    {
        var openFileDialog = new OpenFileDialog
        {
            Title = "Select Documents for EcoRAG Ingestion",
            Filter = "Supported Documents (*.pdf;*.docx;*.txt;*.md)|*.pdf;*.docx;*.txt;*.md|PDF Files (*.pdf)|*.pdf|All Files (*.*)|*.*",
            Multiselect = false
        };

        if (openFileDialog.ShowDialog() == true)
        {
            await IngestFileAsync(openFileDialog.FileName);
        }
    }

    public async Task IngestFileAsync(string filePath)
    {
        IsUploading = true;
        UploadProgress = 0;
        StatusMessage = $"Ingesting {System.IO.Path.GetFileName(filePath)}...";

        var progress = new Progress<double>(p => UploadProgress = p);
        var doc = await _apiService.IngestDocumentAsync(filePath, progress);

        Application.Current?.Dispatcher?.Invoke(() =>
        {
            Documents.Insert(0, doc);
            IsUploading = false;
            StatusMessage = $"Successfully indexed {doc.FileName} into FAISS vector database ({doc.ChunkCount} chunks, {doc.IndexingEnergyJoules} J).";
        });
    }

    [RelayCommand]
    public async Task LoadDocumentsAsync()
    {
        var docs = await _apiService.GetDocumentsAsync();
        Application.Current?.Dispatcher?.Invoke(() =>
        {
            Documents.Clear();
            foreach (var doc in docs)
            {
                Documents.Add(doc);
            }
        });
    }
}
