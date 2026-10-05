namespace EcoRag.Desktop.Models;

public class EnergyTelemetry
{
    public string QueryId { get; set; } = string.Empty;
    public double EnergyJoules { get; set; }
    public double EnergyWattHours => EnergyJoules / 3600.0;
    public double BaselineJoules { get; set; }
    public double SavedJoules { get; set; }
    public double ReductionPercent { get; set; }
    public double EnergySavedPercentage => ReductionPercent > 0
        ? ReductionPercent
        : (BaselineJoules > 0
            ? Math.Max(0, ((BaselineJoules - EnergyJoules) / BaselineJoules) * 100.0)
            : 0);

    public int PromptTokens { get; set; }
    public int CompletionTokens { get; set; }
    public int TotalTokens => PromptTokens + CompletionTokens;

    public double RetrievalLatencyMs { get; set; }
    public double RerankLatencyMs { get; set; }
    public double LlmLatencyMs { get; set; }
    public double? TotalLatencyOverrideMs { get; set; }
    public double TotalLatencyMs => TotalLatencyOverrideMs ?? (RetrievalLatencyMs + RerankLatencyMs + LlmLatencyMs);

    public double AttentionWorkRatio { get; set; } = 1.0;
    public double AttentionSavingsPercentage => Math.Max(0, (1.0 - AttentionWorkRatio) * 100.0);
    public int ContextTokens { get; set; }
    public string Complexity { get; set; } = "normal";
    public string CacheTier { get; set; } = "MISS";
    public bool RerankBypassed { get; set; }
    public string MeasurementType { get; set; } = "estimated";
    public int RetrievedCount { get; set; }

    public double RetrievalJoules { get; set; }
    public double FusionJoules { get; set; }
    public double RerankJoules { get; set; }
    public double ContextJoules { get; set; }
    public double GenerationJoules { get; set; }

    public double StageShare(double joules) => EnergyJoules > 0 ? Math.Min(100, joules / EnergyJoules * 100.0) : 0;
    public double RetrievalShare => StageShare(RetrievalJoules);
    public double FusionShare => StageShare(FusionJoules);
    public double RerankShare => StageShare(RerankJoules);
    public double ContextShare => StageShare(ContextJoules);
    public double GenerationShare => StageShare(GenerationJoules);

    public string RequestId
    {
        get => QueryId;
        set => QueryId = value;
    }
    public double EcoVsBaselinePercent => BaselineJoules > 0 ? Math.Min(100, EnergyJoules / BaselineJoules * 100.0) : 0;

    public string FormattedBadge =>
        string.IsNullOrEmpty(QueryId)
            ? "No current query telemetry"
            : $"⚡ {EnergyJoules:F1} J ({EnergySavedPercentage:F0}% saved) • ⏱️ {TotalLatencyMs:F0}ms • 🧠 {TotalTokens} tokens • {MeasurementType}";
}
