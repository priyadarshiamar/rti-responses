# Plan: Report 2, "What the state told us about itself"
## Analysis of the data received, by provenance

**Status:** DRAFT for verification by Amar before any tables are produced
**Date:** 2026-09-24
**Companion:** Report 1 (filings and responses, PAP-consistent) is separate and not covered here.
**Audience:** Gaurav. Tables and figures with notes; specifications stated where estimated.

---

## 0. Why a separate report

The pre-analysis plan (main.tex) specifies how to analyse the audit's *outcomes*: incidence, speed, disposition, fees, appeals, and the salience contrast. It says what to do with register data in one paragraph (five analyses) and nothing about the documents that arrive as attachments, or about the public statistics the replies pointed us to. This report covers that material. Nothing in it touches treatment arms, so it can be written now without contaminating the experiment.

## 1. Three kinds of data, by how we got them

The distinction is the organising principle of the report. Every table carries a provenance tag.

| Tag | Source | What we hold today | Coverage |
|---|---|---|---|
| **A. In the reply** | Documents PIOs enclosed with their RTI response | KA-057: handwritten Kannada register, 6 pp (Format A). TN-057: one register row plus month table (Formats A and B). TN-052: period totals (Format C; photo, numbers partly illegible). TN-173: half-year totals (Format C) **plus the department's Section 25(2) Format I return for 2025 covering 7 authorities**. TN-283: 69 pp register and 3 pp annual return, offered on payment. | 5 offices, 1 department return |
| **B. From a website named in a reply** | Public documents at URLs the PIO cited instead of supplying | **Tamil Nadu State Information Commission** annual reports 2015 to 2023 (cited by TN-052): per-authority annexure, 21 fields, about 300 authorities a year, 2,940 rows parsed. **Central Information Commission** annual reports 2020-21 to 2024-25 (cited by TN-308): Annexure 1, ministry-wise and public-authority-wise abstract of online annual returns, including the Union Territory of Delhi. | TN: 9 years, all state authorities. CIC: 5 years, central ministries and Delhi |
| **C. Sought by us for states without replies** | Same kind of commission publication, found by us | **Maharashtra SIC** annual reports 2006 to 2024, Marathi (2012 also English); downloaded, not yet parsed. **Karnataka** and **Telangana** commission sites are unreachable from outside India; need an RA or VPN to check. | MH: downloaded. KA, TG: not yet |

Type B is analytically the strongest: it is official, it covers every authority whether or not it answered us, and it predates our filings. Type A is the richest per document but selected on response. Type C is a benchmark and, for Maharashtra, a language-cost decision.

## 2. What is in the Tamil Nadu commission annexes (Type B)

Per authority per year: number of PIOs; opening pendency; requests received; total; transferred under s.6(3); replied with information; rejected under s.8, s.9, s.11, s.24, other; pending at year end; charges collected (Rs); number of first appellate authorities; first appeals opening, received, total, disposed with information, rejected, pending. The 2023 layout adds application fees, penalties, and disciplinary cases, and drops the clause split of rejections.

Parser quality (to be reported as a data-quality table): 2,940 authority-year rows; 99.6 percent satisfy total = opening + received; 93 percent satisfy total = replied + transferred + rejected + pending (failures are mostly blank pending cells and a handful of wrapped-row misalignments in 2018). Authority names in 2019 to 2022 are occasionally truncated by the PDF's rotated text and need harmonisation across years.

## 3. Proposed analyses

### B. Commission data (Tamil Nadu 2015 to 2023; Delhi and Centre 2020-21 to 2024-25)

| # | Analysis | Output | Specification |
|---|---|---|---|
| B1 | **State-level RTI activity, 2015 to 2023.** Requests, reply share, transfer share, rejection share by clause, first-appeal rate, charges per request. | One figure (small multiples), one table | Sums over authorities; shares as ratios of sums. Vertical markers at the 2019 amendment, COVID (2020), DPDP (Aug 2023). Descriptive only. |
| B2 | **Department heterogeneity.** 40 departments × 9 years: volume concentration (Home and Revenue dominate), rejection rates, s.24 blanket exemptions, appeal rates. | Lorenz-style concentration figure; table of departments ranked by volume with rates | Department totals from the annex. Empirical-Bayes shrinkage on rates for small departments, as the PAP prescribes for league tables. |
| B3 | **Authority-level panel and persistence.** Harmonise names across years; within-authority correlation of reply share and appeal rate year to year; relation between volume and rejection or appeal rate. | Scatter with binned means; persistence table | Two-way fixed effects: y_it = a_i + g_t + e_it, reporting the share of variance that is between-authority. Year effects around 2019 as an event-study with the caveat that COVID coincides. |
| B4 | **Tier as a routing layer.** Secretariat departments versus heads of department versus corporations: transfer share, reply share, requests per PIO. | One table, one figure | Tier from name pattern ("Department, Secretariat" = Secretariat; else HOD/corporation). Feeds the PAP amendment that a s.6(3) transfer at the secretariat tier is the modal compliant response. |
| B5 | **Appeals funnel and commission throughput.** First appeals per 100 requests by department; second appeals received versus disposed at the commission (from the report body: 21,476 received, 8,369 disposed in 2023) and the pendency series. | Funnel figure; table | Ratios; commission pendency as "silent commission" measure for the appeals estimand. |
| B6 | **Fees.** Charges collected per request by department; implied pages at Rs 2 per page; comparison with the two fee demands we received (Rs 832 and Rs 138). | Table | Ratios. |
| B7 | **Link to the audit sample.** Match the 176 Tamil Nadu department-HQ and HOD offices in the sampled batch to annex rows; report match rate; compare sampled versus unsampled authorities on volume and reply share; produce the pre-treatment covariate file for the PAP. | Match table; balance-style comparison | Exact and fuzzy name matching with manual review of unmatched. No outcome data used. |
| B8 | **Delhi and Centre benchmark.** From CIC Annexure 1: same metrics for UT of Delhi authorities and central ministries, 2020-21 to 2024-25. | One table | Sums and shares; presented as a benchmark for the Delhi filings and for cross-jurisdiction comparison. |

### A. Documents in the replies

| # | Analysis | Output | Notes |
|---|---|---|---|
| A1 | **Triangulation for one office.** Co-operation Secretariat: register letter (712, Aug 2025 to Jul 2026), own Section 25 return (502, calendar 2025), commission publication (554 in 2023; series back to 2015). | One figure, one table | The first measurement-consistency case; states what a discrepancy means before we see more. |
| A2 | **Format I return, 7 authorities, 2025.** Routing share, rejection clauses, appeal rate, penalty incidence, fees, as already transcribed. | One table | Compare each authority's 2025 self-return with its 2023 commission row (B7 matching). |
| A3 | **Register extracts.** TN-057 (one application) and KA-057 (handwritten, needs Kannada transcription): demand composition fields where present; days to disposal; fees recorded at intake. | Table | Enter into `register_rows.csv` per the plan; KA-057 transcription is an RA task, not Claude's. |
| A4 | **Format C totals.** TN-052 and TN-173 period totals; fee-pending registers (TN-173, TN-283) listed as pending entries. | Table | TN-052 numbers need a manual read from the photo. |

### C. Other states

| # | Analysis | Output | Notes |
|---|---|---|---|
| C1 | **Maharashtra.** Parse state and department totals from the SIC reports if tables are machine-readable; Marathi digits and labels need a mapping. | Table of state totals by year if feasible | Decision needed: worth the parsing cost now, or defer to when Maharashtra filings scale beyond 33. |
| C2 | **Karnataka and Telangana.** Ask an RA to check the commission sites from India; record availability and years. | One paragraph | Availability itself is a finding about the state's transparency infrastructure. |

## 4. Report structure

1. Provenance and coverage (the table in Section 1, with counts).
2. Data quality (parser checks, name harmonisation, what is missing).
3. Tamil Nadu 2015 to 2023: B1 to B6.
4. The audit sample in the official record: B7.
5. What the replies enclosed: A1 to A4.
6. Benchmarks: B8, C1, C2.
7. What this changes in the pre-analysis plan (three amendments: tier as routing, pre-treatment covariates, office-paired misreporting estimator).

Every table and figure gets a two-line note: what it shows, and provenance tag. Specifications appear as displayed equations only where something is estimated (B3).

## 5. Decisions I need from you before producing the report

1. **Maharashtra parsing now or later** (C1)? My recommendation: later, unless Gaurav wants a Maharashtra benchmark for the 33 filings.
2. **Name harmonisation depth** for B3 and B7: automatic fuzzy matching with a manual review of the top 40 departments' offices (about two hours), or full manual review of all 300 (an RA day)?
3. **CIC scope** (B8): Delhi authorities only, or Delhi plus central ministries as a national benchmark?
4. **KA-057 transcription**: assign to a Kannada-reading RA now, or leave A3 as a placeholder in the first version?
5. **Anything to exclude** because it would pre-empt a treatment analysis? I see nothing here that conditions on arm, but you should confirm.

## 6. Files

- `commission_reports/tn/parse_tn.py`, `tn_sic_annex.csv`, `parse_log.txt` (Type B, done)
- `commission_reports/cic/pdf/` (Type B, downloaded; parser to write)
- `commission_reports/mh/pdf/` (Type C, downloaded; decision pending)
- `reports/report2_received_data/` will hold `analysis.py`, `report.tex`, figures, and the PDF.
