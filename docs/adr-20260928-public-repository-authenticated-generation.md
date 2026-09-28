# ADR 2026-09-28: Public Repository and Authenticated Generation

## Status

Accepted.

## Context

Earlier Litinerary implementations mixed public catalog discovery with itinerary
generation. That allowed standalone books or destinations to appear publicly even
when no public itinerary represented them, and generation assumed books were
persisted catalog records.

## Decision

The persisted public itinerary is the canonical public artifact.

Anonymous users can only consume repository content derived from public
itineraries. Authenticated registered users can currently use external discovery,
generation, and adaptation through a centralized capability policy. Future paid
entitlement enforcement will replace the policy grant condition without changing
the route or persistence architecture.

Generated itineraries are public after successful validation and persistence.
External book metadata is stored on the itinerary snapshot and does not require a
standalone `BookModel` row.

## Consequences

Public `/api/books` and `/api/destinations` are repository-only. Authenticated
`/api/discovery/*` endpoints may return transient external results.

`itineraries.book_id` is a durable identifier but no longer requires a `books`
row for externally discovered books. Itinerary snapshot columns preserve display,
search, reuse, and provenance metadata.

Provider or validation failures must not persist incomplete public itineraries.
Admin ingestion stays admin-only.
