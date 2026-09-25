#!/usr/bin/env python3
"""Extract the UT of Delhi public authorities from Annexure 1 of the CIC annual reports
(Ministry-wise and Public Authority-wise abstract of online annual returns).
Layout: one column per public authority, one row per item (1..13 plus rejection clauses).
The ministry column carries an integer code (e.g. 59) and its authorities carry 59.1, 59.2, ...
Output: cic_delhi_annex.csv (one row per authority-year) and parse_log.txt."""
import fitz, re, csv, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS_2020 = {1: "opening", 2: "received", 3: "total", 4: "transferred", 5: "fa_received", 6: "fa_disposed",
         7: "rejected", 8: "disciplinary", 9: "fee_rs", 10: "charges_rs", 11: "penalty_rs", 12: "amount_total_rs",
         13: "capios", 14: "cpios", 15: "faas", 16: "officers_total"}
ITEMS = {1: "opening", 2: "received", 3: "total", 4: "transferred", 5: "fa_received", 6: "fa_disposed",
         7: "replied", 8: "rejected", 9: "disciplinary", 10: "fee_rs", 11: "charges_rs", 12: "penalty_rs",
         13: "amount_total_rs", 14: "capios", 15: "cpios", 16: "faas", 17: "officers_total"}


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\n", " ")).strip()


def nums(cell):
    """cells may hold two merged values ('864 601') or '14 (2%)'."""
    cell = re.sub(r"\([^)]*\)", "", clean(cell))
    return [int(x.replace(",", "")) for x in re.findall(r"-?\d[\d,]*", cell)]


def main():
    out = []
    log = open(os.path.join(HERE, "parse_log.txt"), "w")
    for fn in sorted(os.listdir(os.path.join(HERE, "pdf"))):
        year = re.search(r"AR(\d{4}-\d{2})", fn).group(1)
        doc = fitz.open(os.path.join(HERE, "pdf", fn))
        KNOWN = {"2020-21": "61", "2021-22": "59", "2022-23": "59", "2023-24": "59"}
        delhi_code = KNOWN.get(year)
        found = 0
        for pno in range(len(doc)):
            txt = doc[pno].get_text()
            if "Opening Balance" not in txt:
                continue
            try:
                tabs = doc[pno].find_tables()
            except Exception as e:
                log.write(f"{year} p{pno+1}: {e}\n"); continue
            for t in tabs.tables:
                rows = t.extract()
                if len(rows) < 5:
                    continue
                hdr = [clean(c) for c in rows[0]]
                names = [clean(c) for c in rows[1]] if len(rows) > 1 else []
                # discover the Delhi ministry code on this page
                for j, nm in enumerate(names):
                    if re.search(r"^UT of Delhi$|Govt\.? of NCT of Delhi|Union Territory of Delhi", nm) and j < len(hdr):
                        m = re.match(r"^(\d+)$", hdr[j])
                        if m:
                            delhi_code = m.group(1)
                if delhi_code is None:
                    continue
                # columns belonging to Delhi authorities: header codes 'code.k' (a cell may hold two codes)
                cols = []  # (j, sub-index, code, name)
                for j, h in enumerate(hdr):
                    codes = re.findall(rf"\b{delhi_code}\.(\d+)\b", h)
                    if codes:
                        nm_cell = names[j] if j < len(names) else ""
                        # when two codes share a cell, names may also be merged; keep the cell text
                        for si, c in enumerate(codes):
                            cols.append((j, si, f"{delhi_code}.{c}", nm_cell if len(codes) == 1 else f"{nm_cell} [merged {si+1}/{len(codes)}]"))
                if not cols:
                    continue
                recs = {c[2]: {"year": year, "page": pno + 1, "code": c[2], "name": c[3]} for c in cols}
                for r in rows[2:]:
                    cells = [clean(c) for c in r]
                    m = re.match(r"^(\d+)$", cells[0]) if cells else None
                    if not m:
                        continue
                    item = int(m.group(1))
                    IT = ITEMS_2020 if year == "2020-21" else ITEMS
                    if item not in IT:
                        continue
                    for j, si, code, _ in cols:
                        if j < len(cells):
                            vals = nums(cells[j])
                            if len(vals) > si:
                                recs[code][IT[item]] = vals[si]
                out.extend(recs.values()); found += len(recs)
                log.write(f"{year} p{pno+1}: Delhi code {delhi_code}, {len(recs)} authorities\n")
        print(f"{year}: Delhi code {delhi_code}, {found} authority rows")
    fields = ["year", "page", "code", "name"] + list(ITEMS.values())
    with open(os.path.join(HERE, "cic_delhi_annex.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in out:
            w.writerow({k: r.get(k, "") for k in fields})
    ok = sum(1 for r in out if r.get("total") is not None and r.get("received") is not None and r["total"] == (r.get("opening") or 0) + r["received"])
    n = sum(1 for r in out if r.get("total") is not None and r.get("received") is not None)
    print(f"rows={len(out)} total-identity ok {ok}/{n}")


if __name__ == "__main__":
    main()
