# Local Offline Deployment Rehearsal Record

## Status

- Result: passed
- Executed at: 2026-06-21T22:12:32+03:00
- Execution context: local Windows PowerShell from repository root
- Rehearsal port: 8765
- Environment posture: offline/mock only

## Preflight Harness

- Harness command: powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\deployment_readiness_check.ps1
- Harness result: passed

## Backend Health

- Health result: passed (/api/health returned ok)

## Readiness Provider Posture

- Status: ready
- External calls allowed: False
- Providers: auth=dev/mock, llm=fake/mock, vector_db=fake/mock, poi_verification=mock/mock, routing=mock/mock, ticketing=mock/mock, affiliate=mock/mock, tts=mock/mock

## Seed Reset And Validation

- Reset result: passed
- Validation result: passed
- Counts: destinations=5, books=10, pois=13, itineraries=2

## Mock Itinerary Generation

- Result: passed
- Title: The Adventures of Sherlock Holmes in London
- LLM provider: mock_ai
- Routing provider: mock_routing
- Baker Street present: yes

## Shutdown

- Backend stopped: yes
- Listener remains on port 8765: no

## Safety Confirmations

- Live LLM request made: no
- /v1/chat/completions called: no
- External providers enabled: no
- Real API key required or read: no
- Secret-like values added to this evidence: no
- Raw provider payload added to this evidence: no

## Limitations

- Local loopback rehearsal only; no cloud infrastructure was exercised.
- Frontend runtime preview is documented separately; the preflight harness validates frontend tests, typecheck, and build.
- Staged internal and public/beta live modes remain no-go.

## Next Recommended Action

Use this record as local offline/mock rehearsal evidence only. Cloud-specific deployment rehearsal, staged log-sink review, production-grade internal access boundary, approved request/spend ceilings, owner approvals, and optional provider-gated tests remain separate blockers.
