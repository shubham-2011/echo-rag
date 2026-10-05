using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Net.Http.Json;
using System.Runtime.CompilerServices;
using System.Text.Json;
using EcoRag.Desktop.Models;

namespace EcoRag.Desktop.Services;

public class EcoRagApiService : IEcoRagApiService
{
    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower
    };

    private static readonly string UiLogPath = Path.Combine(Path.GetTempPath(), "ecorag_ui.log");

    private readonly HttpClient _httpClient;
    public string BaseUrl { get; set; } = "http://127.0.0.1:8000";
    public bool IsConnected { get; private set; }
    public List<string> ActiveDocumentIds { get; private set; } = [];

    private readonly List<DocumentItem> _localDocuments = [];

    public EcoRagApiService(HttpClient httpClient)
    {
        _httpClient = httpClient;
        if (_httpClient.Timeout < TimeSpan.FromSeconds(30))
            _httpClient.Timeout = TimeSpan.FromSeconds(120);
    }

    private static void UiLog(string line)
    {
        try
        {
            File.AppendAllText(UiLogPath, $"{DateTime.Now:O} {line}{Environment.NewLine}");
        }
        catch
        {
            Debug.WriteLine(line);
        }
        Debug.WriteLine(line);
    }

    public async Task<bool> CheckHealthAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync($"{BaseUrl.TrimEnd('/')}/api/health");
            IsConnected = response.IsSuccessStatusCode;
            return IsConnected;
        }
        catch (Exception ex)
        {
            UiLog($"[ERROR] component=UI error=HEALTH {ex.GetType().Name} {ex.Message}");
            IsConnected = false;
            return false;
        }
    }

    public async Task<List<DocumentItem>> GetDocumentsAsync()
    {
        if (await CheckHealthAsync())
        {
            try
            {
                var docs = await _httpClient.GetFromJsonAsync<List<DocumentItem>>(
                    $"{BaseUrl.TrimEnd('/')}/api/v1/documents", JsonOpts);
                if (docs != null && docs.Count > 0)
                {
                    ActiveDocumentIds = [.. docs.Select(d => d.FileName).Where(n => !string.IsNullOrWhiteSpace(n))];
                    return docs;
                }
            }
            catch (Exception ex)
            {
                UiLog($"[FALLBACK] component=DOCUMENTS reason={ex.GetType().Name}");
            }
        }

        return _localDocuments;
    }

    public async Task<DocumentItem> IngestDocumentAsync(string filePath, IProgress<double>? progress = null)
    {
        var fileInfo = new FileInfo(filePath);
        var doc = new DocumentItem
        {
            FileName = fileInfo.Name,
            FileSizeFormatted = $"{Math.Max(1, fileInfo.Length / 1024):N0} KB",
            ChunkCount = 0,
            EmbeddingModel = "server",
            Status = "Processing",
            IndexingProgress = 0,
            IndexedAt = DateTime.Now,
            IndexingEnergyJoules = 0
        };

        if (!await CheckHealthAsync())
        {
            doc.Status = "Backend unavailable";
            return doc;
        }

        using var form = new MultipartFormDataContent();
        await using var fileStream = File.OpenRead(filePath);
        using var streamContent = new StreamContent(fileStream);

        string ext = fileInfo.Extension.ToLowerInvariant();
        string mimeType = ext switch
        {
            ".pdf" => "application/pdf",
            ".docx" => "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".md" => "text/markdown",
            ".csv" => "text/csv",
            _ => "text/plain"
        };

        streamContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue(mimeType);
        form.Add(streamContent, "file", fileInfo.Name);
        form.Add(new StringContent("256"), "chunk_size");
        form.Add(new StringContent("30"), "chunk_overlap");
        form.Add(new StringContent("true"), "enable_dedup");
        form.Add(new StringContent("sentence_window"), "strategy");
        form.Add(new StringContent("true"), "replace_index");

        var res = await _httpClient.PostAsync($"{BaseUrl.TrimEnd('/')}/api/ingest/file", form);
        if (!res.IsSuccessStatusCode)
        {
            doc.Status = $"Ingest failed ({(int)res.StatusCode})";
            UiLog($"[ERROR] component=INGEST status={(int)res.StatusCode}");
            return doc;
        }

        var ingestRes = await res.Content.ReadFromJsonAsync<BackendIngestResponse>(JsonOpts);
        if (ingestRes != null)
        {
            doc.ChunkCount = ingestRes.unique_chunks_indexed;
            doc.Status = "Indexed (Live FAISS)";
            doc.IndexingProgress = 100.0;
            _localDocuments.Clear();
            _localDocuments.Insert(0, doc);
            ActiveDocumentIds = [fileInfo.Name];
            UiLog($"[INGEST] doc_id={fileInfo.Name} chunks={ingestRes.unique_chunks_indexed} replace_index=true");
        }
        progress?.Report(100);
        return doc;
    }

    public async IAsyncEnumerable<string> StreamQueryAsync(
        string query,
        Action<EnergyTelemetry> onTelemetryReceived,
        Action<List<Citation>> onCitationsReceived,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        bool backendAvailable = await CheckHealthAsync();
        if (!backendAvailable)
        {
            UiLog("[FALLBACK] component=UI reason=backend_unavailable action=abstain");
            yield return "Backend unavailable. Start the EcoRAG API on http://127.0.0.1:8000 and ingest your documents.";
            yield break;
        }

        BackendQueryResponse? backendResponse = null;
        string? requestId = null;
        try
        {
            var reqPayload = new
            {
                query,
                retrieval_mode = "adaptive",
                top_k = 5,
                max_tokens = 250,
                context_strategy = "sentence_window",
                window_size = 2,
                doc_ids = ActiveDocumentIds.Count > 0 ? ActiveDocumentIds : null
            };

            var res = await _httpClient.PostAsJsonAsync(
                $"{BaseUrl.TrimEnd('/')}/api/query", reqPayload, JsonOpts, cancellationToken);
            if (res.IsSuccessStatusCode)
            {
                backendResponse = await res.Content.ReadFromJsonAsync<BackendQueryResponse>(JsonOpts, cancellationToken);
                requestId = res.Headers.TryGetValues("X-Request-ID", out var ids)
                    ? ids.FirstOrDefault()
                    : backendResponse?.request_id;
            }
            else
            {
                UiLog($"[ERROR] component=API status={(int)res.StatusCode} request_id={requestId}");
            }
        }
        catch (Exception ex)
        {
            UiLog($"[ERROR] component=API error={ex.GetType().Name} message={ex.Message}");
            backendResponse = null;
        }

        if (backendResponse == null || string.IsNullOrWhiteSpace(backendResponse.answer))
        {
            UiLog("[FALLBACK] component=UI reason=empty_or_failed_api_response action=abstain");
            yield return "The API did not return an answer. Check backend logs for this request; no demo answer was substituted.";
            yield break;
        }

        requestId = string.IsNullOrWhiteSpace(backendResponse.request_id)
            ? (requestId ?? "missing_request_id")
            : backendResponse.request_id;

        var t = backendResponse.telemetry;
        double j = t?.estimated_joules ?? 0.0;
        if (j <= 0.0 && t != null) j = Math.Round(t.estimated_wh * 3600.0, 2);

        UiLog($"[API_RESPONSE] request_id={requestId} energy_j={j} latency_ms={t?.latency_ms ?? 0} citations={backendResponse.citations.Count}");

        var liveCitations = backendResponse.citations.Select(c => new Citation
        {
            DocumentName = string.IsNullOrWhiteSpace(c.filename) ? c.doc_id : c.filename,
            ChunkId = c.chunk_id,
            ChunkIndex = c.rank,
            PageNumber = c.page_number,
            RelevanceScore = Math.Round(c.rerank_score ?? c.score, 3),
            Snippet = c.text.Length > 280 ? c.text[..280] + "..." : c.text
        }).ToList();
        UiLog($"[UI_UPDATE] request_id={requestId} sources={liveCitations.Count} first={(liveCitations.FirstOrDefault()?.DocumentName ?? "none")}");
        onCitationsReceived(liveCitations);

        var stages = t?.stage_energy_j;
        var liveTelemetry = new EnergyTelemetry
        {
            QueryId = requestId,
            RequestId = requestId,
            EnergyJoules = Math.Round(j, 2),
            BaselineJoules = t?.baseline_joules ?? (j > 0 ? Math.Round(j * 1.85, 2) : 0),
            SavedJoules = t?.saved_joules ?? 0,
            ReductionPercent = t?.reduction_percent ?? 0,
            PromptTokens = t?.prompt_tokens ?? t?.context_tokens ?? 0,
            CompletionTokens = t?.completion_tokens ?? backendResponse.answer.Split(' ', StringSplitOptions.RemoveEmptyEntries).Length,
            RetrievalLatencyMs = t?.stage_timings_ms?.GetValueOrDefault("faiss_ms") ?? 0,
            RerankLatencyMs = t?.stage_timings_ms?.GetValueOrDefault("rerank_ms") ?? 0,
            LlmLatencyMs = t?.stage_timings_ms?.GetValueOrDefault("llm_ms") ?? 0,
            TotalLatencyOverrideMs = t?.latency_ms,
            AttentionWorkRatio = t?.attention_work_ratio ?? 1.0,
            ContextTokens = t?.context_tokens ?? 0,
            Complexity = t?.complexity ?? "adaptive",
            CacheTier = t?.cache_tier ?? "MISS",
            RerankBypassed = t?.rerank_bypassed ?? false,
            MeasurementType = t?.measurement_type ?? "estimated",
            RetrievedCount = t?.retrieved_count ?? liveCitations.Count,
            RetrievalJoules = stages?.GetValueOrDefault("retrieval_energy_j") ?? 0,
            FusionJoules = stages?.GetValueOrDefault("fusion_energy_j") ?? 0,
            RerankJoules = stages?.GetValueOrDefault("rerank_energy_j") ?? 0,
            ContextJoules = stages?.GetValueOrDefault("context_energy_j") ?? 0,
            GenerationJoules = stages?.GetValueOrDefault("generation_energy_j") ?? 0
        };
        onTelemetryReceived(liveTelemetry);
        UiLog($"[UI_UPDATE] request_id={requestId} energy_j={liveTelemetry.EnergyJoules} latency_ms={t?.latency_ms ?? 0}");

        var liveWords = backendResponse.answer.Split(' ');
        foreach (var word in liveWords)
        {
            if (cancellationToken.IsCancellationRequested)
                yield break;

            yield return word + " ";
            await Task.Delay(15, cancellationToken);
        }
    }
}

public class BackendIngestResponse
{
    public string doc_id { get; set; } = "";
    public int total_chunks_produced { get; set; }
    public int unique_chunks_indexed { get; set; }
    public int deduplicated_count { get; set; }
    public int total_vectors_in_store { get; set; }
}

public class BackendSearchHit
{
    public string chunk_id { get; set; } = "";
    public string doc_id { get; set; } = "";
    public string text { get; set; } = "";
    public double score { get; set; }
    public int rank { get; set; }
    public string? filename { get; set; }
    public int? page_number { get; set; }
    public string? section { get; set; }
    public double? retrieval_score { get; set; }
    public double? rerank_score { get; set; }
}

public class BackendTelemetry
{
    public string? request_id { get; set; }
    public double latency_ms { get; set; }
    public double peak_ram_mb { get; set; }
    public double estimated_wh { get; set; }
    public double estimated_joules { get; set; }
    public bool rerank_bypassed { get; set; }
    public double eco_score { get; set; }
    public string? cache_tier { get; set; }
    public string? complexity { get; set; }
    public double? attention_work_ratio { get; set; }
    public int? context_tokens { get; set; }
    public int? prompt_tokens { get; set; }
    public int? completion_tokens { get; set; }
    public int? total_tokens { get; set; }
    public string? measurement_type { get; set; }
    public int? retrieved_count { get; set; }
    public double? baseline_joules { get; set; }
    public double? saved_joules { get; set; }
    public double? reduction_percent { get; set; }
    public Dictionary<string, double>? stage_timings_ms { get; set; }
    public Dictionary<string, double>? stage_energy_j { get; set; }
}

public class BackendQueryResponse
{
    public string request_id { get; set; } = "";
    public string query { get; set; } = "";
    public string answer { get; set; } = "";
    public List<BackendSearchHit> citations { get; set; } = [];
    public BackendTelemetry? telemetry { get; set; }
}
