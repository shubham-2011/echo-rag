"""EcoRAG Synoptek internship PDF smoke benchmark (20 core questions)."""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000"
DOC_ID = "Pre Placement Paid Internship -EOC Engineer.pdf"

SMOKE = [
    {
        "id": 1,
        "query": "What is the company name?",
        "must": [r"synoptek is|about us.{0,40}synoptek|company.{0,20}synoptek"],
        "must_not": [r"\bfaiss\b", r"energy-optimized pipeline", r"jisa", r"cryptobind"],
        "category": "fact",
    },
    {
        "id": 2,
        "query": "Where is it headquartered?",
        "must": [r"irvine"],
        "must_not": [r"\bfaiss\b"],
        "category": "followup_unresolved",
        "note": "Without conversation rewrite, 'it' may not resolve to Synoptek.",
    },
    {
        "id": 3,
        "query": "What does the company do?",
        "must": [r"systems integrator|managed it|msp|consultancy|it management"],
        "must_not": [r"energy-optimized pipeline"],
        "category": "fact",
    },
    {
        "id": 4,
        "query": "How many employees does it have?",
        "must": [r"1100"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 5,
        "query": "How many clients does it serve?",
        "must": [r"1200"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 6,
        "query": "Where is the work location?",
        "must": [r"pune"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 7,
        "query": "What degrees are eligible?",
        "must": [r"b\.?e\.?|b\.?tech|m\.?sc|mca"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 8,
        "query": "What percentage is required?",
        "must": [r"65"],
        "must_not": [r"\b50%"],
        "category": "fact",
    },
    {
        "id": 9,
        "query": "What is the internship duration?",
        "must": [r"september|sep\.?\s*2026|9\s*month"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 10,
        "query": "What is the stipend?",
        "must": [r"10,000|10000"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 11,
        "query": "What happens if I leave early?",
        "must": [r"50,000|50000|50 thousand"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 12,
        "query": "What is the FTE compensation?",
        "must": [r"3\.5"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 13,
        "query": "What is the service agreement?",
        "must": [r"2\s*-?\s*year|two year"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 14,
        "query": "What is the bond amount?",
        "must": [r"2\s*lakh|2,00,000|200000"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 15,
        "query": "What is Round 1?",
        "must": [r"aptitude|group discussion|\bgd\b"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 16,
        "query": "What is Round 2?",
        "must": [r"technical"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 17,
        "query": "What is Round 3?",
        "must": [r"hr"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 18,
        "query": "What are the technical requirements?",
        "must": [r"windows|linux|tcp|dns|dhcp|troubleshooting"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 19,
        "query": "What does the document say about unfamiliar technologies?",
        "must": [r"learn|practic|cv|resume|theoret"],
        "must_not": [],
        "category": "fact",
    },
    {
        "id": 20,
        "query": "Who is the CEO?",
        "must": [r"couldn.?t find|not (enough|found|stated)|no relevant|not mentioned"],
        "must_not": [r"\bceo\b.{0,40}\bis\b"],
        "category": "abstain",
        "note": "Must not invent a CEO name.",
    },
    {
        "id": 21,
        "query": "Does this document mention JISA Softech?",
        "must": [r"couldn.?t find|not (enough|found|stated)|does not mention|not mention"],
        "must_not": [r"jisa softech is"],
        "category": "boundary",
    },
    {
        "id": 22,
        "query": "If the stipend is ₹10,000 per month and the internship lasts 9 months, what is the total stipend over the internship?",
        "must": [r"90,000|90000"],
        "must_not": [],
        "category": "calculation",
        "note": "₹90,000 is calculated, not explicit in the PDF.",
    },
]


def normalize_money_text(text: str) -> str:
    """Map equivalent currency spellings without collapsing 50,000 vs 5,000."""

    def word_amount(match: re.Match) -> str:
        raw = match.group(1).replace(",", "")
        number = float(raw)
        unit = match.group(2).lower()
        scale = 1000.0 if unit.startswith("thousand") else 100_000.0
        value = number * scale
        as_int = int(round(value))
        return str(as_int) if abs(value - as_int) < 1e-6 else str(value)

    out = re.sub(
        r"(?:₹|rs\.?|inr)\s*(\d+(?:[.,]\d+)?)\s*(thousand|lakhs?)\b",
        word_amount,
        text,
        flags=re.I,
    )
    out = re.sub(r"\b(\d+(?:[.,]\d+)?)\s*(thousand|lakhs?)\b", word_amount, out, flags=re.I)
    out = re.sub(r"\b(\d{1,3}(?:,\d{2,3})+)\b", lambda m: m.group(1).replace(",", ""), out)
    out = re.sub(r"(?:₹|rs\.?|inr)\s*", " ", out, flags=re.I)
    return out


def post_json(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        body["_header_request_id"] = resp.headers.get("X-Request-ID")
        return body


def score_case(case: dict, data: dict) -> dict:
    answer = data.get("answer") or ""
    citations = data.get("citations") or []
    telemetry = data.get("telemetry") or {}
    rid = data.get("request_id")
    checks = []
    passed = True
    norm_answer = normalize_money_text(answer)
    for pattern in case["must"]:
        ok = bool(re.search(pattern, answer, re.I | re.S)) or bool(
            re.search(pattern, norm_answer, re.I | re.S)
        )
        checks.append({"rule": "must", "pattern": pattern, "ok": ok})
        passed = passed and ok
    for pattern in case["must_not"]:
        hit = bool(re.search(pattern, answer, re.I | re.S)) or bool(
            re.search(pattern, norm_answer, re.I | re.S)
        )
        ok = not hit
        checks.append({"rule": "must_not", "pattern": pattern, "ok": ok})
        passed = passed and ok
    source_ok = any(
        (c.get("filename") or c.get("doc_id") or "").endswith(DOC_ID) or DOC_ID in (c.get("doc_id") or "")
        for c in citations
    )
    if case["category"] != "abstain":
        checks.append({"rule": "source_doc", "pattern": DOC_ID, "ok": source_ok})
        passed = passed and source_ok
    id_ok = rid and rid == telemetry.get("request_id")
    checks.append({"rule": "request_id", "ok": bool(id_ok)})
    passed = passed and bool(id_ok)
    return {
        "id": case["id"],
        "query": case["query"],
        "pass": passed,
        "category": case["category"],
        "request_id": rid,
        "answer": answer,
        "n_sources": len(citations),
        "top_source": (citations[0].get("filename") or citations[0].get("doc_id")) if citations else None,
        "top_page": citations[0].get("page_number") if citations else None,
        "top_section": citations[0].get("section") if citations else None,
        "grounding_passed": telemetry.get("grounding_passed"),
        "energy_j": telemetry.get("estimated_joules"),
        "latency_ms": telemetry.get("latency_ms"),
        "checks": checks,
        "note": case.get("note"),
    }


def main() -> None:
    rows = []
    for case in SMOKE:
        data = post_json(
            "/api/query",
            {
                "query": case["query"],
                "retrieval_mode": "adaptive",
                "top_k": 5,
                "max_tokens": 250,
                "doc_ids": [DOC_ID],
                "session_id": "synoptek_smoke",
                "turn": case["id"],
            },
        )
        rows.append(score_case(case, data))
        mark = "PASS" if rows[-1]["pass"] else "FAIL"
        print(f"{mark} {case['id']:02d} {case['query']}")
        print(f"     {rows[-1]['answer'][:180].replace(chr(10), ' ')}")
    passed = sum(1 for r in rows if r["pass"])
    summary = {"passed": passed, "total": len(rows), "results": rows}
    out = Path(__file__).resolve().parents[1] / "tmp_synoptek_smoke.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSCORE {passed}/{len(rows)} -> {out}")


if __name__ == "__main__":
    main()
