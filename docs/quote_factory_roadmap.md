# Quote Factory Roadmap

## Purpose

Quote Factory is the external workspace for turning historical quote data into traceable candidate evidence.

It produces candidate data only:

- `RawQuoteRow`
- `RawCatalogSource`
- `RawCatalogItem`
- `PriceObservation`
- `PriceRange`
- `PriceRange Review Decision`
- audit and review queue payloads

It does not produce formal prices, `PricingRule`, `MaterialSpec`, `LaborRule`, `BudgetEstimateLine`, renderer output, Excel/PDF, Supabase migrations, APIs, payment, escrow, or listing-fee behavior.

## Current Published Baseline

### QF5.2 PriceRange Review Decision Contract

Status: published baseline.

QF5.2 defines review decisions for candidate statistical `PriceRange` payloads. `approved_for_cloud` means candidate statistical readiness only, not formal price approval.

### QF5.3 PriceRange Review Decision Audit & Override Contract

Status: publish candidate for Issue #1.

QF5.3 adds:

- override request payloads
- allowed and conditional override transitions
- illegal override rejection
- reviewed output with audit metadata
- audit log payloads
- stricter forbidden formal pricing / formal spec field checks

## Next Planned Phase

### QF5.4 PriceRange Review Audit QA / Cloud Staging Dry-run Contract

Status: planned only. Not active until QF5.3 is merged and visible in `laibeoffer/laibe-quote-factory`.

QF5.4 may define a dry-run QA packet for cloud staging readiness. It must remain local/sample-only until explicitly authorized.

Allowed QF5.4 direction:

- QA checklist for QF5.3 audit payloads
- dry-run staging manifest
- candidate upload readiness rules
- enum / schema consistency checks
- no real Supabase connection
- no migration
- no API

Forbidden QF5.4 direction:

- real cloud upload
- formal pricing approval
- `PricingRule`
- `MaterialSpec`
- `LaborRule`
- `BudgetEstimateLine.unit_price`
- renderer / Excel / PDF
- production customer quote output
