# EcoRAGAudit — Solidity Security & Design Audit

**Contract:** `backend/contracts/src/EcoRAGAudit.sol`  
**Scope:** Pre-deployment review (no deploy performed in this audit).  
**Claim:** Blockchain provides **integrity / provenance** of an anchored commitment, **not** correctness of RAG answers.

---

## Executive summary

The original contract stored only **32-byte hashes** (good separation from RAG content) but allowed **anyone** to anchor and **overwrite** existing keys, which contradicts an “immutable proof” story. The revised contract adds **anchorer access control**, **one-shot anchoring per `entityKey`**, explicit **verification** and **entity key** helpers, and clearer **events**. Off-chain hashing must stay aligned with `backend/src/audit/canonicalizer.py` (canonical JSON + SHA-256 hex → `bytes32`).

---

## Question-by-question evaluation

### 1. What exactly is being anchored?

**Off-chain:** A canonical JSON audit record (experiment manifest, configuration snapshot, telemetry summary, etc.).

**On-chain:** Three commitments under a logical **`entityKey`**:

| Field | Meaning |
|--------|---------|
| `payloadHash` | SHA-256 of canonical JSON for that record |
| `merkleRoot` | Root of the Merkle batch that included this leaf (or zero if N/A) |
| Metadata | `anchoredAt`, `submitter` (who paid for the tx) |

Not anchored on-chain: documents, prompts, chunks, answers, embeddings, full telemetry traces.

### 2. What data is stored on-chain?

Per `entityKey`: `payloadHash`, `merkleRoot`, `uint64 anchoredAt`, `address submitter`. Plus access-control mappings (`owner`, `isAnchorer`). **~2–3 storage slots per anchor** (cold write on first anchor).

### 3. Sensitive / private RAG data on-chain?

**No full content** in the contract. **Risk:** If operators anchor hashes of records that still contain PII inside the JSON, the hash is a **commitment** (not reversible directly) but could aid **confirmation attacks** if the plaintext leaks elsewhere. Policy: anchor **redacted manifests** only (hashes of evaluation summaries, not raw prompts).

### 4. Is hash construction deterministic?

**On-chain:** Does not hash JSON; accepts `bytes32` from caller.

**Off-chain (authoritative):** `canonical_json()` → UTF-8 bytes → SHA-256 (`canonicalizer.py`). Deterministic if schema version and payload types are stable.

**Gap:** Solidity never recomputes SHA-256 of JSON; **adapter layer** must convert hex digest to `bytes32` consistently (big-endian byte order of the 32 hash bytes).

### 5. Can an anchor be reproduced off-chain?

**Yes**, given the same canonical payload and Merkle batch rules as `merkle.py`. Recompute hash and root, derive `entityKey` with `computeEntityKey(type, id)` or equivalent `keccak256(abi.encode(type, id))`.

### 6. Can an existing anchor be verified?

**Yes:** `verifyAnchor(entityKey, payloadHash, merkleRoot)` or read `getAnchor` and compare locally. Merkle membership uses off-chain `verify_merkle_proof` against stored root.

### 7. Can the same request be anchored twice?

**Original:** Yes — second `anchor` **overwrote** the mapping (immutable claim broken).

**Revised:** No — `AlreadyAnchored(entityKey)` revert on second write.

### 8. Is replay protection required?

**Transaction replay** is handled by the chain (nonce). **Logical replay** (re-anchor same experiment) is blocked by one-shot `entityKey`. New versions need a **new entity id** or version suffix in `entityId`.

### 9. Who is authorized to create anchors?

**Original:** Any `msg.sender`.

**Revised:** Only addresses with `isAnchorer[addr] == true`; owner grants/revokes.

### 10. Is access control implemented correctly?

**Revised:** Owner + anchorer role; custom errors; zero-address checks on grant/transfer. **Not included:** pausing, multisig, timelock (future hardening).

### 11. Are events emitted for auditability?

**Yes:** `AuditAnchored` with indexed `entityKey`, `payloadHash`, `submitter` for indexers. Role/ownership events for governance audit.

### 12. Are timestamps used correctly?

`block.timestamp` for **approximate** anchoring time (miner skew ±15s). Not used for cryptographic security. Stored as `uint64`.

### 13. Are request IDs handled safely?

There is no native “request_id” field. **`entityKey`** must be derived safely off-chain (`abi.encode`, not ambiguous `encodePacked` concatenation). Optional helper: `computeEntityKey(string entityType, string entityId)`.

EcoRAG `request_id` (e.g. `rag_…`) can be part of `entityId` string when anchoring a query run.

### 14. Are hashes `bytes32` where appropriate?

**Yes** for `entityKey`, `payloadHash`, `merkleRoot`.

### 15. Is gas usage reasonable?

Single-anchor tx: one cold SSTORE (new key) + event LOG. **No loops, no strings, no on-chain Merkle.** Suitable for periodic batch anchors, not per-token RAG.

### 16. Can old anchors be queried?

**Per key:** `getAnchor` / `isAnchored` returns the **sole** immutable record.

**History:** Overwrites removed in revised contract; earlier versions are only recoverable from **event logs** if someone indexed the chain before overwrite (original risk).

### 17. Can a verifier prove off-chain result ↔ on-chain anchor?

**Yes:** Canonicalize → hash → compare to `payloadHash`; Merkle proof → compare to `merkleRoot`; optional `verifyAnchor` view.

### 18. Mutable state vs “immutable proof”?

**Original:** Mutable mapping overwrite.

**Revised:** Anchor payload immutable after first success; only **roles/owner** mutable (governance).

### 19. Hash collision via ambiguous encoding?

Contract does not concatenate payloads. **Off-chain risk:** using non-canonical JSON or `encodePacked`-style key derivation. Mitigation: canonical JSON + `abi.encode` for keys.

### 20. `abi.encode` / `abi.encodePacked` safety?

Contract uses **`abi.encode`** in `computeEntityKey` only. **No `encodePacked`** on variable-length data in hashing paths.

### 21. Unnecessary on-chain fields?

`submitter` and `merkleRoot` are optional for minimalism but **useful for audit** (who anchored, batch context). `merkleRoot` may be zero for single-leaf workflows.

### 22. Separation: RAG / telemetry / evaluation / proof / anchor?

| Layer | Location |
|--------|-----------|
| RAG runtime | Off-chain API |
| Telemetry / traces | Off-chain logs + DB |
| Evaluation | Off-chain |
| Canonical record + hash | Off-chain (`audit` service) |
| Public commitment | On-chain `anchor()` |

Clean separation **if** operators only pass hashes, not calldata blobs.

---

## Recommended off-chain → on-chain flow

```
request → RAG → answer → telemetry → evaluation
                         ↓
              canonical JSON record (redacted)
                         ↓
              payloadHash = SHA256(canonical)
              merkleRoot  = Merkle(batch leaves)
              entityKey   = keccak256(abi.encode(entityType, entityId))
                         ↓
              EcoRAGAudit.anchor(entityKey, payloadHash, merkleRoot)
```

Verification:

```
record → canonical_json → hash → compare getAnchor / verifyAnchor
       → merkle_proof → verify_merkle_proof → merkleRoot
```

---

## Fixes applied (pre-deploy)

1. **Revert on duplicate `entityKey`** (`AlreadyAnchored`).
2. **`onlyAnchorer`** + owner role management.
3. **`verifyAnchor`**, **`isAnchored`**, **`computeEntityKey`** helpers.
4. **Custom errors** and NatSpec; **`merkleRoot` not indexed** (3 indexed event slots used for entityKey, payloadHash, submitter).
5. **Solidity tests** via Hardhat in `backend/contracts/` (run before any deploy).

---

## Out of scope (not claims)

- RAG answer correctness, retrieval quality, or telemetry accuracy.
- Private chain data availability (IPFS / DB still required to show plaintext).
- On-chain Merkle verification (done off-chain to save gas).

---

## Test plan (must pass before deploy)

See `backend/contracts/test/EcoRAGAudit.test.js` — anchor creation, duplicate revert, unauthorized caller, hash verification, events, invalid zero hash, entity key determinism, retrieval, gas snapshot.

Run:

```bash
cd backend/contracts
npm install
npx hardhat test
```
