# Generated Itinerary Quality Review Template

Use this template after controlled live LLM smoke tests. Do not include secrets, raw provider payloads, private user data, or unredacted logs.

Live POI, routing, ticketing, affiliate, TTS, and managed-auth validation are out of scope unless those providers are separately staged and approved.

## Review Metadata

- Review ID:
- Smoke test number:
- Date/time:
- Reviewer:
- Environment:
- Destination:
- Book:
- Duration days:
- Transportation mode:
- Provider shown in sanitized result:

## Destination Fit

- Itinerary stays within the requested destination:
- Stops match the destination context:
- No unsupported city/region appears:
- Notes:

## Seed-Data Alignment

- Stops align with current MVP seed data:
- Book/destination relationship is valid:
- Literary relevance uses seeded or grounded context:
- No unsupported POI IDs or invented required fields:
- Notes:

## POI Plausibility

- POIs are recognizable or seed-backed:
- Coordinates/provenance are present where expected:
- Verification status is acceptable for smoke testing:
- Low-confidence or review-needed POIs are identified:
- Notes:

## Routing Limitations

- Mock routing limitations are understood:
- Walking distance appears plausible for review-only use:
- Public transport or car/taxi assumptions are clearly provisional:
- No turn-by-turn or real transit claim is made:
- Notes:

## Hallucination Checks

- No unsupported claims about tickets, opening hours, prices, or access:
- No invented real-time availability:
- No copyrighted full-text-derived details:
- No unsupported safety or legal advice:
- Notes:

## Safety And Disclaimer Text

- User-facing copy avoids overclaiming verification:
- Logistics notes make mock/live provider limitations clear:
- No sensitive personal data appears:
- Notes:

## Accessibility And Structure

- Itinerary has clear title, summary, days, and ordered stops:
- Day count matches request:
- Stop descriptions are readable and concise:
- Important warnings are visible:
- Notes:

## Budget And Time Feasibility

- Duration appears feasible for the requested day count:
- Stop count is reasonable:
- Estimated time/distance is plausible or clearly mock:
- Budget/ticketing claims are absent or marked provisional:
- Notes:

## User-Facing Clarity

- The itinerary is understandable without internal context:
- The literary theme is clear:
- Logistics notes are actionable without pretending live validation:
- Notes:

## Reviewer Verdict

- Verdict: pass/fail/needs revision
- Required fixes:
- Follow-up owner placeholder:
- Approved for another controlled smoke test: yes/no
- Approved for staged internal testing: no, unless all staged-readiness blockers are satisfied separately
