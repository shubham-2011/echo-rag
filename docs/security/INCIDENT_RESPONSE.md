# EcoRAG Incident Response Procedure

This is a minimum operational procedure for suspected API-key compromise, cross-tenant exposure, malicious uploads, or service-resource abuse. It does not replace organization-specific legal, regulatory, or customer-notification requirements.

## 1. Triage and contain

1. Record the discovery time, affected service/host, reporter, and observed behavior. Avoid copying API keys, bearer headers, document contents, or user prompts into the incident ticket.
2. For suspected active compromise, restrict network access to the API. If needed to stop ongoing exposure or resource exhaustion, stop the backend service while preserving its logs and deployment configuration.
3. Remove or replace compromised entries in `ECORAG_API_KEYS_JSON`, or replace `ECORAG_API_KEY` for local single-user mode. Restart the service so all requests use the updated configuration. Do not set an empty or malformed key configuration as a temporary bypass; the service should fail closed.
4. If the affected identity may have uploaded private documents, preserve the relevant tenant-specific index state only through approved, access-controlled mechanisms. Current indexes and parent documents are in-memory and are lost on process restart; there is no supported durable export or tenant deletion workflow.

## 2. Preserve evidence safely

- Preserve timestamped service, reverse-proxy, host, and deployment logs with access restricted to incident responders.
- Keep a record of the deployed build/version, container image, configuration change times, and affected API-key subject identifiers where already available.
- Do not add secrets, full prompts, retrieved text, or uploaded files to ordinary logs or reports. Hash evidence files when required by the organization's chain-of-custody process.
- Current application security logs are not a durable audit trail and may not identify every successful action. Document those limits instead of inferring that missing events did not occur.

## 3. Assess scope

1. Identify the affected key subject(s), routes, time window, deployment workers, and any reverse-proxy or network exposure.
2. Review authentication denials, security decision events, rate-limit events, process/resource telemetry, and host logs. These are limited indicators; they do not prove the absence of data access.
3. For suspected tenant leakage, determine whether an unauthorized response included another tenant's document text, IDs, or metadata. Preserve only evidence necessary for investigation and restrict access to it.
4. For suspicious uploads, record the tenant, filename, file hash, parser outcome, and `UNTRUSTED`/review status without placing document contents in the incident record.

## 4. Recover

1. Patch or reconfigure the cause and rotate/revoke affected credentials before restoring access.
2. Restart from a known-good build and confirm that API-key configuration is valid, protected routes reject missing/invalid credentials, and tenant retrieval remains isolated.
3. Re-ingest only approved clean documents. Current tenant indexes are in-memory and are not automatically restored after restart.
4. Restore network access gradually while watching for renewed authentication failures, rate-limit events, parser saturation, or unusual resource use.

## 5. Close and improve

- Maintain a timeline, impact assessment, containment/recovery actions, and unresolved questions.
- Notify system owners and affected users through the organization's approved process when evidence and applicable obligations require it.
- Add a regression test for the confirmed failure mode, update this procedure and the Phase 3 report, and track longer-term fixes such as durable tenant-aware storage, centralized quotas, audit retention, secret management, and isolated document parsing.
