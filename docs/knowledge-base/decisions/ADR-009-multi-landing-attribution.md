# ADR-009: Shared solution-landing attribution

Date: 2026-11-08. Status: published to production by explicit owner instruction.

## Context
Multiple solution landings need one administrator page, individual saved UTM
links and account attribution. The main public swipies.app landing must remain intact.

## Decision
Add an authenticated Flask extension and isolated private SQLite store. Campaign
URLs lead to registered solution subdomains. Opt-in marked CTA buttons route
through one fixed-origin server redirect carrying a random visitor ID and UTM
into the existing registration mechanism. No browser-declared success events
are trusted. Read actual platform users through the existing read-only adapter.

## Consequences
No platform schema change or main public HTML edit. A copied campaign link can
generate a transition, so reports are labeled as link attribution, not verified
landing views or unique people. Existing logged-in users may remain unmatched.
New landing DNS, CTA integration, private-state backup and deployment are separate.
See [implementation and release notes](../landing-acquisition.md).
