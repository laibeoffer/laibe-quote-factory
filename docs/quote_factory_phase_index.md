# Quote Factory Phase Index

## Phase Status

| Phase | Name | Status | Notes |
| --- | --- | --- | --- |
| QF1 | `RawQuoteRow` spec and samples | Completed | Defines raw and normalized quote row shape. |
| QF2 | `RawQuoteRow -> RawCatalogItem` mapping and loader skeleton | Completed | Sample-only conversion to raw catalog payloads. |
| QF2 core specs | Header, alias, unit, split, observation, range specs | Completed | Rules only; no real upload parsing. |
| QF3 | Config parameterization | Completed | Local JSON configs and validators. |
| QF3.1 | Cloud payload validator | Completed | Local sample validation only; no Supabase. |
| QF4 | Generate `PriceObservation` samples | Completed | Candidate observations only. |
| QF4.1 | Alias confidence hardening | Completed | Edge cases and cloud validation. |
| QF4.2 | Negative context regression | Completed | Prevents unsafe alias auto-match. |
| QF5 | Generate `PriceRange` samples | Completed | Statistical candidates only. |
| QF5.1 | PriceRange sanity guard | Completed | Group key, display null, cross-unit checks. |
| QF5.2 | PriceRange review decision contract | Published baseline | Review decisions remain candidate-governance only. |
| QF5.3 | PriceRange review audit / override contract | Completed | Published through PR #2 / main `d075c505d0e950ca288e8d374bdf2efc6b447105`; audit override behavior remains candidate-governance only. |
| QF5.4 | Cloud-ready export package finalization | Completed | Adds sample dry-run export package, export manifest, and package validator for Raw Candidate Warehouse intake. |

## Phase Gate

QF5.4 became active only through the scoped export package finalization task after QF5.3 was visible in `laibeoffer/laibe-quote-factory`.

QF5.4 remains a GitHub-tracked dry-run package for Raw Candidate Warehouse intake. It is not a real cloud upload, Supabase integration, API, migration, renderer path, or formal pricing path.

## Permanent Boundary

Quote Factory never directly outputs:

- formal price
- `PricingRule`
- `MaterialSpec`
- `LaborRule`
- `BudgetEstimateLine`
- renderer / Excel / PDF output
- customer-facing formal quote