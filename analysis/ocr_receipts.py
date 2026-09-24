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
import time
def fetch(path, tries=15):
    """Force Google Drive to materialise a cloud-only file; return its first bytes or b''."""
    for i in range(tries):
        try:
            with open(path,"rb") as f:
                head=f.read(8)
                f.seek(0, 2)
                if f.tell()>0 and head: return head
        except OSError:
            pass
        time.sleep(4)
    return b""
def text_of(path):
    head=fetch(path)
    if not head: return "","unavailable"
    if head.startswith(b"\x89PNG") or head[:3]==b"\xff\xd8\xff":
        return subprocess.run(["tesseract",path,"stdout","-l","eng","--psm","6"],capture_output=True,text=True).stdout,"tesseract_image"
    if head[:5].lower() in (b"<!doc",b"<html") or b"<htm" in head.lower():
        raw=open(path,"rb").read().decode("utf-8","ignore"); return re.sub(r"<[^>]+>"," ",raw),"html"
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
        if rel in done and (done[rel]["filing_date"] or done[rel]["method"] in ("pdftotext",)): continue
        if rel in done: rows=[r for r in rows if r["file"]!=rel]
        m=LOOSE.search(fn.upper().replace("_","-")); app=f"{m.group(1)}-{m.group(2)}" if m else ""
        t,meth=text_of(path)
        reg=re.search(r"([A-Z]{4,6}/R/20\d\d/\d{5})",t)
        date=re.search(r"(?:Date of Filing|Date of Submission|Filing Date|Date of Receipt|Applied on|Application Date|Date)[^0-9]{0,40}(\d{2})[-/.](\d{2})[-/.](\d{4})",t,re.I)
        if not date: date=re.search(r"\b(\d{2})[-/](\d{2})[-/](20\d\d)\b",t)
        fd=f"{date.group(3)}-{date.group(2)}-{date.group(1)}" if date else ""
        rows.append({"app_id":app,"file":rel,"reg_no":reg.group(1) if reg else "","filing_date":fd,"method":meth})
        with open(OUT,"w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=["app_id","file","reg_no","filing_date","method"]); w.writeheader(); w.writerows(rows)
print("receipts:",len(rows),"with date:",sum(1 for r in rows if r["filing_date"]),"with reg:",sum(1 for r in rows if r["reg_no"]))
