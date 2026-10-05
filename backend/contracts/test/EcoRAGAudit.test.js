const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("EcoRAGAudit", function () {
  let audit;
  let owner;
  let anchorer;
  let stranger;

  const entityKey = ethers.keccak256(
    ethers.AbiCoder.defaultAbiCoder().encode(
      ["string", "string"],
      ["experiment", "EXP-001"]
    )
  );
  const payloadHash = ethers.hexlify(ethers.randomBytes(32));
  const merkleRoot = ethers.hexlify(ethers.randomBytes(32));

  beforeEach(async function () {
    [owner, anchorer, stranger] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("EcoRAGAudit");
    audit = await Factory.deploy();
    await audit.grantAnchorer(anchorer.address);
  });

  it("creates an anchor and stores retrievable data", async function () {
    await expect(audit.connect(anchorer).anchor(entityKey, payloadHash, merkleRoot))
      .to.emit(audit, "AuditAnchored")
      .withArgs(entityKey, payloadHash, merkleRoot, anchorer.address, (ts) => ts > 0n);

    const stored = await audit.getAnchor(entityKey);
    expect(stored.payloadHash).to.equal(payloadHash);
    expect(stored.merkleRoot).to.equal(merkleRoot);
    expect(stored.submitter).to.equal(anchorer.address);
    expect(await audit.isAnchored(entityKey)).to.equal(true);
  });

  it("reverts duplicate anchor for the same entityKey", async function () {
    await audit.connect(anchorer).anchor(entityKey, payloadHash, merkleRoot);
    const otherHash = ethers.hexlify(ethers.randomBytes(32));
    await expect(
      audit.connect(anchorer).anchor(entityKey, otherHash, merkleRoot)
    ).to.be.revertedWithCustomError(audit, "AlreadyAnchored");
  });

  it("rejects unauthorized anchor attempts", async function () {
    await expect(
      audit.connect(stranger).anchor(entityKey, payloadHash, merkleRoot)
    ).to.be.revertedWithCustomError(audit, "NotAnchorer");
  });

  it("verifyAnchor matches off-chain recomputed hashes", async function () {
    await audit.connect(anchorer).anchor(entityKey, payloadHash, merkleRoot);
    expect(await audit.verifyAnchor(entityKey, payloadHash, merkleRoot)).to.equal(true);
    const wrong = ethers.hexlify(ethers.randomBytes(32));
    expect(await audit.verifyAnchor(entityKey, wrong, merkleRoot)).to.equal(false);
    expect(await audit.verifyAnchor(entityKey, payloadHash, wrong)).to.equal(false);
  });

  it("verifyAnchor returns false for missing anchor", async function () {
    const missingKey = ethers.keccak256(ethers.toUtf8Bytes("missing"));
    expect(await audit.verifyAnchor(missingKey, payloadHash, merkleRoot)).to.equal(false);
  });

  it("emits AuditAnchored with indexed fields discoverable from receipt", async function () {
    const tx = await audit.connect(anchorer).anchor(entityKey, payloadHash, merkleRoot);
    const receipt = await tx.wait();
    const ev = receipt.logs
      .map((log) => {
        try {
          return audit.interface.parseLog(log);
        } catch {
          return null;
        }
      })
      .find((parsed) => parsed && parsed.name === "AuditAnchored");
    expect(ev).to.not.equal(undefined);
    expect(ev.args.entityKey).to.equal(entityKey);
    expect(ev.args.payloadHash).to.equal(payloadHash);
  });

  it("reverts on zero payload hash", async function () {
    await expect(
      audit.connect(anchorer).anchor(entityKey, ethers.ZeroHash, merkleRoot)
    ).to.be.revertedWithCustomError(audit, "ZeroPayloadHash");
  });

  it("computeEntityKey is deterministic", async function () {
    const a = await audit.computeEntityKey("experiment", "EXP-001");
    const b = await audit.computeEntityKey("experiment", "EXP-001");
    expect(a).to.equal(b);
    expect(a).to.equal(entityKey);
    const c = await audit.computeEntityKey("experiment", "EXP-002");
    expect(c).to.not.equal(a);
  });

  it("returns empty anchor struct before first anchor", async function () {
    const freshKey = ethers.keccak256(ethers.toUtf8Bytes("fresh"));
    const stored = await audit.getAnchor(freshKey);
    expect(stored.payloadHash).to.equal(ethers.ZeroHash);
    expect(await audit.isAnchored(freshKey)).to.equal(false);
  });

  it("anchor gas stays within a reasonable bound", async function () {
    const tx = await audit.connect(anchorer).anchor(entityKey, payloadHash, merkleRoot);
    const receipt = await tx.wait();
    expect(receipt.gasUsed).to.be.lessThan(250000n);
  });

  it("owner can revoke anchorer role", async function () {
    await audit.revokeAnchorer(anchorer.address);
    await expect(
      audit.connect(anchorer).anchor(entityKey, payloadHash, merkleRoot)
    ).to.be.revertedWithCustomError(audit, "NotAnchorer");
  });
});
