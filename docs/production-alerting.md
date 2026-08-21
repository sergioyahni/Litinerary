# Production Alerting Policy

PLU-05 defines the alert contract that future Render, log, or monitoring integrations must consume. It does not claim that an external alert destination is already provisioned.

## Signal Source

Primary signals are structured JSON log events emitted by the backend logger `litinerary`, plus `/api/health` and `/api/readiness` probe results.

Every structured event is expected to include stable operational fields where applicable:

- `event`
- `category`
- `app_env`
- `request_id`
- `operation`
- `provider_type`
- `provider_name`
- `status_code`
- `latency_ms`
- `error_type`
- `success`
- `estimated_cost_usd`
- `warning_count`

Logs must not include access tokens, API keys, Authorization headers, passwords, JWTs, full prompts, arbitrary user input, raw provider responses, or authenticated user IDs by default.

## Alerts

### Availability

Alert when production `/api/health` fails repeatedly for 3 consecutive checks or for 2 minutes, whichever the monitoring platform can express more reliably.

Operator action: confirm the deployed service process is running, inspect `api_request_failed` and platform startup logs, and preserve affected request IDs.

### Readiness

Alert when `/api/readiness` remains non-ready for more than 5 minutes in production.

Operator action: inspect the readiness payload for the failed check group, especially `database.status`, migration status, provider modes, and usage-control posture. Do not page for brief deployment warmup transients.

### Server Errors

Alert on sustained HTTP 5xx responses from `api_request_completed` or any `api_request_failed` burst.

Initial threshold: 5 or more 5xx responses in 5 minutes, or any 5xx rate above 5 percent for 10 minutes.

Do not alert on every individual 4xx. User-caused validation failures and normal authorization failures are not infrastructure incidents by themselves.

### Latency

Alert on sustained API latency above an initial operational threshold of 2000 ms for general API requests or 10000 ms for itinerary generation.

These are initial thresholds only and must be tuned after real traffic exists.

### Provider Failures

Alert on sustained `provider_call_failed` events for required providers when failures are classified as:

- upstream unavailable
- rate limited
- quota or cost blocked
- provider not configured when real provider mode is expected
- external calls blocked unexpectedly for the active environment

Do not page for user-caused provider 4xx equivalents such as bad input, unsafe input, too many stops, or unsupported batch size unless they reveal a product defect or a sudden abnormal spike.

### Usage Limiter And Budget Guard

Alert immediately on `usage_limiter_failed` or `usage_counter_cleanup_failed` in production. Limiter failure can affect rate, quota, and cost controls.

Normal `rate_limit_blocked` events are not incidents unless they spike unexpectedly or block a known legitimate flow.

### Cost And Budget

Track `estimated_cost_usd` on provider and usage-policy events. Alert when estimated provider cost approaches an approved daily ceiling or when `provider_cost_budget` blocks production traffic.

Do not infer exact provider billing from these estimates. Reconcile with provider billing dashboards when real providers are enabled.

## Deferred Delivery

External alert routing, notification channels, escalation schedules, dashboards, and retention settings are deferred until real staging and production infrastructure exists.
