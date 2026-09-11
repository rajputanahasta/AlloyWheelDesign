from pathlib import Path
from io import BytesIO
import fitz, re, json, hashlib, shutil
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]; CAT=ROOT/'catalogues'; SITE=ROOT/'site'; ASSETS=SITE/'wheel_dashboard_assets'; TPL=ROOT/'dashboard_template.html'
SIZE=re.compile(r'(?<!\d)(\d{2}(?:\.\d)?)[xX](\d{1,2}(?:\.\d)?)(?:J|JJ)?\b'); ET=re.compile(r'\bET\s*[-:]?\s*(-?\d{1,3})\b',re.I); CB=re.compile(r'\bCB\s*[-:]?\s*(\d{2,3}(?:\.\d)?)\b',re.I); PCD=re.compile(r'\b(\d{1,2}X\d{2,3}(?:\.\d)?)\b',re.I)
BRANDS=set('AUDI BMW BENZ MERCEDES VOLKSWAGEN VW TOYOTA HONDA FORD CHEVROLET JEEP PORSCHE TESLA NISSAN INFINITI LEXUS MAZDA SUBARU HYUNDAI KIA VOLVO SKODA PEUGEOT RENAULT FIAT MG BYD GMC RAM DODGE CADILLAC CHRYSLER SUZUKI MITSUBISHI ISUZU'.split())
COLORS=['GUNMETAL MACHINE FACE','BLACK MACHINE FACE','BLACK MACHINED','MATT BLACK','MATTE BLACK','GLOSS BLACK','SATIN BLACK','MACHINE FACE','MACHINED FACE','SILVER','BLACK','GUNMETAL','GREY','GRAY','WHITE','BRONZE','GOLD','CHROME','RED','BLUE']
def clean(s): return re.sub(r'\s+',' ',s or '').strip()
def stock(s): return int(s) if re.fullmatch(r'\d+',clean(s)) else None
def parse(line,last=''):
    m=SIZE.search(line)
    if not m:return None,last
    size=f'{m.group(1)}x{m.group(2)}'; before=line[:m.start()]
    toks=clean(before).split(); model=''
    for t in reversed(toks):
        if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]{1,30}',t) and t.upper() not in {'MODEL','SIZE','PHOTO','PICTURE'}: model=t;break
    model=model or last
    et=(ET.search(line).group(1) if ET.search(line) else '')
    cb=(CB.search(line).group(1) if CB.search(line) else '')
    pcd=(PCD.search(line).group(1).upper() if PCD.search(line) else '')
    u=line.upper(); color=next((c.title() for c in COLORS if c in u),'')
    cm=re.search(r'\b(?:COLOR|COLOUR)\s*[:#-]?\s*([A-Z0-9-]{2,20})',line,re.I); code=cm.group(1) if cm else ''
    vehicle=' '.join(dict.fromkeys(t.title() for t in re.findall(r'[A-Za-z][A-Za-z-]+',line) if t.upper() in BRANDS))
    return {'model':model,'size':size,'et':et,'cb':cb,'pcd':pcd,'color_code':code,'color':color,'vehicle':vehicle},model

def imgs(page,src,pno):
    out=[]
    for ix,x in enumerate(page.get_images(full=True)):
        try:
            raw=page.parent.extract_image(x[0])['image']; im=Image.open(BytesIO(raw)).convert('RGB')
            if im.width<100 or im.height<100: continue
            im.thumbnail((1000,1000),Image.LANCZOS); fn=f'{src}_p{pno}_i{ix}_{hashlib.sha1(raw).hexdigest()[:12]}.jpg'; im.save(ASSETS/fn,'JPEG',quality=84,optimize=True); out.append(fn)
        except: pass
    return out

def process(pdf):
    doc=fitz.open(pdf); rec=[]; last=''
    for pno,page in enumerate(doc,1):
        lines=[clean(x) for x in page.get_text('text').splitlines() if clean(x)]; images=imgs(page,pdf.stem,pno); page_rows=[]
        for i,line in enumerate(lines):
            # Combine nearby PDF text fragments; this handles split table cells.
            block=' '.join(lines[max(0,i-1):min(len(lines),i+3)])
            r,last2=parse(block,last)
            if r:
                last=last2; page_rows.append(r)
        # dedupe overlapping windows
        uniq=[]; seen=set()
        for r in page_rows:
            k=tuple(r[x].upper() for x in ['model','size','et','cb','pcd','color_code','color'])
            if k not in seen: seen.add(k); uniq.append(r)
        for j,r in enumerate(uniq):
            r.update(source=pdf.stem,source_file=pdf.name,page=pno,image=(images[j] if j<len(images) else (images[0] if len(images)==1 else '')),stock=None); rec.append(r)
    doc.close(); return rec

def main():
    if SITE.exists(): shutil.rmtree(SITE)
    ASSETS.mkdir(parents=True,exist_ok=True)
    allr=[]
    pdfs=sorted(CAT.glob('*.pdf'))
    for pdf in pdfs:
        print('Scanning',pdf.name); allr += process(pdf)
    # Numeric stock: only use explicit stock sections and pure integer lines. Sequential mapping is used when the PDF's stock table follows catalogue order.
    by={}
    for r in allr: by.setdefault(r['source_file'],[]).append(r)
    for pdf in pdfs:
        try: doc=fitz.open(pdf)
        except: continue
        vals=[]; active=False
        for page in doc:
            lines=[clean(x) for x in page.get_text('text').splitlines() if clean(x)]
            for line in lines:
                if re.search(r'\bSTOCK\b',line,re.I): active=True; continue
                if active and re.fullmatch(r'\d+',line): vals.append(int(line))
        doc.close(); rows=by.get(pdf.name,[])
        for i,v in enumerate(vals[:len(rows)]): rows[i]['stock']=v
    # Deduplicate variants, preferring photo and numeric stock.
    out={}
    for r in allr:
        if not r['model'] or not r['size']: continue
        k=tuple((r[x] or '').upper() for x in ['model','size','et','cb','pcd','color_code','color'])
        old=out.get(k)
        if not old or (r['stock'] is not None, bool(r['image']),sum(bool(r[x]) for x in ['et','cb','pcd','color','vehicle'])) > (old['stock'] is not None,bool(old['image']),sum(bool(old[x]) for x in ['et','cb','pcd','color','vehicle'])): out[k]=r
    data=sorted(out.values(),key=lambda r:(r['model'].upper(),r['size'],r['pcd'],r['et'],r['color']))
    (SITE/'wheel_stock_database.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    html=TPL.read_text(encoding='utf-8').replace('__DATA__',json.dumps(data,ensure_ascii=False,separators=(',',':')))
    (SITE/'index.html').write_text(html,encoding='utf-8')
    print('Built',len(data),'variants;',sum(bool(r['image']) for r in data),'photos;',sum(r['stock'] is not None for r in data),'numeric stock')
if __name__=='__main__': main()
