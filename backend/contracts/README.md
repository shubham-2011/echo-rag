# EcoRAGAudit smart contract

Compact on-chain commitments for off-chain audit records. **Do not deploy** until Hardhat tests pass.

## Audit

See [frontend/knowledge/ecorag_audit_solidity_security_audit.md](../../frontend/knowledge/ecorag_audit_solidity_security_audit.md).

## Tests

```bash
cd backend/contracts
npm install
npx hardhat test
```

## Off-chain verification

1. Build canonical JSON (`src/audit/canonicalizer.py`).
2. `payloadHash` = 32-byte SHA-256 of UTF-8 canonical JSON.
3. `merkleRoot` from `src/audit/merkle.py` (or `bytes32(0)` if not batched).
4. `entityKey` = `keccak256(abi.encode(entityType, entityId))` — same as `computeEntityKey` on-chain.
5. Call `verifyAnchor(entityKey, payloadHash, merkleRoot)` or compare `getAnchor`.
