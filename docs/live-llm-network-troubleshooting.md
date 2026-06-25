# Live LLM Network Troubleshooting

## Purpose

This runbook diagnoses the local connectivity blocker for controlled non-production
live LLM smoke tests. It must not be used to make an itinerary-generation request,
call `/v1/chat/completions`, print secrets, or bypass live-provider gates.

Current blocker:

- `dnsOk=True`
- `tcp443Ok=False`
- `httpsOk=False`
- `backendPythonHttpsOk=False`
- `networkPreflightReady=False`

This means `api.openai.com` resolves, but outbound TCP 443 / HTTPS from this
environment fails before the backend receives an authenticated provider response.
Likely causes include firewall policy, proxy or VPN requirements, corporate
network egress controls, TLS/certificate trust, local security software, or
backend process environment inheritance.

If any real API key appeared in a tracked file, example file, docs, logs, terminal
transcript, or shared evidence, revoke or rotate that key outside the repository
before any further live smoke attempt.

## Preflight Field Meanings

- `loadedEnvSource`: local env source loaded by the preflight. This must not print
  secret values.
- `endpointScheme`: expected to be `https`.
- `endpointHost`: provider host, currently `api.openai.com`.
- `endpointBasePath`: provider base path, currently `/v1`.
- `timeoutSeconds`: timeout used by the network preflight.
- `httpProxyPresent`, `httpsProxyPresent`, `noProxyPresent`: boolean-only proxy
  environment presence checks. Values are intentionally not printed.
- `sslCertFilePresent`, `sslCertDirPresent`, `requestsCaBundlePresent`:
  boolean-only certificate environment presence checks.
- `dnsOk`: DNS resolution for the provider host succeeded.
- `tcp443Ok`: direct TCP 443 connection to the provider host succeeded.
- `httpsOk`: HTTPS request to the configured base URL succeeded or returned a
  reachable HTTP status.
- `backendPythonSource`: Python interpreter used for backend-style reachability.
- `backendPythonHttpsOk`: backend Python can reach the provider base URL over
  HTTPS without sending an API key.
- `backendPythonSslDefaultVerifyPathsPresent`: backend Python has default SSL
  CA paths available.
- `networkPreflightReady`: all required network checks passed.

Required pass condition before another live smoke retry:

- `tcp443Ok=True`
- `httpsOk=True`
- `backendPythonHttpsOk=True`
- `networkPreflightReady=True`

## Safe Automated Check

Run from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\live_llm_network_preflight.ps1
```

This check must not send `LLM_API_KEY` and must not call `/v1/chat/completions`.
It may perform DNS, TCP, and unauthenticated HTTPS reachability checks only.

## Manual Windows Diagnostics

Run these only in a trusted local terminal. Do not paste or print API keys or
proxy credentials.

DNS lookup:

```powershell
Resolve-DnsName api.openai.com
```

TCP 443 connectivity:

```powershell
Test-NetConnection api.openai.com -Port 443
```

HTTPS reachability without API key:

```powershell
try {
  $response = Invoke-WebRequest -Uri "https://api.openai.com/v1" -Method Get -TimeoutSec 10
  "httpsOk=True status=$($response.StatusCode)"
} catch {
  if ($_.Exception.Response) {
    "httpsOk=True status=$([int]$_.Exception.Response.StatusCode)"
  } else {
    "httpsOk=False category=network_or_tls"
  }
}
```

Proxy presence with values redacted:

```powershell
"HTTP_PROXY present=$([bool]$env:HTTP_PROXY)"
"HTTPS_PROXY present=$([bool]$env:HTTPS_PROXY)"
"NO_PROXY present=$([bool]$env:NO_PROXY)"
```

Backend Python HTTPS reachability without API key:

```powershell
cd backend
..\venv\Scripts\python.exe -c "import urllib.request, urllib.error; url='https://api.openai.com/v1';\
try:\
 r=urllib.request.urlopen(url, timeout=10); print('backendPythonHttpsOk=True status=%s' % r.status)\
except urllib.error.HTTPError as e: print('backendPythonHttpsOk=True status=%s' % e.code)\
except Exception as e: print('backendPythonHttpsOk=False category=%s' % e.__class__.__name__)"
```

If PowerShell succeeds but backend Python fails, focus on Python certificate trust,
proxy inheritance, or interpreter selection. If both fail, focus on firewall,
VPN, proxy, DNS policy, local security software, or network egress rules.

## Proxy Environment Guidance

Some networks require outbound HTTPS through a proxy. If required, set proxy
variables only in a trusted local shell or an ignored local env file such as
`.env.development.local`.

Do not commit proxy URLs. Proxy URLs may contain usernames, passwords, tokens, or
internal hostnames.

PowerShell session-only example with placeholders:

```powershell
$env:HTTPS_PROXY="<set locally if required>"
$env:HTTP_PROXY="<set locally if required>"
$env:NO_PROXY="127.0.0.1,localhost"
```

Ignored local env example with placeholders only:

```dotenv
HTTPS_PROXY=<set locally if required>
HTTP_PROXY=<set locally if required>
NO_PROXY=127.0.0.1,localhost
```

Verify only boolean proxy presence:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\live_llm_network_preflight.ps1
```

Expected proxy reporting is boolean only, for example `httpsProxyPresent=True`.
The proxy value itself must not be printed.

## TLS And Certificate Guidance

Common Windows/Python TLS causes:

- Corporate TLS inspection requires a corporate CA certificate.
- Python may not trust the same CA roots as Windows or the browser.
- `SSL_CERT_FILE`, `SSL_CERT_DIR`, or `REQUESTS_CA_BUNDLE` may need to point to an
  approved local CA bundle.
- VPN or endpoint security software may intercept TLS or block unknown clients.

If your organization requires a custom CA bundle, configure it locally only:

```powershell
$env:SSL_CERT_FILE="<path to approved local CA bundle>"
$env:REQUESTS_CA_BUNDLE="<path to approved local CA bundle>"
```

Do not disable TLS verification. Disabling certificate verification would weaken
provider-boundary safety and is not acceptable for smoke tests, staged internal
testing, beta, or production.

## Backend Process Inheritance Checklist

The smoke backend must see the same network, proxy, certificate, and timeout
environment as the shell that passed preflight.

Use these scripts from the repository root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\live_llm_network_preflight.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\live_llm_smoke_preflight.ps1 -RequireLiveReady
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\live_llm_smoke_backend.ps1
```

Checklist:

- `.env.development.local` is ignored by Git.
- `live_llm_network_preflight.ps1` loads the same env source as smoke preflight.
- Proxy and certificate variables appear only as booleans in preflight output.
- Backend Python source is the expected local backend interpreter.
- `LLM_BASE_URL` is `https://api.openai.com/v1` or another approved compatible
  base URL.
- `LLM_TIMEOUT_SECONDS` is visible if explicitly configured.
- No other live providers are enabled.

## Retry Criteria

Another live smoke retry is allowed only after all of these are true:

- Any exposed real key has been revoked or rotated by the user.
- `scripts/live_llm_network_preflight.ps1` reports `networkPreflightReady=True`.
- `backendPythonHttpsOk=True`.
- `scripts/live_llm_smoke_preflight.ps1 -RequireLiveReady` passes.
- The model is confirmed Chat Completions-compatible.
- Endpoint/base URL composition remains correct.
- Other live providers remain disabled.
- Rollback to mock/offline mode is ready.
- The smoke-test runbook permits exactly one retry.

Prompt 3 remains blocked until at least one controlled live LLM smoke test
succeeds with sanitized evidence.
