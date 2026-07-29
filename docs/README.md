# KSF Stock Market Analysis — Business Analysis Documentation

Based on **BABOK®** (Business Analysis Body of Knowledge) and **PMBOK®** (Project Management Body of Knowledge) frameworks.

## Document Structure

```
docs/
├── requirements/       — Functional and non-functional requirements
├── architecture/       — System architecture and technical design
├── user-stories/       — User stories and use cases
├── methodology/        — BABOK/PMBOK-aligned process docs
└── test-plans/         — Test scenarios and acceptance criteria
```

## Version History

|| Version | Date       | Author      | Changes           |
||---------|------------|-------------|-------------------|
|| 1.0.0   | 2026-05-25 | OWL         | Initial BABOK documentation |
|| 1.1.0   | 2026-06-23 | OWL         | Added screener AJAX endpoint docs; FR-3.6; architecture/uml diagrams |
│ 1.2.0   | 2026-07-24 | OWL         | Advisor hiring/notifications (BR-7, FR-6.x), optional KB risk rules (FR-103), ATR 2.5x methodology, WhatsApp gateway framework, knowledge base pages |
│ 1.3.0   | 2026-07-28 | OWL         | CFI DCF 8-step methodology, CFI M&A 10-step process, CFI LBO/valuation reference, financial modeling dictionary, US-DCF-001 user story |
| | | | |
#### Finance Dictionary Reference

The shared **CFI Finance Dictionary** is defined in [`docs/methodology/cfi-dcf-methodology.md`](./methodology/cfi-dcf-methodology.md) (Financial Dictionary section) and cross-referenced in all valuation-related documentation:

| Reference | Path |
|---|---|
| DCF Terms (CapEx, NWC, WACC, Terminal Value, ...) | `docs/methodology/cfi-dcf-methodology.md` |
| LBO / M&A Terms | `docs/methodology/cfi-ma-process.md` |
| Valuation approach comparison | `ksfii_app/CODE/docs/financial-modeling/cfi-reference.md` |
| CFI source references | `docs/wiki/CFI_References.md` |

> **Note:** All finance modeling terminology in this project maps directly to the CFI
> definitions stated above. When adding new valuation features or user stories, maintain
> consistent definitions with the linked dictionary.
