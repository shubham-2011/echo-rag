# EcoRAG Desktop Client (Frontend)

Modern, energy-conscious Windows desktop frontend for the **EcoRAG** platform built with **C# (.NET 10 / WPF)** following the **MVVM** (Model-View-ViewModel) architectural pattern.

---

## 🌟 Key Features

- 💬 **Interactive Chat & Prompting**: Real-time querying against the EcoRAG backend with streaming-style responses, citations, and source transparency.
- ⚡ **Real-Time Energy & Efficiency Telemetry**: Live gauges and charts displaying query latency (ms), token savings (%), reranker bypass rate (%), and Joules/energy saved.
- 📂 **Document Knowledge Ingestion**: Drag-and-drop ingestion supporting `.pdf`, `.docx`, `.txt`, `.md`, and `.csv`.
- 🎛️ **Retrieval Strategy Tuning**: Easily switch between `Dense`, `BM25`, `Hybrid (RRF)`, and `Adaptive EcoRAG` retrieval modes directly from the UI.
- 🎨 **Modern Dark/Light Theme**: Fluent design aesthetics with clean typography, high-contrast readability, and responsive layouts.

---

## 🏗️ Architecture & Structure

```
frontend/
├── src/
│   └── EcoRag.Desktop/
│       ├── Models/              # Data models (ChatMessage, Citation, DocumentItem, EnergyTelemetry)
│       ├── Services/            # HTTP API Client & service contracts (EcoRagApiService, IEcoRagApiService)
│       ├── ViewModels/          # MVVM ViewModels (ChatViewModel, DashboardViewModel, TelemetryViewModel, etc.)
│       ├── Views/               # WPF XAML Views (ChatView, DashboardView, DocumentsView, TelemetryView)
│       ├── App.xaml / App.xaml.cs
│       ├── MainWindow.xaml / MainWindow.xaml.cs
│       └── EcoRag.Desktop.csproj
├── Run-EcoRag-Desktop.bat       # One-click desktop launcher
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Windows 10/11
- [.NET 10 SDK](https://dotnet.microsoft.com/download) (or .NET 8+)
- Visual Studio 2022 / VS Code / JetBrains Rider

### Running Locally
1. Start the EcoRAG backend (FastAPI service on `http://localhost:8000` or via Docker).
2. Launch the desktop application:
   ```powershell
   cd frontend/src/EcoRag.Desktop
   dotnet run
   ```
   Or simply double-click `Run-EcoRag-Desktop.bat`.
