namespace EcoRag.Desktop.Models;

public class Citation
{
    public string DocumentName { get; set; } = string.Empty;
    public string ChunkId { get; set; } = string.Empty;
    public int ChunkIndex { get; set; }
    public int? PageNumber { get; set; }
    public double RelevanceScore { get; set; }
    public string Snippet { get; set; } = string.Empty;
    public string PageLabel => PageNumber is int page ? $"p.{page}" : "p.?";
}
