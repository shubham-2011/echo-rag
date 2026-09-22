namespace EcoRag.Desktop.Models;

public class Citation
{
    public string DocumentName { get; set; } = string.Empty;
    public int ChunkIndex { get; set; }
    public int PageNumber { get; set; } = 1;
    public double RelevanceScore { get; set; }
    public string Snippet { get; set; } = string.Empty;
}
