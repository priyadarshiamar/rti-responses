#!/usr/bin/env python3
"""OCR every filing receipt in Filed_RTI/ and extract registration number + date of filing.
Output: analysis/_cache/receipts.csv (app_id, file, reg_no, filing_date, method)."""
import os,re,csv,subprocess,glob,tempfile
DRIVE=os.path.expanduser("~/Library/CloudStorage/GoogleDrive-pamar@clio.uc3m.es/.shortcut-targets-by-id/1nlnBaoUheM3B-oo-qPBwQmsIciHUBmRz/rti/Filed_RTI")
OUT=os.path.expanduser("~/rti-responses/analysis/_cache/receipts.csv")
LOOSE=re.compile(r"\b(TN|KA|TG|DL|MH)\b[^0-9]{0,24}?(\d{3})\b")
done={}
if os.path.exists(OUT):
    for r in csv.DictReader(open(OUT)): done[r["file"]]=r
rows=list(done.values())
def text_of(path):
    try: open(path,"rb").read(1)
    except OSError: pass
    t=subprocess.run(["pdftotext","-layout",path,"-"],capture_output=True,text=True).stdout
    if len(re.sub(r"\s","",t))>=40: return t,"pdftotext"
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm","-r","150","-png","-f","1","-l","2",path,d+"/p"],capture_output=True)
        out=[]
        for png in sorted(glob.glob(d+"/p*.png")):
            out.append(subprocess.run(["tesseract",png,"stdout","-l","eng","--psm","6"],capture_output=True,text=True).stdout)
        return "\n".join(out),"tesseract"
for root,_,files in os.walk(DRIVE):
    for fn in sorted(files):
        if not fn.lower().endswith((".pdf",".png",".jpg",".jpeg")): continue
        path=os.path.join(root,fn); rel=os.path.relpath(path,DRIVE)
        if rel in done: continue
        m=LOOSE.search(fn.upper().replace("_","-")); app=f"{m.group(1)}-{m.group(2)}" if m else ""
        if path.lower().endswith(".pdf"): t,meth=text_of(path)
        else:
            t=subprocess.run(["tesseract",path,"stdout","-l","eng","--psm","6"],capture_output=True,text=True).stdout; meth="tesseract"
        reg=re.search(r"([A-Z]{4,6}/R/20\d\d/\d{5})",t)
        date=re.search(r"(?:Date of Filing|Date of Submission|Filing Date)[^0-9]{0,40}(\d{2})[-/.](\d{2})[-/.](\d{4})",t,re.I)
        if not date: date=re.search(r"\b(\d{2})[-/](\d{2})[-/](20\d\d)\b",t)
        fd=f"{date.group(3)}-{date.group(2)}-{date.group(1)}" if date else ""
        rows.append({"app_id":app,"file":rel,"reg_no":reg.group(1) if reg else "","filing_date":fd,"method":meth})
        with open(OUT,"w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["app_id","file","reg_no","filing_date","method"]); w.writeheader(); w.writerows(rows)
print("receipts:",len(rows),"with date:",sum(1 for r in rows if r["filing_date"]),"with reg:",sum(1 for r in rows if r["reg_no"]))
