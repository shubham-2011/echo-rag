// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title EcoRAGAudit
/// @notice Stores compact immutable cryptographic commitments. Detailed RAG data stays off-chain.
/// @dev Integrity model: off-chain canonical JSON → SHA-256 → `payloadHash`; batch Merkle root → `merkleRoot`.
///      On-chain code does NOT validate RAG correctness—only that a commitment was recorded at a time by an authorized submitter.
contract EcoRAGAudit {
    struct Anchor {
        bytes32 payloadHash;
        bytes32 merkleRoot;
        uint64 anchoredAt;
        address submitter;
    }

    address public owner;
    mapping(address => bool) public isAnchorer;
    mapping(bytes32 => Anchor) private _anchors;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event AnchorRoleGranted(address indexed account);
    event AnchorRoleRevoked(address indexed account);

    /// @notice Emitted once per `entityKey` when a new anchor is created (discoverable by indexers).
    event AuditAnchored(
        bytes32 indexed entityKey,
        bytes32 indexed payloadHash,
        bytes32 merkleRoot,
        address indexed submitter,
        uint64 anchoredAt
    );

    error NotOwner();
    error NotAnchorer();
    error ZeroPayloadHash();
    error AlreadyAnchored(bytes32 entityKey);
    error ZeroAddress();

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    modifier onlyAnchorer() {
        if (!isAnchorer[msg.sender]) revert NotAnchorer();
        _;
    }

    constructor() {
        owner = msg.sender;
        isAnchorer[msg.sender] = true;
    }

    function transferOwnership(address newOwner) external onlyOwner {
        if (newOwner == address(0)) revert ZeroAddress();
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    function grantAnchorer(address account) external onlyOwner {
        if (account == address(0)) revert ZeroAddress();
        isAnchorer[account] = true;
        emit AnchorRoleGranted(account);
    }

    function revokeAnchorer(address account) external onlyOwner {
        isAnchorer[account] = false;
        emit AnchorRoleRevoked(account);
    }

    /// @notice Record a commitment for `entityKey`. Each key may be anchored at most once.
    /// @param entityKey Stable id, e.g. `keccak256(abi.encode(entityType, entityId))`.
    /// @param payloadHash SHA-256 digest of canonical off-chain JSON (32 bytes, big-endian convention off-chain).
    /// @param merkleRoot Merkle root of the batch containing this leaf, or `bytes32(0)` if not batched.
    function anchor(bytes32 entityKey, bytes32 payloadHash, bytes32 merkleRoot) external onlyAnchorer {
        if (payloadHash == bytes32(0)) revert ZeroPayloadHash();
        if (_anchors[entityKey].payloadHash != bytes32(0)) revert AlreadyAnchored(entityKey);

        uint64 ts = uint64(block.timestamp);
        _anchors[entityKey] = Anchor({
            payloadHash: payloadHash,
            merkleRoot: merkleRoot,
            anchoredAt: ts,
            submitter: msg.sender
        });

        emit AuditAnchored(entityKey, payloadHash, merkleRoot, msg.sender, ts);
    }

    function getAnchor(bytes32 entityKey) external view returns (Anchor memory) {
        return _anchors[entityKey];
    }

    function isAnchored(bytes32 entityKey) external view returns (bool) {
        return _anchors[entityKey].payloadHash != bytes32(0);
    }

    /// @notice Returns true when off-chain recomputed hashes match the stored anchor.
    function verifyAnchor(
        bytes32 entityKey,
        bytes32 payloadHash,
        bytes32 merkleRoot
    ) external view returns (bool) {
        Anchor memory stored = _anchors[entityKey];
        if (stored.payloadHash == bytes32(0)) {
            return false;
        }
        return stored.payloadHash == payloadHash && stored.merkleRoot == merkleRoot;
    }

    /// @dev Use `abi.encode` (not `encodePacked`) when deriving keys off-chain to avoid ambiguous concatenation.
    function computeEntityKey(string calldata entityType, string calldata entityId) external pure returns (bytes32) {
        return keccak256(abi.encode(entityType, entityId));
    }
}
