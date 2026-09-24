#!/usr/bin/env python3
"""Report 1: filings and responses, consistent with the pre-analysis plan.
Produces LaTeX table fragments and PDF figures in this directory.
Withholds every tabulation of outcomes by treatment arm (PAP discipline): arms appear only in
design/balance tables and in the filing-attrition test, which is pre-treatment.
"""
import os, re, csv, glob, datetime, collections
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.api as sm

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.join(ROOT, "analysis", "_cache")
HOME = os.path.expanduser("~")
DRIVE = os.path.join(HOME, "Library/CloudStorage/GoogleDrive-pamar@clio.uc3m.es/.shortcut-targets-by-id/1nlnBaoUheM3B-oo-qPBwQmsIciHUBmRz/rti")
ASOF = datetime.date(2026, 9, 24)
STATE = {"TN": "Tamil Nadu", "TG": "Telangana", "KA": "Karnataka", "DL": "Delhi", "MH": "Maharashtra"}
ORDER = ["TN", "TG", "KA", "DL", "MH"]
LOOSE = re.compile(r"\b(TN|KA|TG|DL|MH)\b[^0-9]{0,24}?(\d{3})\b")

plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def tex_escape(s):
    return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")


def write(name, text):
    with open(os.path.join(HERE, name), "w") as f:
        f.write(text)


# ---------------------------------------------------------------- drawn samples
def load_drawn():
    frames = []
    tn = pd.read_csv(os.path.join(CACHE, "assignments_TN.csv"), dtype=str)
    tn["state"] = "TN"
    tn["stratum"] = tn["randomization_stratum"]
    frames.append(tn[["application_id", "state", "treatment", "assigned_ra", "tier", "stratum", "tree_department"]].rename(columns={"tree_department": "department"}))
    for st, path in [("TG", "rti-telangana/out/tg2026q3_02/assignments.csv"), ("KA", "rti-karnataka/out/ka2026q3_01/assignments.csv"),
                     ("DM", "rti-delhi-maharashtra/out/dm2026q3_01/assignments.csv")]:
        d = pd.read_csv(os.path.join(HOME, path), dtype=str)
        d["state"] = d["application_id"].str[:2]
        d["tier"] = ""
        d["stratum"] = d["dept_group"]
        d["department"] = d["dept_group"]
        frames.append(d[["application_id", "state", "treatment", "assigned_ra", "tier", "stratum", "department"]])
    drawn = pd.concat(frames, ignore_index=True)
    drawn["legal"] = (drawn["treatment"] == "legal_salience").astype(int)
    return drawn


# ---------------------------------------------------------------- filed
def load_filed():
    files = collections.defaultdict(list)
    for root, _, fs in os.walk(os.path.join(DRIVE, "Filed_RTI")):
        for fn in fs:
            m = LOOSE.search(fn.upper().replace("_", "-"))
            if m:
                files[f"{m.group(1)}-{m.group(2)}"].append(os.path.relpath(os.path.join(root, fn), DRIVE))
    sheets = pd.read_csv(os.path.join(CACHE, "filed_sheets.csv"), dtype=str).fillna("")
    rec_path = os.path.join(CACHE, "receipts.csv")
    receipts = pd.read_csv(rec_path, dtype=str).fillna("") if os.path.exists(rec_path) else pd.DataFrame(columns=["app_id", "filing_date", "reg_no"])
    rows = []
    ids = set(files) | set(sheets.loc[(sheets["registration_number"] != "") | (sheets["filing_date"] != ""), "app_id"])
    sh = sheets.set_index("app_id")
    rc = receipts[receipts["filing_date"] != ""].drop_duplicates("app_id").set_index("app_id")
    for a in sorted(ids):
        fd = ""
        src = ""
        if a in sh.index and sh.loc[a, "filing_date"]:
            fd, src = sh.loc[a, "filing_date"], "sheet"
        elif a in rc.index:
            fd, src = rc.loc[a, "filing_date"], "receipt_ocr"
        logged = int(a in sh.index and bool(sh.loc[a, "registration_number"] or sh.loc[a, "filing_date"]))
        rows.append({"application_id": a, "state": a[:2], "has_receipt": int(a in files), "n_files": len(files.get(a, [])),
                     "filing_date": fd, "date_source": src, "in_sheet": int(a in sh.index), "logged": logged,
                     "filed": int(a in files or logged)})
    filed = pd.DataFrame(rows)
    filed["filing_date"] = pd.to_datetime(filed["filing_date"], errors="coerce")
    filed["days_exposed"] = (pd.Timestamp(ASOF) - filed["filing_date"]).dt.days
    return filed


# ---------------------------------------------------------------- responses
def load_responses():
    r = pd.read_csv(os.path.join(ROOT, "responses_coded.csv"), dtype=str).fillna("")
    r["filing_date"] = pd.to_datetime(r["filing_date"])
    r["response_date"] = pd.to_datetime(r["response_date"])
    r["days"] = (r["response_date"] - r["filing_date"]).dt.days
    r["state"] = r["app_id"].str[:2]
    return r


# ---------------------------------------------------------------- tables
def table_design(drawn):
    out = []
    for st in ORDER:
        d = drawn[drawn.state == st]
        if d.empty:
            continue
        tiers = d["tier"].replace("", np.nan).value_counts()
        tier_s = "; ".join(f"{k} {v}" for k, v in tiers.items()) if len(tiers) else "single tier (portal roster)"
        ras = d["assigned_ra"].value_counts().sort_index()
        out.append(f"{STATE[st]} & {len(d)} & {int((d.legal == 0).sum())} / {int(d.legal.sum())} & {tex_escape(tier_s)} & {'/'.join(str(v) for v in ras)} & {d['stratum'].nunique()} \\\\")
    tot = len(drawn)
    out.append(r"\midrule " + f"All & {tot} & {int((drawn.legal == 0).sum())} / {int(drawn.legal.sum())} & & & \\\\")
    write("tab_design.tex", "\n".join(out))


def table_filing(drawn, filed):
    m = drawn.merge(filed[["application_id", "filed", "has_receipt", "filing_date", "days_exposed"]], on="application_id", how="left")
    m["filed"] = m["filed"].fillna(0).astype(int)
    out = []
    for st in ORDER:
        d = m[m.state == st]
        if d.empty:
            continue
        p = d[d.legal == 0]; l = d[d.legal == 1]
        out.append(f"{STATE[st]} & {len(d)} & {int(d.filed.sum())} & {100*d.filed.mean():.0f} & {100*p.filed.mean():.0f} & {100*l.filed.mean():.0f} & {100*(l.filed.mean()-p.filed.mean()):+.1f} \\\\")
    d = m
    out.append(r"\midrule " + f"All & {len(d)} & {int(d.filed.sum())} & {100*d.filed.mean():.0f} & {100*d[d.legal==0].filed.mean():.0f} & {100*d[d.legal==1].filed.mean():.0f} & {100*(d[d.legal==1].filed.mean()-d[d.legal==0].filed.mean()):+.1f} \\\\")
    write("tab_filing.tex", "\n".join(out))
    # attrition test: LPM filed ~ legal with stratum FE, HC1; and randomisation inference within strata (TN only, the fully stratified batch)
    tn = m[m.state == "TN"].copy()
    X = pd.get_dummies(tn["stratum"], drop_first=True, dtype=float)
    X.insert(0, "legal", tn["legal"].astype(float))
    X = sm.add_constant(X)
    fit = sm.OLS(tn["filed"].astype(float), X).fit(cov_type="HC1")
    b, se, pval = fit.params["legal"], fit.bse["legal"], fit.pvalues["legal"]
    rng = np.random.default_rng(20260817)
    obs = tn.groupby("legal").filed.mean().diff().iloc[-1]
    perms = []
    groups = [g.index.values for _, g in tn.groupby("stratum")]
    legal = tn["legal"].values.copy(); filed_v = tn["filed"].values
    idx = {i: k for k, i in enumerate(tn.index)}
    for _ in range(2000):
        lp = legal.copy()
        for g in groups:
            pos = [idx[i] for i in g]
            lp[pos] = rng.permutation(lp[pos])
        perms.append(filed_v[lp == 1].mean() - filed_v[lp == 0].mean())
    ri_p = float(np.mean(np.abs(perms) >= abs(obs)))
    write("attrition_stats.tex",
          f"\\newcommand{{\\attrN}}{{{len(tn)}}}\\newcommand{{\\attrB}}{{{100*b:.1f}}}\\newcommand{{\\attrSE}}{{{100*se:.1f}}}\\newcommand{{\\attrP}}{{{pval:.2f}}}\\newcommand{{\\attrRI}}{{{ri_p:.2f}}}\\newcommand{{\\attrStrata}}{{{tn['stratum'].nunique()}}}\n")
    return m


def table_balance(m):
    tn = m[(m.state == "TN") & (m.filed == 1)]
    out = []
    for name, col in [("Tier", "tier"), ("Research assistant", "assigned_ra")]:
        out.append(r"\multicolumn{5}{l}{\itshape " + name + r"} \\")
        for k, g in tn.groupby(col):
            out.append(f"\\quad {tex_escape(k)} & {len(g)} & {int((g.legal==0).sum())} & {int(g.legal.sum())} & {100*g.legal.mean():.0f} \\\\")
    ct = pd.crosstab(tn["tier"], tn["legal"]); from scipy.stats import chi2_contingency
    p_tier = chi2_contingency(ct)[1] if ct.shape[0] > 1 else float("nan")
    ct2 = pd.crosstab(tn["assigned_ra"], tn["legal"]); p_ra = chi2_contingency(ct2)[1] if ct2.shape[0] > 1 else float("nan")
    out.append(r"\midrule All filed, Tamil Nadu & " + f"{len(tn)} & {int((tn.legal==0).sum())} & {int(tn.legal.sum())} & {100*tn.legal.mean():.0f} \\\\")
    write("tab_balance.tex", "\n".join(out))
    write("balance_stats.tex", f"\\newcommand{{\\balPtier}}{{{p_tier:.2f}}}\\newcommand{{\\balPra}}{{{p_ra:.2f}}}\n")


def table_exposure(filed):
    out = []
    for st in ORDER:
        d = filed[(filed.state == st) & (filed.filed == 1)]
        if d.empty:
            continue
        dd = d.dropna(subset=["days_exposed"])
        out.append(f"{STATE[st]} & {len(d)} & {int(d.has_receipt.sum())} & {len(dd)} & {dd.filing_date.min():%d %b} -- {dd.filing_date.max():%d %b} & {dd.days_exposed.median():.0f} & {dd.days_exposed.max():.0f} & {int((dd.days_exposed >= 30).sum())} \\\\")
    d = filed[filed.filed == 1]; dd = d.dropna(subset=["days_exposed"])
    out.append(r"\midrule All & " + f"{len(d)} & {int(d.has_receipt.sum())} & {len(dd)} & & {dd.days_exposed.median():.0f} & {dd.days_exposed.max():.0f} & {int((dd.days_exposed >= 30).sum())} \\\\")
    write("tab_exposure.tex", "\n".join(out))


def table_responses(resp):
    DISP = {"full": "Full", "partial": "Partial", "denied": "Denied (deflection)", "fee_pending": "Fee pending", "returned": "Returned", "transferred": "Transferred"}
    GRAN = {"format_a": "A: register rows", "format_b": "B: counts", "format_c": "C: totals", "narrative_only": "Prose only", "none": "None"}
    out = []
    for _, r in resp.sort_values(["state", "app_id"]).iterrows():
        gran = GRAN.get(r.granularity, r.granularity)
        if r.granularity == "format_a" and r.app_id == "TN-057":
            gran = "A + B"
        fee = f"Rs {int(float(r.fee_inr)):,}" if r.fee_inr else "--"
        out.append(f"{r.app_id} & {tex_escape(r.authority)} & {r.filing_date:%d %b} & {r.response_date:%d %b} & {r.days} & {r.medium} & {DISP.get(r.disposition, r.disposition)} & {gran} & {fee} \\\\")
    write("tab_responses.tex", "\n".join(out))


def table_access():
    rows = [
        ("Tamil Nadu", "Portal, own software", "17,417 offices, 40 depts", "Yes", "No", "1", "Rs 10 online", "3,000 chars", "None"),
        ("Telangana", "Portal, own software", "3,401 offices", "Yes", "SMS", "2", "Rs 10 online", "3,000 chars", "None"),
        ("Karnataka", "Portal, NIC RTI Online", "1,800 nodal officers", "Yes", "Email + SMS", "3", "Rs 10 via treasury gateway (UPI)", "3,000 chars", "None"),
        ("Delhi", "Portal, NIC RTI Online", "223 authorities", "No", "Email", "1--2", "Rs 10 online", "3,000 chars", "None"),
        ("Maharashtra", "Portal, NIC RTI Online", "328 authorities", "No", "Email", "1--2", "Rs 10 online", "150 words", "None"),
        ("Rajasthan", "Portal, own software", "not enumerated", "No", "Optional", "1", "Rs 10 online", "--", "ID number and scan; state address"),
    ]
    out = [" & ".join(tex_escape(c) for c in r) + r" \\" for r in rows]
    write("tab_access.tex", "\n".join(out))


# ---------------------------------------------------------------- figures
def fig_timeline(filed):
    d = filed[(filed.filed == 1)].dropna(subset=["filing_date"])
    fig, ax = plt.subplots(figsize=(5.2, 2.6))
    for st in ORDER:
        s = d[d.state == st].sort_values("filing_date")
        if s.empty:
            continue
        cum = s.groupby("filing_date").size().cumsum()
        ax.step(cum.index, cum.values, where="post", label=f"{STATE[st]} ({len(s)})")
    ax.axvline(pd.Timestamp(ASOF), color="gray", lw=0.8, ls=":")
    ax.set_ylabel("Cumulative applications filed"); ax.legend(frameon=False, fontsize=7)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d %b"))
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig_timeline.pdf")); plt.close(fig)


def km(times, events, grid):
    """Kaplan-Meier survival on a grid; returns 1-S (cumulative incidence of response)."""
    times = np.asarray(times, float); events = np.asarray(events, int)
    S = 1.0; out = []; ts = np.unique(times[events == 1])
    j = 0; cur = []
    for g in grid:
        while j < len(ts) and ts[j] <= g:
            t = ts[j]; n = ((times >= t)).sum(); dth = ((times == t) & (events == 1)).sum()
            S *= (1 - dth / n) if n > 0 else 1; j += 1
        out.append(1 - S)
    return np.array(out)


def fig_km(filed, resp):
    d = filed[(filed.filed == 1)].copy()
    rf = resp.set_index("app_id")["filing_date"]
    fill = d.filing_date.isna() & d.application_id.isin(rf.index)
    d.loc[fill, "filing_date"] = d.loc[fill, "application_id"].map(rf)
    d["days_exposed"] = (pd.Timestamp(ASOF) - d["filing_date"]).dt.days
    d = d.dropna(subset=["days_exposed"])
    ev = resp.set_index("app_id")["days"]
    d["event"] = d.application_id.isin(ev.index).astype(int)
    d["time"] = np.where(d.event == 1, d.application_id.map(ev), d.days_exposed)
    grid = np.arange(0, 31)
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    for st, lab in [("ALL", "All states"), ("TN", "Tamil Nadu"), ("KA", "Karnataka")]:
        s = d if st == "ALL" else d[d.state == st]
        if s.empty or s.event.sum() == 0:
            continue
        ci = km(s.time, s.event, grid)
        ax.step(grid, 100 * ci, where="post", label=f"{lab} (n={len(s)}, events={int(s.event.sum())})")
    ax.axvline(30, color="gray", lw=0.8, ls=":"); ax.set_ylim(0, 8); ax.text(29.6, 7.6, "statutory deadline", fontsize=7, color="gray", ha="right", va="top")
    ax.set_xlabel("Days since filing"); ax.set_ylabel("Applications with a PIO document (%)")
    ax.set_xlim(0, 31); ax.legend(frameon=False, fontsize=7, loc="lower right")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig_km.pdf")); plt.close(fig)
    # numbers for text
    s = d; ci = km(s.time, s.event, [7, 14, 21, 28])
    atrisk = {t: int((s.time >= t).sum()) for t in [7, 14, 21, 28]}
    write("km_stats.tex", "".join(f"\\newcommand{{\\km{n}}}{{{100*v:.1f}}}\\newcommand{{\\risk{n}}}{{{atrisk[t]}}}" for n, t, v in zip(["Seven", "Fourteen", "TwentyOne", "TwentyEight"], [7, 14, 21, 28], ci)) + "\n")


def main():
    drawn = load_drawn(); filed = load_filed(); resp = load_responses()
    table_design(drawn); m = table_filing(drawn, filed); table_balance(m); table_exposure(filed); table_responses(resp); table_access()
    fig_timeline(filed); fig_km(filed, resp)
    nd = int(filed[filed.filed == 1].filing_date.notna().sum()); nf = int(filed.filed.sum()); nr = int(filed.has_receipt.sum())
    write("counts.tex", f"\\newcommand{{\\nDrawn}}{{{len(drawn)}}}\\newcommand{{\\nFiled}}{{{nf}}}\\newcommand{{\\nReceipt}}{{{nr}}}\\newcommand{{\\nDated}}{{{nd}}}\\newcommand{{\\nResp}}{{{len(resp)}}}\\newcommand{{\\asof}}{{{ASOF:%d %B %Y}}}\n")
    print(f"drawn={len(drawn)} filed={nf} dated={nd} responses={len(resp)}")
    print(filed.groupby('state').agg(filed=('filed','sum'), receipt=('has_receipt', 'sum'), dated=('filing_date', lambda s: s.notna().sum())))


if __name__ == "__main__":
    main()
