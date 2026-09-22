# rti-responses

Response tracking for the RTI audit ([design document](https://github.com/priyadarshiamar/rti-telangana)): first-pass coding of every reply received from a public information officer, and a dashboard built from it.

**Dashboard:** https://priyadarshiamar.github.io/rti-responses/

## What is here

| Path | What |
|---|---|
| `responses_coded.csv` | One row per application that has received a response. The source of truth; editable by hand. |
| `build.py` | Scans the shared Drive folder of response PDFs, extracts text (pdftotext, tesseract fallback), joins with the assignment sheets, writes `docs/`. |
| `template.html` | Page template. `build.py` embeds `data.json` into it. |
| `docs/index.html`, `docs/data.json` | Generated. Served by GitHub Pages. |
| `data/files_index.csv` | Generated inventory of files in the Drive folder. |

The OCR text layer (`text/`) is gitignored because the documents carry applicant addresses. The Drive folder itself is not in this repo.

## Codebook (columns of `responses_coded.csv`)

- `disposition` (what happened): `full` information supplied · `partial` some supplied · `denied` refused or deflected · `fee_pending` offered on payment · `returned` bounced with nothing · `transferred` handed to another office · `silent`
- `granularity` (how detailed): `format_a` one row per RTI application in the office's register · `format_b` monthly or category counts · `format_c` period totals · `narrative_only` prose without numbers · `none`
- `q3_sec25` (the Section 25 annual return requested): `supplied` · `not_held` · `refused_separate_application` · `referred_to_website` · `offered_on_payment` · `not_addressed`
- `medium`: `portal` · `email` · `post` · `phone`
- `fee_inr`, `fee_pages`, `fee_channel` (`portal`, `treasury_head_of_account`, `post_or_counter`, `DD`, `IPO`)
- `supplied_by_email` 1/0 · `clause_cited` (e.g. `8(1)(j)`, `7(9)`, `none`) · `appeal_candidate` 1/0
- `coder`, `coded_on`, `confidence` (`high`/`medium`/`low`). Rows coded by `claude` are a first pass pending double coding.

Filing date is the portal's date of filing; `response_date` is the date on the PIO's document (for postal replies this precedes receipt).

## Refresh

```bash
python3 build.py          # full run, OCRs new scans
python3 build.py --no-ocr # skip OCR
```

A scheduled Claude task runs the build every two days, codes new responses, commits, and pushes.
