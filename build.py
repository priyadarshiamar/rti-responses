#!/usr/bin/env python3
"""Build the RTI response dashboard.

1. Scan the Drive `rti responses/` folder for PDFs (forcing cloud-only files to download).
2. Extract a text layer for every file (pdftotext, falling back to tesseract OCR) into text/.
3. Join responses_coded.csv with the assignment sheets (treatment arm, RA, tier).
4. Count filed applications per state from Filed_RTI/.
5. Emit data.json, files_index.csv, and index.html (template.html with the data embedded).

Run:  python3 build.py            (from any cwd)
      python3 build.py --no-ocr   (skip OCR of new scans; faster)
"""
import csv, json, os, re, subprocess, sys, statistics, datetime, glob, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
DRIVE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-pamar@clio.uc3m.es/.shortcut-targets-by-id/"
    "1nlnBaoUheM3B-oo-qPBwQmsIciHUBmRz/rti")
RESP_DIR = os.path.join(DRIVE, "rti responses")
FILED_DIR = os.path.join(DRIVE, "Filed_RTI")
TEXT_DIR = os.path.join(HERE, "text")
CODED = os.path.join(HERE, "responses_coded.csv")
TEMPLATE = os.path.join(HERE, "template.html")
OUT_HTML = os.path.join(HERE, "docs", "index.html")
OUT_JSON = os.path.join(HERE, "docs", "data.json")
OUT_INDEX = os.path.join(HERE, "data", "files_index.csv")
DO_OCR = "--no-ocr" not in sys.argv

STATE_NAMES = {"TN": "Tamil Nadu", "KA": "Karnataka", "TG": "Telangana", "DL": "Delhi", "MH": "Maharashtra"}
# Tolerates the RAs' spellings: "TN-052", "TG - 041", "TG -132", "TG RTI Online __ 004", "RTI_KA-055"
_LOOSE = re.compile(r"\b(TN|KA|TG|DL|MH)\b[^0-9]{0,24}?(\d{3})\b")


class _IdMatcher:
    def search(self, s):
        m = _LOOSE.search(s)
        if not m:
            return None
        norm = f"{m.group(1)}-{m.group(2)}"
        class R:  # minimal stand-in so callers can keep using .group(1)
            def group(self, _): return norm
        return R()


ID_RE = _IdMatcher()


def force_download(path):
    try:
        with open(path, "rb") as f:
            f.read(1)
    except OSError:
        pass


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def extract_text(pdf, dest_txt):
    """pdftotext first; OCR when the text layer is empty."""
    r = sh(["pdftotext", "-layout", pdf, "-"])
    text = r.stdout if r.returncode == 0 else ""
    used = "pdftotext"
    if len(re.sub(r"\s", "", text)) < 50 and DO_OCR and shutil.which("tesseract"):
        used = "tesseract"
        tmp = os.path.join(TEXT_DIR, "_tmp")
        os.makedirs(tmp, exist_ok=True)
        for f in glob.glob(os.path.join(tmp, "*")):
            os.remove(f)
        sh(["pdftoppm", "-r", "150", "-png", pdf, os.path.join(tmp, "p")])
        pages = []
        for png in sorted(glob.glob(os.path.join(tmp, "p*.png"))):
            pages.append(sh(["tesseract", png, "stdout", "-l", "eng"]).stdout)
        text = "\n\f\n".join(pages)
    with open(dest_txt, "w") as f:
        f.write(text)
    return text, used


def scan_responses():
    os.makedirs(TEXT_DIR, exist_ok=True)
    rows = []
    for root, _, files in os.walk(RESP_DIR):
        for fn in files:
            if not fn.lower().endswith(".pdf") or fn.startswith("."):
                continue
            path = os.path.join(root, fn)
            force_download(path)
            st = os.stat(path)
            m = ID_RE.search(fn.upper().replace("_", "-"))
            app_id = m.group(1) if m else ""
            rel = os.path.relpath(path, RESP_DIR)
            txt_path = os.path.join(TEXT_DIR, re.sub(r"[^A-Za-z0-9._-]", "_", rel) + ".txt")
            meta_path = txt_path + ".meta"
            stamp = f"{st.st_size}:{int(st.st_mtime)}"
            used = "cached"
            if not (os.path.exists(meta_path) and open(meta_path).read().strip() == stamp) or st.st_size == 0:
                if st.st_size > 0:
                    _, used = extract_text(path, txt_path)
                    open(meta_path, "w").write(stamp)
                else:
                    used = "not_downloaded"
            chars = len(re.sub(r"\s", "", open(txt_path).read())) if os.path.exists(txt_path) else 0
            pages = ""
            pi = sh(["pdfinfo", path]).stdout
            pm = re.search(r"Pages:\s+(\d+)", pi)
            if pm:
                pages = int(pm.group(1))
            rows.append({
                "file": rel, "app_id": app_id, "state": STATE_NAMES.get(app_id[:2], "") if app_id else "",
                "bytes": st.st_size, "pages": pages,
                "modified": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
                "text_chars": chars, "text_source": used,
            })
    rows.sort(key=lambda r: (r["app_id"], r["file"]))
    return rows


def count_filed():
    ids = {}
    for root, _, files in os.walk(FILED_DIR):
        for fn in files:
            m = ID_RE.search(fn.upper().replace("_", "-"))
            if m:
                ids.setdefault(m.group(1)[:2], set()).add(m.group(1))
    return {STATE_NAMES.get(k, k): len(v) for k, v in ids.items()}


def load_assignments():
    info = {}
    for fn in ["assignments.csv", "assignments_TG.csv"]:
        p = os.path.join(DRIVE, fn)
        if not os.path.exists(p):
            continue
        force_download(p)
        with open(p, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                info[r["application_id"]] = {
                    "ra": r.get("assigned_ra", ""), "treatment": r.get("treatment", ""),
                    "tier": r.get("tier", "") or r.get("dept_group", ""),
                    "department": r.get("tree_department", "") or r.get("dept_group", ""),
                }
    return info


def main():
    files = scan_responses()
    filed = count_filed()
    assign = load_assignments()
    with open(CODED, encoding="utf-8-sig") as f:
        coded = list(csv.DictReader(f))
    for r in coded:
        a = assign.get(r["app_id"], {})
        r["ra"] = r.get("ra") or a.get("ra", "")
        r["treatment"] = r.get("treatment") or a.get("treatment", "")
        r["tier"] = r.get("tier") or a.get("tier", "")
        r["department"] = a.get("department", "")
        try:
            d0 = datetime.date.fromisoformat(r["filing_date"]); d1 = datetime.date.fromisoformat(r["response_date"])
            r["days"] = (d1 - d0).days
        except Exception:
            r["days"] = None
        r["files"] = [x["file"] for x in files if x["app_id"] == r["app_id"]]
    coded_ids = {r["app_id"] for r in coded}
    uncoded = sorted({x["app_id"] for x in files if x["app_id"] and x["app_id"] not in coded_ids})
    unmatched = [x["file"] for x in files if not x["app_id"]]

    days = [r["days"] for r in coded if r["days"] is not None]
    data = {
        "built_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "filed_by_state": filed,
        "filed_total": sum(filed.values()),
        "responses": coded,
        "files": files,
        "uncoded_app_ids": uncoded,
        "unmatched_files": unmatched,
        "summary": {
            "responded_apps": len(coded),
            "median_days": statistics.median(days) if days else None,
            "fee_total": sum(float(r["fee_inr"] or 0) for r in coded),
            "appeal_candidates": sum(1 for r in coded if r.get("appeal_candidate") == "1"),
        },
    }
    os.makedirs(os.path.dirname(OUT_HTML), exist_ok=True)
    json.dump(data, open(OUT_JSON, "w"), indent=1, ensure_ascii=False)
    with open(OUT_INDEX, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(files[0].keys()) if files else ["file"])
        w.writeheader(); w.writerows(files)
    html = open(TEMPLATE).read().replace("/*__DATA__*/null", json.dumps(data, ensure_ascii=False))
    open(OUT_HTML, "w").write(html)
    print(f"files={len(files)} coded={len(coded)} uncoded={uncoded} unmatched={unmatched} filed={filed}")


if __name__ == "__main__":
    main()
