# Synoptek internship PDF smoke benchmark

Source file: `D:\job related\JDS\Pre Placement Paid Internship -EOC Engineer.pdf`  
Scoped queries: `doc_ids=["Pre Placement Paid Internship -EOC Engineer.pdf"]`  
Runner: `backend/scripts/synoptek_smoke_benchmark.py`

## Latest live score

**18 / 22** (2026-10-03) after ingesting this PDF into a MiniLM index.

Q11 answer was correct (`₹50 Thousand`); the scorer originally required `50,000`. Treat as a **true RAG pass**.

| # | Question | Result | Answer excerpt |
|---|----------|--------|----------------|
| 1 | Company name | PASS | About Us Synoptek is a GSI / MSP |
| 2 | Headquartered | PASS | Irvine, CA |
| 3 | What company does | PASS | SI and MSP / IT management |
| 4 | Employees | PASS | 1100+ |
| 5 | Clients | PASS | 1200+ |
| 6 | Work location | PASS | Pune |
| 7 | Degrees | FAIL | Wrong sentence (interview advice) |
| 8 | Percentage | PASS | 65% throughout academics |
| 9 | Duration | PASS | Sep 2026–May 2027, 9 months |
| 10 | Stipend | PASS | ₹10,000 per month |
| 11 | Leave early | PASS* | ₹50 Thousand training charge |
| 12 | FTE compensation | FAIL | Returned internship **shift** not ₹3.5 LPA |
| 13 | Service agreement | PASS | 2-year after confirmation |
| 14 | Bond | PASS | ₹2 lakh |
| 15 | Round 1 | PASS | Aptitude & GD |
| 16 | Round 2 | PASS | Technical & Practical |
| 17 | Round 3 | PASS | HR Discussion |
| 18 | Technical requirements | FAIL | Job-spec intro, not Windows/Linux/TCP |
| 19 | Unfamiliar tech | PASS | Tests learned/practiced knowledge |
| 20 | CEO | PASS | Abstain |
| 21 | JISA Softech | weak | Legal notice, not a clean “not mentioned” |
| 22 | Total stipend calc | PASS | Calculated ₹90,000, labeled not in PDF |

## Not run (full 257)

Paraphrase battery, interview lists, conversational Tests A–D, ambiguous duration, adversarial system prompts, UI citation/page checks.

Conversational “it/the duration” still has **no session rewrite** in `/api/query`. HQ follow-up passed because the lexical query still hits About Us.

## Rerun

```powershell
cd backend
..\venv\Scripts\python.exe scripts\synoptek_smoke_benchmark.py
```
