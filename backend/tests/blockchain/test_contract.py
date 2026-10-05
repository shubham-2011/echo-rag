"""BC-CONTRACT-* — on-chain tests run only when a local EVM adapter is configured."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.blockchain

SOL_PATH = Path(__file__).resolve().parents[2] / "contracts" / "src" / "EcoRAGAudit.sol"


def test_bc_contract_001_source_present():
    assert SOL_PATH.is_file()
    text = SOL_PATH.read_text(encoding="utf-8")
    assert "contract EcoRAGAudit" in text
    assert "function anchor" in text
    assert "AlreadyAnchored" in text
    assert "onlyAnchorer" in text
    assert "function verifyAnchor" in text


@pytest.mark.skip(reason="Public chain adapter not implemented; enable when AUDIT_CHAIN_ENABLED + local Anvil")
def test_bc_contract_010_anchor_on_chain():
    """Placeholder for Foundry/Hardhat or web3.py against local EVM."""
    raise NotImplementedError
