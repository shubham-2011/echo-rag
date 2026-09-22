namespace EcoRag.Desktop.Models;

public class EnergyTelemetry
{
    public string QueryId { get; set; } = Guid.NewGuid().ToString("N")[..8];
    public double EnergyJoules { get; set; }
    public double EnergyWattHours => EnergyJoules / 3600.0;
    public double BaselineJoules { get; set; }
    public double EnergySavedPercentage => BaselineJoules > 0 
        ? Math.Max(0, ((BaselineJoules - EnergyJoules) / BaselineJoules) * 100.0)
        : 0;

    public int PromptTokens { get; set; }
    public int CompletionTokens { get; set; }
    public int TotalTokens => PromptTokens + CompletionTokens;

    public double RetrievalLatencyMs { get; set; }
    public double RerankLatencyMs { get; set; }
    public double LlmLatencyMs { get; set; }
    public double TotalLatencyMs => RetrievalLatencyMs + RerankLatencyMs + LlmLatencyMs;

    public double AttentionWorkRatio { get; set; } = 1.0;
    public double AttentionSavingsPercentage => Math.Max(0, (1.0 - AttentionWorkRatio) * 100.0);
    public int ContextTokens { get; set; }
    public string Complexity { get; set; } = "normal";
    public string CacheTier { get; set; } = "MISS";
    public bool RerankBypassed { get; set; }

    public string FormattedBadge => $"⚡ {EnergyJoules:F1} J ({EnergySavedPercentage:F0}% saved) • ⏱️ {TotalLatencyMs:F0}ms • 🧠 {ContextTokens} tokens • 📉 Attn: -{AttentionSavingsPercentage:F0}%";
}
