# Public Repository and Authenticated Generation Architecture

Status: authoritative as of 2026-09-28.

Litinerary's public product surface is the persisted public itinerary repository.
Anonymous users may browse and search only content represented by persisted public
itineraries. Public destination and book discovery is therefore derived from
public itinerary snapshots, not from standalone catalog tables.

Authenticated registered users currently receive generation capabilities. The
backend exposes this through a centralized capability policy with decisions for:

- external discovery;
- itinerary generation;
- itinerary adaptation.

The current policy grants those capabilities to authenticated users. A later paid
entitlement system should change only this policy decision, not the discovery,
generation, or persistence pipeline.

Generation is repository-first. A request first searches for a matching public
itinerary. If one exists, it is reused. If not, an authorized discovery/generation
path may create a validated itinerary. Successful generated or adapted
itineraries are persisted as public repository content.

Externally discovered books are transient discovery and generation inputs. They
are not inserted into the `books` table merely because they were searched,
selected, or used to generate an itinerary. Instead, the persisted itinerary
stores durable book snapshot metadata such as title, author, provider identity,
themes, and provenance. Public book discovery can later find that book through
the itinerary snapshot without invoking an external provider.

Destination discovery follows the same public-repository rule. Standalone
destination rows may remain as reference data, but public discoverability is
determined by public itinerary representation.

Admin ingestion remains an admin endpoint. It is not used as an ordinary-user
discovery or generation API.

## Migration downgrade safety

Migration `20260928_0010` removes the historical requirement that every
itinerary book identifier reference a standalone `books` row. Downgrading to
`20260815_0009` is therefore blocked before schema mutation when any itinerary
uses external-book snapshot metadata without a matching book row. The guard
prevents data loss and avoids fabricating catalog records. An operator must
explicitly reconcile, archive, or remove incompatible itineraries before
retrying the downgrade.

No payment, subscription, checkout, billing, or fake entitlement state is part of
this implementation.
