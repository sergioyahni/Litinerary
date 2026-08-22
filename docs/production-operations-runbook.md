# Production Operations Runbook

This runbook defines PLU-05 incident ownership and first-response procedures for Litinerary production operations. It does not implement rollback, restore, or external alert delivery; those remain later Production-GO work.

## Ownership

Primary production incident owner: repository/application owner.

Current responsible owner: `sergioyahni`.

Until a separate on-call or platform team exists, the responsible owner owns triage, user-impact assessment, evidence preservation, and escalation decisions.

## Severity Model

- SEV-1: service unavailable, major data risk, active security risk, or production cost controls failing open.
- SEV-2: major degraded functionality, critical provider unavailable, readiness unhealthy beyond transient startup, or durable usage limiter unavailable.
- SEV-3: limited degradation, non-critical provider issue, normal rate-limit pressure, or cleanup job failure without user impact.

## General Triage

For every incident:

1. Confirm the signal from structured logs, health/readiness checks, and platform status.
2. Capture timestamps, request IDs, affected endpoint paths, status codes, provider names, and error types.
3. Preserve the relevant structured log lines and deployment/version identifiers.
4. Avoid exposing secrets in incident notes.
5. If rollback or data restore is required, hand off to PLU-06 procedures once they exist.

## Availability Alert

Confirm:

- `/api/health` response and platform health-check status.
- Recent `api_request_failed` events.
- Startup logs for import/config/database failures.

Safe first response:

- If the process is down, check platform service status and recent deploy activity.
- If startup validation fails, identify the failing configuration group without printing secrets.
- Limit traffic only if repeated failures are worsening data integrity or cost exposure.

Escalate to SEV-1 when production is unavailable for users or a security/data risk is suspected.

## Readiness Alert

Confirm:

- `/api/readiness` status.
- `readiness_checked` events.
- Database and migration readiness fields.
- Provider mode and credential-presence booleans.

Safe first response:

- For database readiness failure, check database availability and migration state.
- For provider readiness mismatch, verify feature flags and environment gates.
- Do not add external-provider fan-out to readiness while responding.

Escalate to SEV-2 when readiness remains unhealthy after a short transient period.

## Server Error Alert

Confirm:

- `api_request_completed` events with `status_code >= 500`.
- `api_request_failed` events with matching `request_id`.
- Endpoint path, method, latency, and `error_type`.

Safe first response:

- Identify whether the failure is isolated to one endpoint or global.
- Check the current deployment version and recent configuration changes.
- Consider rollback only under future PLU-06 rollback procedures.

Escalate to SEV-1 for broad outage, data risk, or security risk; otherwise use SEV-2 or SEV-3 based on impact.

## Latency Alert

Confirm:

- `latency_ms` on `api_request_completed`.
- Whether latency is general or limited to itinerary generation.
- Provider latency from `provider_call_succeeded` or `provider_call_failed`.

Safe first response:

- Check whether provider calls, database operations, or routing/POI steps dominate latency.
- Temporarily limit traffic only if queues or cost exposure are worsening.

Initial thresholds are documented in `docs/production-alerting.md` and must be tuned from real traffic.

## Provider Failure Alert

Confirm:

- `provider_call_failed` events.
- `provider_type`, `provider_name`, `operation`, `error_type`, and `warning_count`.
- Whether the error is upstream unavailable, rate limited, quota/cost blocked, bad input, or intentional provider blocking.

Safe first response:

- Check provider status pages only after confirming real provider mode is enabled.
- For quota/cost blocked events, inspect configured ceilings before raising limits.
- For user-caused bad input, do not treat the alert as infrastructure unless volume suggests abuse or product regression.

Escalate to SEV-2 when a required provider blocks core functionality.

## Usage Limiter Or Cleanup Alert

Confirm:

- `usage_limiter_failed` events.
- `usage_counter_cleanup_failed` events.
- Database readiness and `usageControls.durable` from readiness.

Safe first response:

- Treat limiter failure as operationally significant because it protects quota and cost boundaries.
- Do not bypass limiter controls in production without explicit owner approval.
- Re-run the explicit cleanup command only after confirming the configured database target and retention window.

Cleanup command:

```powershell
cd backend
python -m scripts.cleanup_usage_counters
```

Escalate to SEV-2 if limiter failures block legitimate core usage or prevent cost controls from operating.

## Evidence To Preserve

- Request IDs.
- Structured event names and fields.
- Health/readiness response status.
- Deployment/version identifier.
- Cleanup command output, if relevant.
- Any owner action taken in GitHub, Render, Auth0, or the database provider.
