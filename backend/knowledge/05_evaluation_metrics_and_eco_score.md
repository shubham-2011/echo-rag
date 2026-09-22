# 05. Evaluation Metrics & The EcoRAG Score

Benchmarking EcoRAG requires measuring both **Quality Metrics** (how good the system is) and **Physical Resource Metrics** (how much it costs the machine and the planet). This document details each metric, the mathematical formulations, and composite scoring functions.

---

## 1. Quality Evaluation Metrics

```
                     ┌───────────────────────────────────┐
                     │          QUALITY METRICS          │
                     └─────────────────┬─────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
         ┌─────────────────────┐               ┌─────────────────────┐
         │  Retrieval Quality  │               │ Answer Correctness  │
         └──────────┬──────────┘               └──────────┬──────────┘
                    │                                     │
           • Recall@K                            • Semantic Similarity
           • Hit Rate@K                          • Faithfulness (RAGAS)
           • MRR (Mean Recip. Rank)              • Answer Relevance
           • Context Precision                   • Exact Match / F1
```

### 1.1. Retrieval Metrics
- **Recall@K:** The proportion of ground-truth relevant chunks retrieved within the Top-$K$ results:
  $$\text{Recall@K} = \frac{|\text{Retrieved Chunks}_{1..K} \cap \text{Relevant Chunks}|}{|\text{Relevant Chunks}|}$$
- **Mean Reciprocal Rank (MRR):** Measures how high the first relevant chunk appears in the ranked list:
  $$\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$
  *Where $\text{rank}_i$ is the position of the first relevant chunk for query $i$.*
- **Hit Rate@K:** Binary indicator (1 if at least one ground-truth document is in Top-$K$, 0 otherwise).

### 1.2. Answer Correctness Metrics
- **Faithfulness (Groundedness):** Measures whether all claims in the generated response can be directly inferred from the retrieved context (prevents hallucinations).
- **Answer Relevance:** Evaluates whether the generated response directly answers the user's question without extraneous tangents.
- **Semantic Answer Similarity (SAS):** Embedding cosine similarity between the generated answer and the reference ground-truth answer:
  $$\text{SAS}(y, \hat{y}) = \cos\left(E(y), E(\hat{y})\right)$$

---

## 2. Physical Resource & Telemetry Metrics

```
┌────────────────────────────────────────────────────────────────────────┐
│                        RESOURCE TELEMETRY METRICS                      │
├───────────────────┬──────────────┬─────────────────────────────────────┤
│ Metric            │ Unit         │ Measurement Mechanism               │
├───────────────────┼──────────────┼─────────────────────────────────────┤
│ 1. Energy Consumed│ Watt-hours   │ CodeCarbon / PyJoules / RAPL / NVML │
│ 2. Total Latency  │ Seconds (s)  │ Python `time.perf_counter()`        │
│ 3. TTFT           │ Milliseconds │ Time to first streamed token        │
│ 4. Host RAM (RSS) │ Megabytes/GB │ `psutil.Process().memory_info().rss`│
│ 5. GPU VRAM       │ Megabytes/GB │ `torch.cuda.max_memory_allocated()` │
│ 6. Prompt Tokens  │ Integer      │ Tokenizer length of injected prompt │
│ 7. Generated Token│ Integer      │ Tokenizer count of LLM answer       │
│ 8. Financial Cost │ Dollars/INR  │ Token cost + GPU power cost in kWh  │
└───────────────────┴──────────────┴─────────────────────────────────────┘
```

### Measuring Energy Consumption
- **CodeCarbon:** Tracks carbon emissions and energy (kWh) based on hardware TDP and regional grid carbon intensity.
- **PyJoules / Intel RAPL:** Reads microjoules directly from CPU/DRAM MSR hardware registers.
- **pynvml (NVIDIA Management Library):** Reads instantaneous GPU power draw (milliwatts) sampled across the query execution duration:
  $$\text{Energy (Joules)} = \int_{0}^{T} P_{\text{GPU}}(t) \, dt$$
  $$\text{Energy (Watt-hours)} = \frac{\text{Joules}}{3600}$$

---

## 3. Cost Per Successful Answer

Cost must account for both software API usage and physical hardware electricity:

$$\text{Cost}_{\text{Query}} = \text{Cost}_{\text{Tokens}} + \text{Cost}_{\text{Hardware Electricity}}$$

Where:
- $\text{Cost}_{\text{Tokens}} = (N_{\text{prompt}} \times \text{Rate}_{\text{input}}) + (N_{\text{completion}} \times \text{Rate}_{\text{output}})$
- $\text{Cost}_{\text{Hardware Electricity}} = \text{Energy (kWh)} \times \text{Tariff Rate (per kWh)}$

---

## 4. Multi-Objective Optimization & The Eco Score

To compare configurations fairly, we define a composite objective function.

### 4.1. Conceptual Eco Score
$$\text{Eco Score} = \frac{\text{Answer Correctness}}{\text{Resource Consumption}}$$

### 4.2. Multi-Objective Weighted Formulation
Because different organizations prioritize latency, energy, or cost differently, metrics are min-max normalized across all experimental runs and combined using configurable weights:

$$\text{EcoRAG Score} = w_{\text{acc}} \cdot A_{\text{norm}} - \left( w_{\text{eng}} \cdot E_{\text{norm}} + w_{\text{lat}} \cdot L_{\text{norm}} + w_{\text{cost}} \cdot C_{\text{norm}} + w_{\text{ram}} \cdot R_{\text{norm}} \right)$$

#### Recommended Research Baseline Weights:
- **Accuracy ($w_{\text{acc}}$):** $40\%$ ($0.40$)
- **Energy Consumption ($w_{\text{eng}}$):** $20\%$ ($0.20$)
- **Latency ($w_{\text{lat}}$):** $20\%$ ($0.20$)
- **Financial Cost ($w_{\text{cost}}$):** $15\%$ ($0.15$)
- **RAM Footprint ($w_{\text{ram}}$):** $5\%$ ($0.05$)

> [!NOTE]
> In all academic publications and reporting, **individual metrics must always be reported alongside the composite Eco Score** to maintain scientific transparency.

---

## 5. Pareto Frontier Analysis

A central analytical deliverable of EcoRAG is identifying the **Pareto Optimal Frontier**:

```text
  Accuracy (%)
      100 │                 ● Config B (Optimal Tradeoff: 94%, 2.2 Wh)
          │               ╱
       90 │             ● Config A (Baseline: 88%, 1.2 Wh)
          │            ╱                                 ● Config C (Over-engineered: 95%, 7.8 Wh)
       80 │           ╱
          │          ● Config D (Suboptimal: 78%, 3.5 Wh)
       70 │
          └───────────────────────────────────────────────────► Energy (Watt-hours)
          0          2          4          6          8
```

- **Config A:** High efficiency, moderate accuracy.
- **Config B (Pareto Knee):** 94% accuracy with only 2.2 Wh (the sweet spot).
- **Config C:** Gains only 1% extra accuracy (95%), but consumes **3.5× more energy** (7.8 Wh) due to heavy reranking and huge context windows.
- EcoRAG rigorously proves that Config C represents wasteful over-engineering.
