#!/usr/bin/env python3
"""Parse the per-public-authority annexure tables in Tamil Nadu State Information Commission
annual reports (2015-2023) into one long CSV.

Three layouts occur:
  W  wide, one row per authority, 21 numbered columns (2015-2018; rotated landscape pages)
  T  the same 21 columns but the table is rotated on a portrait page, so PyMuPDF returns it
     transposed: one row per column label (2019-2022)
  C  one column per authority, one row per item, ~13-25 rows (2023)

Output: tn_sic_annex.csv with canonical fields; parse_log.txt with per-page decisions and
row-level identity checks (total == opening + received; disposal components == total).
"""
import fitz, re, csv, os, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
YEARS = list(range(2015, 2024))

# canonical fields for the 21-column layout, by column number
W_COLS = {2: "pios", 3: "opening", 4: "received", 5: "total", 6: "transferred", 7: "replied",
          8: "rej_s8", 9: "rej_s9", 10: "rej_s11", 11: "rej_s24", 12: "rej_other", 13: "pending",
          14: "charges_rs", 15: "faas", 16: "fa_opening", 17: "fa_received", 18: "fa_total",
          19: "fa_disposed", 20: "fa_rejected", 21: "fa_pending"}

# keyword map for the 2023 item-row layout
C_MAP = [
    (r"opening balance", "opening"), (r"requests received", "received"), (r"total no\.? of requests", "total"),
    (r"transferred", "transferred"), (r"appeals received", "fa_received"), (r"appeals disposed", "fa_disposed"),
    (r"rti replied|requests replied", "replied"), (r"applications? for information rejected|rejected", "rej_total"),
    (r"disciplinary", "disciplinary"), (r"fee \(application\)", "fee_rs"), (r"addl\.? ?charges", "charges_rs"),
    (r"penalty collected", "penalty_rs"), (r"total amount", "amount_total_rs"),
]

num_re = re.compile(r"^-?\d[\d,]*$")


def to_int(s):
    s = (s or "").strip().replace(",", "").replace(" ", "")
    if s in ("", "-", "–", "Nil", "nil", "NIL"):
        return None
    if num_re.match(s):
        return int(s)
    return None


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\n", " ")).strip()


def parse_wide(rows, year, page, log):
    """rows: list of lists; find the (1)..(21) header row, then data rows below."""
    hdr_i = None
    for i, r in enumerate(rows):
        if any(clean(c) == "(1)" for c in r) and any(clean(c) == "(2)" for c in r):
            hdr_i = i
            break
    if hdr_i is None:
        return []
    hdr = [clean(c) for c in rows[hdr_i]]
    colmap = {}
    for j, c in enumerate(hdr):
        m = re.match(r"^\((\d+)\)$", c)
        if m:
            colmap[j] = int(m.group(1))
    out = []
    for r in rows[hdr_i + 1:]:
        cells = [clean(c) for c in r]
        name_j = next((j for j, k in colmap.items() if k == 1), 0)
        name = cells[name_j] if name_j < len(cells) else ""
        vals = {}
        for j, k in colmap.items():
            if k in W_COLS and j < len(cells):
                v = to_int(cells[j])
                if v is not None:
                    vals[W_COLS[k]] = v
        if not vals:
            # continuation of the previous name, or a stray label
            if out and name and not re.search(r"\(\d+\)", name):
                out[-1]["name"] += " " + name
                out[-1]["_cont"] = True
            elif name:
                out.append({"name": name, "_orphan": True})
            continue
        row = {"name": name, **vals}
        # a leading orphan (name only) right before a data row is the wrapped first line of that name
        if out and out[-1].get("_orphan") and not out[-1].get("_merged"):
            row["name"] = (out[-1]["name"] + " " + name).strip()
            out.pop()
        out.append(row)
    return [r for r in out if not r.get("_orphan")]


def parse_transposed(rows, year, page, log):
    """rows have the column label in cell 0 or 1 as '(k)'; values follow across."""
    # find rows carrying '(k)'
    labeled = []
    for r in rows:
        cells = [clean(c) for c in r]
        kk = None
        for j, c in enumerate(cells[:3]):
            m = re.match(r"^\((\d+)\)$", c)
            if m:
                kk = (int(m.group(1)), j)
                break
        if kk:
            labeled.append((kk[0], cells[kk[1] + 1:]))
    if not labeled:
        return []
    # transpose: authorities are positions in the value list
    n = max(len(v) for _, v in labeled)
    by_k = {k: v + [""] * (n - len(v)) for k, v in labeled}
    names = by_k.get(1, [""] * n)
    out = []
    for i in range(n):
        name = clean(names[i]) if i < len(names) else ""
        vals = {}
        for k, f in W_COLS.items():
            if k in by_k:
                v = to_int(by_k[k][i])
                if v is not None:
                    vals[f] = v
        if vals or name:
            out.append({"name": name, **vals})
    return out


def parse_columnar(rows, year, page, log):
    """2023: header rows give S.No 1..N and authority names; item rows 1..13."""
    if not rows or not any("Opening Balance" in clean(c) for r in rows[:4] for c in r):
        return []
    # authority name row: the row after the S.No row where cells are text
    sno_i = next((i for i, r in enumerate(rows) if clean(r[0]).lower().startswith("s.no") or clean(r[0]).lower() == "sl.no"), 0)
    name_row = rows[sno_i + 1]
    # value columns are those where the S.No row has an integer
    sno = [clean(c) for c in rows[sno_i]]
    val_cols = [j for j, c in enumerate(sno) if to_int(c) is not None]
    dept = clean(name_row[1]) if len(name_row) > 1 else ""
    auths = [clean(name_row[j]) if j < len(name_row) else "" for j in val_cols]
    recs = [{"name": a, "dept": dept} for a in auths]
    for r in rows[sno_i + 2:]:
        cells = [clean(c) for c in r]
        label = " ".join(cells[:5]).lower()
        field = next((f for pat, f in C_MAP if re.search(pat, label)), None)
        if not field:
            continue
        for idx, j in enumerate(val_cols):
            if j < len(cells):
                v = to_int(cells[j])
                if v is not None and field not in recs[idx]:
                    recs[idx][field] = v
    return recs


def main():
    out_rows = []
    log = open(os.path.join(HERE, "parse_log.txt"), "w")
    for y in YEARS:
        path = os.path.join(HERE, "pdf", f"ar_{y}.pdf")
        doc = fitz.open(path)
        n_rows_year = 0
        current_dept = ""
        for pno in range(len(doc)):
            pg = doc[pno]
            try:
                tabs = pg.find_tables()
            except Exception as e:
                log.write(f"{y} p{pno+1}: find_tables error {e}\n")
                continue
            for t in tabs.tables:
                rows = t.extract()
                if not rows:
                    continue
                flat = " ".join(clean(c) for r in rows for c in r)
                if "(1)" in flat and "(2)" in flat and re.search(r"PIOs|petitions|Petitions|Requests|\(21\)", flat):
                    # wide or transposed?
                    first_cells = [clean(r[0]) for r in rows] + [clean(r[1]) for r in rows if len(r) > 1]
                    transposed = sum(1 for c in first_cells if re.match(r"^\(\d+\)$", c)) >= 5
                    recs = parse_transposed(rows, y, pno + 1, log) if transposed else parse_wide(rows, y, pno + 1, log)
                    layout = "T" if transposed else "W"
                elif "Opening Balance" in flat:
                    recs = parse_columnar(rows, y, pno + 1, log)
                    layout = "C"
                else:
                    continue
                for r in recs:
                    name = r.get("name", "")
                    if not name or re.match(r"^[\d\s.,()-]*$", name):
                        continue
                    is_total = bool(re.search(r"\btotal\b", name, re.I))
                    if is_total:
                        current_dept = re.sub(r"\s*total\s*$", "", name, flags=re.I).strip()
                    dept = r.get("dept") or (current_dept if is_total else "")
                    rec = {"year": y, "page": pno + 1, "layout": layout, "dept_hint": dept,
                           "name": name, "is_total": int(is_total)}
                    for f in ["pios", "opening", "received", "total", "transferred", "replied", "rej_s8", "rej_s9",
                              "rej_s11", "rej_s24", "rej_other", "rej_total", "pending", "charges_rs", "fee_rs",
                              "penalty_rs", "amount_total_rs", "faas", "fa_opening", "fa_received", "fa_total",
                              "fa_disposed", "fa_rejected", "fa_pending", "disciplinary"]:
                        rec[f] = r.get(f, "")
                    # identity checks
                    chk1 = chk2 = ""
                    if rec["total"] != "" and rec["received"] != "":
                        chk1 = int(rec["total"] == (rec["opening"] or 0) + rec["received"])
                    if rec["total"] != "" and rec["replied"] != "":
                        rej = sum(v for k, v in rec.items() if k.startswith("rej_") and v != "" and k != "rej_total")
                        if rec["rej_total"] != "":
                            rej = rec["rej_total"]
                        comp = (rec["replied"] or 0) + (rec["transferred"] or 0) + rej + (rec["pending"] or 0)
                        chk2 = int(comp == rec["total"])
                    rec["chk_total"] = chk1
                    rec["chk_disposal"] = chk2
                    out_rows.append(rec)
                    n_rows_year += 1
                log.write(f"{y} p{pno+1}: layout {layout}, {len(recs)} rows\n")
        # back-fill dept for W/T rows: rows before a 'Department Total' belong to it
        yr = [r for r in out_rows if r["year"] == y]
        pending = []
        for r in yr:
            if r["layout"] in ("W", "T"):
                if r["is_total"]:
                    for p in pending:
                        p["dept_hint"] = p["dept_hint"] or r["dept_hint"]
                    pending = []
                else:
                    pending.append(r)
        print(f"{y}: {n_rows_year} rows")
    fields = list(out_rows[0].keys())
    with open(os.path.join(HERE, "tn_sic_annex.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)
    log.close()
    tot = len(out_rows)
    ok1 = sum(1 for r in out_rows if r["chk_total"] == 1); n1 = sum(1 for r in out_rows if r["chk_total"] != "")
    ok2 = sum(1 for r in out_rows if r["chk_disposal"] == 1); n2 = sum(1 for r in out_rows if r["chk_disposal"] != "")
    print(f"rows={tot}  total-identity ok {ok1}/{n1}  disposal-identity ok {ok2}/{n2}")


if __name__ == "__main__":
    main()
