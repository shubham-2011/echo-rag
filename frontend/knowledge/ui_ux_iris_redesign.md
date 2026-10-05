# EcoRAG Desktop — UI/UX Audit and Iris Redesign

**Date:** 2026-10-03  
**Client:** `frontend/src/EcoRag.Desktop` (C# / .NET 10 / WPF / MVVM)  
**Persona name:** Iris

This note records the visual audit of the running desktop app and the design that replaced it. Bindings, commands, and view-models were left in place. The change is presentation only.

---

## 1. Audit of the previous UI

Reviewed from the live Assistant screen (window title `EcoRAG — Energy-Aware RAG Platform`) plus the XAML for shell, chat, overview, documents, telemetry, and settings.

### Findings

1. **The conversation was the narrow column.** A 260 px nav plus a 380 px energy pane left the chat squeezed. Assistant answers wrapped early and were clipped (`F—` in the visible bubble).
2. **The same numbers were repeated.** `46.0 J` appeared in the header chips, the energy card, the scorecard, the pipeline list, and each message footer. Attention Reduction (`98%`) competed with those chips and overflowed the header.
3. **The comparison table was broken.** `BASELINE VS ECORAG` used a `Grid` with columns but no `RowDefinition`s, so labels and values stacked on one row and painted on top of each other.
4. **An empty row stayed on screen.** Energy breakdown included `Other  0.0 J`, which added height without information.
5. **Navigation had no selected state.** Overview, Documents, Chat, Telemetry, and Settings looked the same after a click. Emoji icons and text were mixed, so the rail felt unfinished.
6. **The primary action was low contrast.** Send was a gray outlined button on a dark field. There was no input placeholder.
7. **Color did not mean anything.** Mint, blue, and amber were used as decoration. The overall teal-on-navy look read as a generic operations dashboard, not an AI product.
8. **Page headers did not match.** Overview, Documents, Telemetry, and Settings each invented their own title size, button shape, and card padding.

---

## 2. Iris color persona

Iris is a dark AI console. Violet is the product. Cyan is a live signal. Mint is reserved for energy that was saved. Amber is the heavier baseline. Nothing else uses those hues.

| Token | Hex | Role |
|---|---|---|
| `AppBackgroundBrush` | `#07060E` | Window canvas |
| `SidebarBackgroundBrush` | `#0C0B14` | Navigation and energy rail |
| `CardBackgroundBrush` | `#161422` | Cards |
| `ElevatedSurfaceBrush` | `#1A1828` | Hover surfaces |
| `InputSurfaceBrush` | `#12101C` | Composer |
| `NavActiveBrush` | `#2A2348` | Selected nav and user bubble |
| `CardBorderBrush` | `#2A2740` | Hairline borders |
| `StrongBorderBrush` | `#3A3654` | Composer and meter tracks |
| `TextPrimaryBrush` | `#F4F2FF` | Titles and values |
| `TextSecondaryBrush` | `#B7B3CC` | Body and secondary labels |
| `TextMutedBrush` | `#7C7894` | Section labels |
| `AccentPrimaryBrush` | `#A78BFA` | Brand, selected nav, Send, assistant name |
| `AccentMutedBrush` | `#6D5BD0` | Pressed violet |
| `InfoPrimaryBrush` / `InfoBlueBrush` | `#67E8F9` | Connected, latency, retrieval |
| `EmeraldBrush` / `SuccessGreenBrush` | `#34D399` | Joules saved and reduction only |
| `DarkEmeraldBrush` | `#059669` | Deeper mint, unused as a fill |
| `AmberBrush` / `WarningPrimaryBrush` | `#FBBF24` | Baseline energy |
| `WarningOrangeBrush` | `#FB923C` | Generation bar (the expensive stage) |
| `ErrorPrimaryBrush` / `ErrorRedBrush` | `#FB7185` | Standard-RAG side of telemetry |

Typeface: `Segoe UI Variable, Segoe UI`.

Shared styles live in `App.xaml`: `CardStyle`, `PageTitleStyle`, `PageSubtitleStyle`, `SectionLabelStyle`, `SidebarButtonStyle`, `SidebarCategoryStyle`, `BadgeStyle`, `PrimaryButtonStyle`, `GhostButtonStyle`, and a rounded `ProgressBar` template (`PART_Track` / `PART_Indicator`).

---

## 3. Layout after the redesign

### Shell (`MainWindow.xaml`)

- Default window `1360×860`, minimum `1100×680`.
- Rail width `232`. Brand mark is a violet tile with the letter E and the caption `Iris console`.
- Items: Overview, Documents, Assistant, Telemetry, Settings. The active item uses `NavActiveBrush` and violet text, driven by `MainViewModel.ActiveSection`.
- Status bar: mint = API connected, cyan = FAISS ready, violet = reranker active. Version label reads `EcoRAG  ·  Iris`.

### Assistant (`ChatView.xaml`)

- Chat is the wide column. Energy is a `340` px rail on the right.
- Header chips are only Energy, Latency, and Tokens. Attention Reduction was removed from the header because it did not fit and duplicated the rail.
- User bubbles align right (`NavActiveBrush`, corner `16,16,4,16`). Assistant copy is left-aligned, width up to `720`, with sources and a one-line telemetry footer (`J`, `% saved`, `ms`, tokens).
- Composer placeholder: `Ask a question about your documents`. Send uses `PrimaryButtonStyle`.
- Right rail, top to bottom:
  1. Actual energy `46.0 J`, saved `29.2 J`, reduction `38.8%`, baseline vs EcoRAG meters.
  2. Where it went: Retrieval `8.2 J`, Fusion `2.1 J`, Rerank `6.7 J`, Context `3.4 J`, Generation `25.6 J`. The empty Other row is gone.
  3. Compare table with real row definitions: Energy, Latency, Tokens, Context, Retrieved. Baseline column is amber on energy; EcoRAG energy is mint.

These joule and token figures are the same sample values that were already hardcoded in the view. They are not new measurements.

### Other screens

- **Overview:** four equal cards (documents, chunks, energy saved, average latency) and a recent-sources list. Same bindings as before.
- **Documents:** title and subtitle aligned to the page styles. Browse uses the primary button. Refresh uses the ghost button. Upload and list bindings are unchanged.
- **Telemetry:** page title and subtitle only. Comparison cards and pipeline bars pick up Iris colors through the existing resource keys.
- **Settings:** page title and subtitle. Test connection uses the primary button. Endpoint, status, and model bindings are unchanged.

---

## 4. Files changed

| File | Change |
|---|---|
| `frontend/src/EcoRag.Desktop/App.xaml` | Iris brushes and shared control styles |
| `frontend/src/EcoRag.Desktop/MainWindow.xaml` | Narrower rail, selected state, status bar |
| `frontend/src/EcoRag.Desktop/Views/ChatView.xaml` | Conversation-first layout and fixed comparison grid |
| `frontend/src/EcoRag.Desktop/Views/DashboardView.xaml` | Shared page and card styles |
| `frontend/src/EcoRag.Desktop/Views/DocumentsView.xaml` | Header and button styles |
| `frontend/src/EcoRag.Desktop/Views/TelemetryView.xaml` | Header copy |
| `frontend/src/EcoRag.Desktop/Views/SettingsView.xaml` | Header and test-connection button |

`dotnet build` of `EcoRag.Desktop.csproj` succeeded with 0 warnings and 0 errors after the change. View-models and API calls were not modified.
