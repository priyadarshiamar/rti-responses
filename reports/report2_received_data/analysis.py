#!/usr/bin/env python3
"""Report 2: what the state told us about itself. Tables and figures by provenance.
A = enclosed in replies; B = from websites the replies cited (TN SIC, CIC); C = sought by us (deferred)."""
import os, re, csv, collections
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TN = pd.read_csv(os.path.join(ROOT, "commission_reports/tn/tn_sic_annex_keyed.csv"), dtype=str)
CIC_P = os.path.join(ROOT, "commission_reports/cic/cic_delhi_annex.csv")
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
NUM = ["pios","opening","received","total","transferred","replied","rej_s8","rej_s9","rej_s11","rej_s24","rej_other","rej_total","pending","charges_rs","fee_rs","penalty_rs","faas","fa_received","fa_disposed","fa_rejected","fa_pending","fa_total"]
for c in NUM: TN[c] = pd.to_numeric(TN[c], errors="coerce")
TN["year"] = TN["year"].astype(int); TN["is_total"] = TN["is_total"].astype(int)
A = TN[TN.is_total == 0].copy()
A["rejected"] = A["rej_total"].where(A["rej_total"].notna(), A[["rej_s8","rej_s9","rej_s11","rej_s24","rej_other"]].sum(axis=1, min_count=1))
def esc(s): return str(s).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("#", r"\#")
def write(n, t): open(os.path.join(HERE, n), "w").write(t + "\n")
def fmt(x, d=0): return "--" if pd.isna(x) else (f"{x:,.{d}f}")

# ---------------- B1 state-level series
def b1():
    g = A.groupby("year").agg(auth=("key","nunique"), received=("received","sum"), transferred=("transferred","sum"), replied=("replied","sum"),
                              rejected=("rejected","sum"), pending=("pending","sum"), fa=("fa_received","sum"), charges=("charges_rs","sum"), pios=("pios","sum"))
    g["reply_share"] = g.replied / g.received; g["transfer_share"] = g.transferred / g.received; g["reject_share"] = g.rejected / g.received
    g["fa_rate"] = g.fa / g.received; g["charge_per_req"] = g.charges / g.received
    rows = [f"{y} & {int(r.auth)} & {fmt(r.received)} & {100*r.transfer_share:.1f} & {100*r.reply_share:.1f} & {100*r.reject_share:.2f} & {100*r.fa_rate:.1f} & {fmt(r.charge_per_req,1)} \\\\" for y, r in g.iterrows()]
    write("tab_b1.tex", "\n".join(rows))
    fig, axes = plt.subplots(2, 3, figsize=(6.4, 3.6)); axes = axes.ravel()
    for ax, (col, lab, sc) in zip(axes, [("received","Requests received","k"),("transfer_share","Transferred u/s 6(3) (share)","pct"),("reply_share","Replied with information (share)","pct"),
                                          ("reject_share","Rejected (share)","pct"),("fa_rate","First appeals per request","pct"),("charge_per_req","Charges per request (Rs)","rs")]):
        y = g[col] * (100 if sc == "pct" else 1) / (1000 if sc == "k" else 1)
        ax.plot(g.index, y, marker="o", ms=3, lw=1.2, color="#1c5cab"); ax.set_title(lab + (" (thousand)" if sc == "k" else " (%)" if sc == "pct" else ""), fontsize=8)
        for xv, t in [(2019.8, "2019 amdt"), (2023.6, "DPDP")]: ax.axvline(xv, color="gray", lw=0.6, ls=":")
        ax.set_xticks([2015, 2019, 2023]); ax.tick_params(labelsize=7)
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig_b1.pdf")); plt.close(fig)
    return g

# ---------------- B2 department concentration
def b2():
    d = A[A.year == 2023].copy()
    dep = d.groupby("dept_hint").agg(auth=("key","nunique"), received=("received","sum"), replied=("replied","sum"), transferred=("transferred","sum"), rejected=("rejected","sum"), fa=("fa_received","sum")).sort_values("received", ascending=False)
    dep = dep[dep.index != ""]
    tot = dep.received.sum(); dep["share"] = dep.received / tot
    rows = [f"{esc(k[:52])} & {int(r.auth)} & {fmt(r.received)} & {100*r.share:.1f} & {100*r.transferred/r.received:.0f} & {100*r.replied/r.received:.0f} & {100*r.rejected/r.received:.1f} & {100*r.fa/r.received:.1f} \\\\" for k, r in dep.head(15).iterrows()]
    rows.append(r"\midrule " + f"All departments & {dep.auth.sum()} & {fmt(tot)} & 100 & {100*dep.transferred.sum()/tot:.0f} & {100*dep.replied.sum()/tot:.0f} & {100*dep.rejected.sum()/tot:.1f} & {100*dep.fa.sum()/tot:.1f} \\\\")
    write("tab_b2.tex", "\n".join(rows))
    # concentration figure: cumulative share of requests vs share of authorities, 2023
    a = d.sort_values("received", ascending=False); cs = a.received.cumsum() / a.received.sum(); xs = np.arange(1, len(a)+1) / len(a)
    fig, ax = plt.subplots(figsize=(3.4, 2.6)); ax.plot(100*xs, 100*cs, color="#1c5cab", lw=1.4); ax.plot([0,100],[0,100], color="gray", lw=0.6, ls=":")
    k10 = cs.iloc[int(len(a)*0.1)-1]; ax.annotate(f"top 10% of authorities\nhandle {100*k10:.0f}% of requests", xy=(10, 100*k10), xytext=(25, 40), fontsize=7, arrowprops=dict(arrowstyle="-", color="gray", lw=0.6))
    ax.set_xlabel("Authorities, ranked by volume (%)"); ax.set_ylabel("Cumulative requests (%)"); fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig_b2.pdf")); plt.close(fig)
    top10 = 100*k10
    write("b2_stats.tex", f"\\newcommand{{\\bTopTen}}{{{top10:.0f}}}\\newcommand{{\\bNauthTwentyThree}}{{{d.key.nunique()}}}")

# ---------------- B3 persistence / two-way FE
def b3():
    p = A[(A.received > 0)].copy(); p["reply_share"] = p.replied / p.received; p["fa_rate"] = p.fa_received / p.received; p["lrec"] = np.log(p.received)
    p = p[p.reply_share.between(0, 1.2)]
    # keep keys present >= 5 years
    keep = p.groupby("key").year.nunique(); p = p[p.key.isin(keep[keep >= 5].index)]
    out = []
    for col, lab in [("lrec","log requests received"),("reply_share","reply share"),("fa_rate","first appeals per request")]:
        q = p.dropna(subset=[col])
        m = smf.ols(f"{col} ~ C(key) + C(year)", data=q).fit()
        m0 = smf.ols(f"{col} ~ C(year)", data=q).fit()
        between = m.rsquared - m0.rsquared
        # lag-1 autocorrelation within authority
        q = q.sort_values(["key","year"]); q["lag"] = q.groupby("key")[col].shift(1); q["dy"] = q.year - q.groupby("key").year.shift(1)
        ac = q[q.dy == 1][[col,"lag"]].corr().iloc[0,1]
        out.append(f"{lab} & {q.key.nunique()} & {len(q)} & {between:.2f} & {ac:.2f} \\\\")
    write("tab_b3.tex", "\n".join(out))
    # year effects for reply share (event-study style, 2018 base)
    q = p.dropna(subset=["reply_share"]); m = smf.ols("reply_share ~ C(key) + C(year, Treatment(2018))", data=q).fit(cov_type="cluster", cov_kwds={"groups": q["key"]})
    ys = sorted(q.year.unique()); coef = [0 if y == 2018 else m.params.get(f"C(year, Treatment(2018))[T.{y}]", np.nan) for y in ys]
    se = [0 if y == 2018 else m.bse.get(f"C(year, Treatment(2018))[T.{y}]", np.nan) for y in ys]
    fig, ax = plt.subplots(figsize=(3.6, 2.5)); ax.errorbar(ys, 100*np.array(coef), yerr=100*1.96*np.array(se), fmt="o", ms=3, color="#1c5cab", capsize=2, lw=1)
    ax.axhline(0, color="gray", lw=0.6); ax.axvline(2019.8, color="gray", lw=0.6, ls=":"); ax.set_ylabel("Reply share, pp vs 2018"); ax.set_xlabel("Year")
    fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig_b3.pdf")); plt.close(fig)
    write("b3_stats.tex", f"\\newcommand{{\\bThreeN}}{{{q.key.nunique()}}}")

# ---------------- B4 tier as routing layer (2023 + pooled)
def b4():
    d = A[A.received > 0].copy()
    g = d.groupby(["tier"]).agg(auth=("key","nunique"), rows=("key","size"), received=("received","sum"), transferred=("transferred","sum"), replied=("replied","sum"), rejected=("rejected","sum"), pios=("pios","sum"), fa=("fa_received","sum"))
    rows = [f"{esc(t)} & {int(r.auth)} & {fmt(r.received/9)} & {100*r.transferred/r.received:.0f} & {100*r.replied/r.received:.0f} & {100*r.rejected/r.received:.1f} & {r.received/r.pios:.0f} & {100*r.fa/r.received:.1f} \\\\" for t, r in g.iterrows()]
    write("tab_b4.tex", "\n".join(rows))

# ---------------- B5 appeals funnel
def b5():
    g = A.groupby("year").agg(received=("received","sum"), fa=("fa_received","sum"), fa_disp=("fa_disposed","sum"), fa_rej=("fa_rejected", lambda s: s.sum(min_count=1)), fa_pend=("fa_pending", lambda s: s.sum(min_count=1)))
    sic = {2019: (None, None), 2023: (21476, 8369)}
    rows = [f"{y} & {fmt(r.received)} & {fmt(r.fa)} & {100*r.fa/r.received:.1f} & {fmt(r.fa_disp)} & {fmt(r.fa_rej)} & {fmt(r.fa_pend)} & {fmt(sic.get(y,(None,None))[0])} & {fmt(sic.get(y,(None,None))[1])} \\\\" for y, r in g.iterrows()]
    write("tab_b5.tex", "\n".join(rows))

# ---------------- B7 match to the audit sample
def b7():
    asg = pd.read_csv(os.path.join(ROOT, "analysis/_cache/assignments_TN.csv"), dtype=str)
    top = asg[asg.tier.isin(["Department","Head of Department"])].copy()
    def norm(s):
        s = s.lower().replace("&"," and "); s = re.sub(r"[^a-z0-9 ]"," ",s)
        s = re.sub(r"\b(the|of|and|department|dept|tamil|nadu|tamilnadu|corporation|limited|ltd|directorate|commissionerate|office|govt|government|chennai)\b"," ",s)
        return re.sub(r"\s+"," ",s).strip()
    import difflib
    keys = A[A.year >= 2021].groupby("key").agg(canonical=("canonical","first"), received=("received","mean"), replied=("replied","mean"), transferred=("transferred","mean"), fa=("fa_received","mean")).reset_index()
    keys["n"] = keys.key.map(norm)
    rows = []; matched = 0; scores = []
    for _, r in top.iterrows():
        n = norm(r.office_name)
        cands = keys.n.tolist(); best = difflib.get_close_matches(n, cands, n=1, cutoff=0.75)
        if not best and r.tier == "Department":
            best = difflib.get_close_matches(n + " secretariat", cands, n=1, cutoff=0.75)
        if best:
            k = keys[keys.n == best[0]].iloc[0]; matched += 1; sc = difflib.SequenceMatcher(None, n, best[0]).ratio(); scores.append(sc)
            rows.append({"application_id": r.application_id, "tier": r.tier, "office_name": r.office_name, "key": k.key, "canonical": k.canonical, "score": round(sc,2), "received_mean_2021_23": round(k.received,1), "reply_share": round(k.replied/k.received,2) if k.received else np.nan, "transfer_share": round(k.transferred/k.received,2) if k.received else np.nan, "fa_rate": round(k.fa/k.received,3) if k.received else np.nan})
        else:
            rows.append({"application_id": r.application_id, "tier": r.tier, "office_name": r.office_name, "key": "", "canonical": "", "score": np.nan})
    M = pd.DataFrame(rows); M.to_csv(os.path.join(HERE, "data", "tn_sample_commission_covariates.csv"), index=False)
    out = []
    for t in ["Department","Head of Department"]:
        s = M[M.tier == t]; mm = s[s.key != ""]
        out.append(f"{t} & {len(s)} & {len(mm)} & {100*len(mm)/len(s):.0f} & {fmt(mm.received_mean_2021_23.median())} & {100*mm.reply_share.median():.0f} & {100*mm.transfer_share.median():.0f} \\\\")
    s = M; mm = s[s.key != ""]
    out.append(r"\midrule All & " + f"{len(s)} & {len(mm)} & {100*len(mm)/len(s):.0f} & {fmt(mm.received_mean_2021_23.median())} & {100*mm.reply_share.median():.0f} & {100*mm.transfer_share.median():.0f} \\\\")
    write("tab_b7.tex", "\n".join(out))
    # sampled vs not, HOD level: compare medians
    hod = keys[keys.canonical.str.contains("Secretariat", case=False) == False]
    write("b7_stats.tex", f"\\newcommand{{\\bSevenMatched}}{{{len(mm)}}}\\newcommand{{\\bSevenTotal}}{{{len(s)}}}\\newcommand{{\\bSevenAllHOD}}{{{len(hod)}}}\\newcommand{{\\bSevenUnRecv}}{{{fmt(hod.received.median())}}}")

# ---------------- B8 Delhi
def b8():
    if not os.path.exists(CIC_P): write("tab_b8.tex", "Delhi & -- \\\\"); return
    c = pd.read_csv(CIC_P); c = c[c.name.str.contains("merged") == False]
    for col in ["opening","received","total","transferred","fa_received","fa_disposed","replied","rejected","fee_rs","charges_rs","penalty_rs","cpios"]: c[col] = pd.to_numeric(c[col], errors="coerce")
    g = c.groupby("year").agg(auth=("code","nunique"), received=("received","sum"), transferred=("transferred","sum"), replied=("replied", lambda v: v.sum(min_count=1)), rejected=("rejected","sum"), fa=("fa_received","sum"), fee=("fee_rs","sum"), charges=("charges_rs","sum"), pen=("penalty_rs","sum"))
    rows = [f"{y} & {int(r.auth)} & {fmt(r.received)} & {100*r.transferred/r.received:.1f} & {"--" if pd.isna(r.replied) else f"{100*r.replied/r.received:.1f}"} & {100*r.rejected/r.received:.1f} & {100*r.fa/r.received:.1f} & {fmt((r.fee+r.charges)/r.received,1)} & {fmt(r.pen)} \\\\" for y, r in g.iterrows()]
    write("tab_b8.tex", "\n".join(rows))
    # top Delhi authorities latest year
    ly = c[c.year == c.year.max()].sort_values("received", ascending=False).head(12)
    rows2 = [f"{esc(r['name'][:55])} & {fmt(r.received)} & {100*r.transferred/r.received:.0f} & {100*r.replied/r.received:.0f} & {100*r.rejected/r.received:.1f} & {100*r.fa_received/r.received:.1f} \\\\" for _, r in ly.iterrows() if r.received]
    write("tab_b8b.tex", "\n".join(rows2)); write("b8_stats.tex", f"\\newcommand{{\\bEightYear}}{{{c.year.max()}}}")

# ---------------- A1 triangulation, A2 format I
def a1():
    coop = A.name.str.contains("Co-operation", case=False, na=False) | A.dept_hint.str.contains("Co-operation", case=False, na=False)
    sec = A.name.str.contains("Secretariat", case=False, na=False)
    s = A[coop & sec].drop_duplicates("year").sort_values("year")
    rows = [f"{int(r.year)} & Commission annual report (B) & calendar year & {fmt(r.received)} & {fmt(r.transferred)} & {fmt(r.replied)} & {fmt(r.fa_received)} \\\\" for _, r in s.iterrows()]
    rows.append(r"2025 & Own s.25(2) return enclosed with reply (A) & calendar year & 502 & 430 & 103 & 51 \\")
    rows.append(r"Aug 2025--Jul 2026 & Register letter in reply (A) & 12 months & 712 & 712 & -- & -- \\")
    write("tab_a1.tex", "\n".join(rows))
    fig, ax = plt.subplots(figsize=(3.6, 2.4)); ax.plot(s.year, s.received, marker="o", ms=3, color="#1c5cab", label="Commission report (B)")
    ax.scatter([2025], [502], color="#eb6834", zorder=3, label="Own s.25 return (A)"); ax.scatter([2026], [712], color="#1baf7a", zorder=3, label="Register letter, Aug 25--Jul 26 (A)")
    ax.set_ylabel("Requests received"); ax.legend(frameon=False, fontsize=6.5, loc="lower right"); ax.set_xticks(range(2015, 2027, 2)); fig.tight_layout(); fig.savefig(os.path.join(HERE, "fig_a1.pdf")); plt.close(fig)

def a2():
    f = pd.read_csv(os.path.join(HERE, "data", "sec25_format1_tn173_2025.csv"))
    rows = [f"{esc(r.authority)} & {r.pios} & {fmt(r.received_2025)} & {100*r.transferred_6_3/r.received_2025:.0f} & {100*r.disposed_with_info/r.received_2025:.0f} & {100*r.rejected/r.received_2025:.1f} & {100*r.fa_received/r.received_2025:.1f} & {fmt((r.fee_rs+r.charges_rs)/r.received_2025,1)} \\\\" for _, r in f.iterrows()]
    t = f.sum(numeric_only=True)
    rows.append(r"\midrule Department total & " + f"{int(t.pios)} & {fmt(t.received_2025)} & {100*t.transferred_6_3/t.received_2025:.0f} & {100*t.disposed_with_info/t.received_2025:.0f} & {100*t.rejected/t.received_2025:.1f} & {100*t.fa_received/t.received_2025:.1f} & {fmt((t.fee_rs+t.charges_rs)/t.received_2025,1)} \\\\")
    write("tab_a2.tex", "\n".join(rows))
    # compare with commission 2023 rows for the same authorities
    comp = []
    for _, r in f.iterrows():
        n = r.authority.split(",")[0].lower()[:22]
        m = A[(A.year == 2023) & (A.canonical.str.lower().str.contains(re.escape(n), na=False))]
        if len(m): comp.append(f"{esc(r.authority)} & {fmt(m.received.iloc[0])} & {fmt(r.received_2025)} & {100*m.replied.iloc[0]/m.received.iloc[0]:.0f} & {100*r.disposed_with_info/r.received_2025:.0f} \\\\")
    write("tab_a2b.tex", "\n".join(comp))

def a3():
    g = pd.read_csv(os.path.join(HERE, "data", "register_extracts_in_replies.csv"), dtype=str).fillna("")
    rows = [f"{r.app_id} & {esc(r.authority)} & {r.format} & {esc(r.period.replace(' to ', ' to\\newline '))} & {r.received or '--'} & {r.transferred or '--'} & {r.replied or '--'} & {esc(r.notes)} \\\\" for _, r in g.iterrows()]
    write("tab_a3.tex", "\n".join(rows))

def quality():
    t = TN[TN.is_total == 0]
    ok1 = (t.chk_total.astype(str) == "1").sum(); n1 = (t.chk_total.astype(str) != "").sum() - (t.chk_total.astype(str) == "nan").sum()
    ok2 = (t.chk_disposal.astype(str) == "1").sum(); n2 = (t.chk_disposal.astype(str).isin(["0","1"])).sum()
    n1 = (t.chk_total.astype(str).isin(["0","1"])).sum()
    ky = t.groupby("key").year.nunique()
    write("quality_stats.tex", f"\\newcommand{{\\qRows}}{{{len(t)}}}\\newcommand{{\\qOkTot}}{{{100*ok1/n1:.1f}}}\\newcommand{{\\qOkDisp}}{{{100*ok2/n2:.1f}}}\\newcommand{{\\qKeys}}{{{len(ky)}}}\\newcommand{{\\qKeysNine}}{{{(ky==9).sum()}}}\\newcommand{{\\qKeysSeven}}{{{(ky>=7).sum()}}}\\newcommand{{\\qKeysOne}}{{{(ky==1).sum()}}}")

if __name__ == "__main__":
    b1(); b2(); b3(); b4(); b5(); b7(); b8(); a1(); a2(); a3(); quality(); print("done")
