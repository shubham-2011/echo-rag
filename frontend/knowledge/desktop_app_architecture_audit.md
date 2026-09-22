# EcoRAG Desktop Application: Comprehensive Architecture & Conversation Audit

> **Source Conversation**: [ChatGPT Share 6ab1985a](https://chatgpt.com/share/6ab1985a-c41c-83e9-b51b-8be4562768a9)  
> **Backend Conversation**: [ChatGPT Share 6ab18f6d](https://chatgpt.com/share/6ab18f6d-8e1c-83ee-9c04-d77ac8f0e36b)  
> **Date**: September 2026  
> **Target Platform**: Windows 10/11 Desktop (64-bit)  
> **Primary Technology Choice**: C# / .NET 8/9 with **WinUI 3 (Windows App SDK)**  

---

## 1. Executive Summary

The **EcoRAG Desktop Application** is a specialized native desktop client designed to interface with the **EcoRAG Backend** (an energy-efficient, telemetry-driven Retrieval-Augmented Generation benchmarking and production platform).

Rather than jumping directly into writing random UI code or boilerplates, the audited conversation establishes a **strict pre-development software engineering framework**:
1. **Separation of Concerns**: The desktop application is an **untrusted client** responsible for presentation, user interaction, local caching, and file selection. All business logic, document parsing, embeddings, FAISS vector indexing, and LLM orchestration reside securely on the backend.
2. **Technology Grounding**: Evaluating C# WinUI 3 vs. Tauri vs. Electron vs. WPF. For a dedicated Windows enterprise/research desktop environment, **C# + WinUI 3 (Windows App SDK)** provides native Fluent Design, optimal memory efficiency, multi-threading, and hardware acceleration without the overhead of Chromium.
3. **Data & Energy Telemetry**: The UI must display not only traditional chat responses and retrieved citations, but also **real-time energy metrics** (Joules, Watt-hours, latency, FLOPs/proxy energy, token usage) comparing standard RAG vs. Eco-optimized RAG.

---

## 2. Desktop Technology Evaluation & Decision

The conversation rigorously audited candidate frameworks across UI quality, performance, memory footprint, and maintainability:

| Technology | UI Quality & Design | API Access | Memory / CPU | Windows Integration | Verdict |
|---|---|---|---|---|---|
| **C# + WinUI 3 (WinAppSDK)** | ⭐⭐⭐⭐⭐ (Native Fluent, Mica, Acrylic) | ⭐⭐⭐⭐⭐ (System.Net.Http, typed) | ⭐⭐⭐⭐⭐ (Native .NET runtime, 60–120 MB RAM) | ⭐⭐⭐⭐⭐ (Deep OS, Credential Locker, Notifications) | **Chosen Primary Path** |
| **C# + WPF** | ⭐⭐⭐⭐ (Mature XAML, ModernWpf) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ (Very stable) | ⭐⭐⭐⭐⭐ | Secondary fallback for older Windows |
| **Tauri + React** | ⭐⭐⭐⭐⭐ (Web CSS, Tailwind) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ (Lightweight Rust backend) | ⭐⭐⭐⭐ | Great alternative if cross-platform required |
| **Electron + React** | ⭐⭐⭐⭐⭐ (Web ecosystem) | ⭐⭐⭐⭐⭐ | ⭐⭐ (Heavy Chromium overhead, 250–500+ MB RAM) | ⭐⭐⭐ | Rejected due to high resource usage |
| **Python + PySide6** | ⭐⭐⭐⭐ (Qt widgets) | ⭐⭐⭐⭐ | ⭐⭐⭐ (GIL, distribution complexity) | ⭐⭐⭐ | Good for quick scripts, weaker for enterprise UI |

### WinUI 3 Selection Rationale:
- **Native Look & Feel**: Uses Windows 11 Fluent Design components (`MicaBackground`, `NavigationView`, `DataGrid`, modern typography).
- **Resource Efficiency**: Significantly lighter than Electron, crucial for an application specifically highlighting "energy efficiency" and environmental awareness.
- **Enterprise C# Ecosystem**: MVVM support with `CommunityToolkit.Mvvm`, strongly-typed DTOs matching backend OpenAPI schemas, asynchronous streams (`IAsyncEnumerable`), and secure storage via `Windows.Security.Credentials.PasswordVault`.

---

## 3. Core Architectural Boundaries: Client vs. Server

A critical finding from the conversation audit is the **untrusted desktop boundary rule**:

```
┌─────────────────────────────────────────────────────────────┐
│                    DESKTOP CLIENT (WinUI 3)                 │
│                                                             │
│  - Modern Fluent UI (Mica, Dark/Light theme)               │
│  - MVVM Pattern (Views, ViewModels, Services)               │
│  - Local Windows Credential Vault (JWT access/refresh)      │
│  - Document Picker & Local Pre-validation                   │
│  - SSE / WebSocket stream listener                          │
│  - Real-time Energy & Telemetry Visualizer                  │
│  - SQLite Local Cache (Recent jobs, queries, offline state) │
└──────────────────────────────┬──────────────────────────────┘
                               │
                          HTTPS / WSS
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND API (FastAPI)                     │
│                                                             │
│  - JWT Authentication & RBAC Authorization                  │
│  - Document Ingestion, Cleaning & Deduplication             │
│  - FAISS Vector Store Management                            │
│  - BGE Reranker & Context Optimization                      │
│  - Energy Telemetry Engine (@measure_energy, Joules)        │
│  - LLM Provider Routing (Cloud / Local)                     │
│  - PostgreSQL / Relational State Metadata                   │
└─────────────────────────────────────────────────────────────┘
```

### What Belongs Where:

| Component / Responsibility | Desktop Client | Backend Server |
|---|:---:|:---:|
| **API Keys & LLM Secrets** | ❌ **Never** | ✅ Secured in `.env` / Secret Store |
| **Database Credentials** | ❌ **Never** | ✅ Managed by Backend Connection Pool |
| **Document Vectorization / FAISS** | ❌ No heavy ML locally | ✅ Backend Ingestion Worker |
| **Raw Energy Measurement Engine** | ❌ (Client only receives metrics) | ✅ Backend `@measure_energy` |
| **User Session / Access Token** | ✅ Windows PasswordVault | ✅ Verified on every request |
| **Local File Caching & Offline Cache** | ✅ SQLite / AppData | ❌ (Server manages permanent object store) |
| **UI Preferences & Window State** | ✅ Local Settings Store | ❌ |

---

## 4. UI/UX Architecture & Screen Map

The application follows a structured single-window navigation design with `NavigationView`:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [≡] EcoRAG Desktop                           [-] [□] [✕]               │
├───────────────┬─────────────────────────────────────────────────────────┤
│ 🏠 Dashboard  │  Quick Overview: Active Documents, System Health        │
│ 📄 Documents  │  Document Ingestion, Status Table, Chunk Explorer       │
│ 💬 RAG Chat   │  Streaming AI Interaction, Citation Badges, Context View│
│ ⚡ Telemetry  │  Energy Benchmarking: Joules, Tokens, Latency Charts   │
│ ⚙️ Settings   │  API Host URL, Theme (Dark/Light), Connection Test      │
├───────────────┴─────────────────────────────────────────────────────────┤
│ 🟢 Connected to Backend: http://127.0.0.1:8000 | Latency: 12ms         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Screen Responsibilities:
1. **Dashboard View**:
   - High-level KPIs: Total documents indexed, queries executed, total energy saved (Joules / % vs baseline RAG), backend status pill.
2. **Document Management & Ingestion**:
   - Drag-and-drop file upload (PDF, DOCX, TXT, MD).
   - Ingestion progress bar (Parsing ➔ Cleaning ➔ Chunking ➔ Embedding ➔ Indexing).
   - Document table with metadata: filename, chunk count, file size, embedding model, date.
3. **RAG Chat & Q&A View**:
   - Conversational interface with token-by-token streaming.
   - Expandable **Source Citations** showing exact chunk content, score, and source page.
   - Live **Query Energy Pill**: Displays `Energy: 142.3 J | Latency: 640ms | Tokens: 380`.
4. **Energy Benchmarking / Telemetry View**:
   - Side-by-side comparison: **Standard RAG vs. EcoRAG**.
   - Interactive charts: Joules per query, Accuracy vs. Energy trade-off, reranker efficiency.
   - Export benchmark reports to CSV / JSON.
5. **Settings View**:
   - Backend URL configuration (e.g., `http://localhost:8000` or remote staging).
   - Authentication login / logout.
   - Local cache clearing and diagnostic log viewer.

---

## 5. Technical Implementation Details for WinUI 3

### A. Recommended Project Structure
```
ECORAG desktop application/
├── src/
│   ├── EcoRag.Desktop/                 # WinUI 3 App Project (.NET 8/9)
│   │   ├── Assets/                     # Icons, branding, SVG/PNG assets
│   │   ├── Common/                     # Converters, Behaviors, Helpers
│   │   ├── Contracts/                  # Service interfaces (INavigation, IApiClient)
│   │   ├── Models/                     # Client domain models & DTOs
│   │   ├── Services/                   # ApiService, AuthService, LocalStorageService
│   │   ├── ViewModels/                 # MVVM ViewModels (CommunityToolkit.Mvvm)
│   │   ├── Views/                      # XAML Pages (DashboardPage, ChatPage, etc.)
│   │   ├── MainWindow.xaml             # Shell Window with NavigationView
│   │   ├── App.xaml                    # Application entry point & DI container
│   │   └── appsettings.json            # Public client configurations
│   └── EcoRag.Core/                    # Optional shared library (Contracts, DTOs)
├── knowledge/                          # Architecture blueprints, links, audits
└── README.md
```

### B. Essential NuGet Packages
- `Microsoft.WindowsAppSDK`: Core WinUI 3 controls and windowing API.
- `CommunityToolkit.Mvvm`: Fast, source-generated MVVM attributes (`[ObservableProperty]`, `[RelayCommand]`).
- `Microsoft.Extensions.DependencyInjection`: Dependency injection container.
- `Microsoft.Extensions.Http`: Typed `HttpClientFactory` with retry and resilience policies.
- `System.Text.Json`: High-performance JSON serialization matching FastAPI schemas.
- `LiveChartsCore.SkiaSharpView.WinUI`: Fluent hardware-accelerated charts for energy telemetry.
- `Microsoft.Data.Sqlite`: Lightweight local client caching.

---

## 6. Pre-Implementation Checklist

Before generating the Visual Studio WinUI 3 project:
- [x] Extract and archive all conversation links and requirements (`knowledge/links.md`).
- [x] Complete technical audit and client-server boundaries (`knowledge/desktop_app_architecture_audit.md`).
- [x] Formulate reusable audit and implementation prompts (`knowledge/analysis_prompts.md`).
- [x] Document FastAPI backend endpoint contract (`knowledge/ecorag_backend_context.md`).
- [ ] Confirm Visual Studio 2022 workload: **.NET Desktop Development** with **Windows App SDK C# Templates**.
- [ ] Initialize clean WinUI 3 desktop solution structure.
