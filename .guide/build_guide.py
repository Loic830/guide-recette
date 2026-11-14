#!/usr/bin/env python3
"""
Guide de recettes — construit Guide.html à partir des PDF et images du dossier.

Usage : python3 build_guide.py [dossier_des_recettes]

- Chaque sous-dossier = une catégorie.
- Seuls les fichiers nouveaux ou modifiés sont traités (cache dans .guide/cache.json).
- Une image portant le même nom qu'un PDF (ex. « Chili.jpg » à côté de « Chili.pdf »)
  sert de miniature personnalisée.
"""
import base64, hashlib, io, json, os, re, shutil, subprocess, sys, tempfile, time, unicodedata

import pymupdf as fitz
from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.dirname(HERE)
CACHE_PATH = os.path.join(HERE, "cache.json")
TEMPLATE_PATH = os.path.join(HERE, "template.html")
OUTPUT_PATH = os.path.join(ROOT, "Guide.html")
CACHE_VERSION = 5

PDF_EXT = {".pdf"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
SKIP_DIRS = {".guide", "_test_guide"}
THUMB_W = 480
PAGE_W = 1100

# ---------------------------------------------------------------- utilitaires

def nfc(s):
    return unicodedata.normalize("NFC", s)

def log(msg):
    print(msg, flush=True)

def file_md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def jpeg_data_uri(img, max_w, quality):
    img = img.convert("RGB")
    if img.width > max_w:
        img = img.resize((max_w, round(img.height * max_w / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

def pix_to_pil(pix):
    if pix.alpha:
        pix = fitz.Pixmap(pix, 0)
    if pix.n - pix.alpha >= 4 or pix.colorspace is None or pix.colorspace.n not in (1, 3):
        pix = fitz.Pixmap(fitz.csRGB, pix)
    mode = "L" if pix.n == 1 else "RGB"
    return Image.frombytes(mode, (pix.width, pix.height), pix.samples)

def render_page(page, width):
    zoom = width / page.rect.width
    return pix_to_pil(page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False))

def open_image(path):
    if path.lower().endswith(".heic"):
        try:
            import pillow_heif  # optionnel
            pillow_heif.register_heif_opener()
        except Exception:
            pass
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")

# ---------------------------------------------------------------- OCR

_OCR_ENGINE = None

def ocr_engine():
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        _OCR_ENGINE = "none"
        try:
            from ocrmac import ocrmac  # macOS : moteur Vision d'Apple
            _OCR_ENGINE = "vision"
        except Exception:
            if shutil.which("tesseract"):
                _OCR_ENGINE = "tesseract"
    return _OCR_ENGINE

def ocr_image(img):
    eng = ocr_engine()
    try:
        if eng == "vision":
            from ocrmac import ocrmac
            res = ocrmac.OCR(img, recognition_level="accurate",
                             language_preference=["fr-FR", "en-US"]).recognize()
            # trier de haut en bas (bbox : x, y, w, h avec origine en bas)
            res.sort(key=lambda r: (-round(r[2][1] + r[2][3], 2), r[2][0]))
            return "\n".join(r[0] for r in res)
        if eng == "tesseract":
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as t:
                img.save(t.name)
            out = subprocess.run(["tesseract", t.name, "stdout", "-l", "fra+eng", "--psm", "3"],
                                 capture_output=True, text=True).stdout
            os.unlink(t.name)
            return out
    except Exception as e:
        log(f"    (OCR impossible : {e})")
    return ""

def word_score(text):
    return len(re.findall(r"[A-Za-zÀ-ÿ]{3,}", text))

def best_rotation(img):
    """Essaie les 4 orientations et garde celle où l'OCR lit le plus de mots."""
    small = img.copy()
    small.thumbnail((1400, 1400))
    best = (word_score(ocr_image(small)), 0)
    if best[0] > 60:
        return 0
    for angle in (90, 270, 180):
        s = word_score(ocr_image(small.rotate(angle, expand=True)))
        if s > best[0]:
            best = (s, angle)
    return best[1]

# ---------------------------------------------------------------- titres et sources

SOURCES = [
    ("5 ingredients 15 minutes", "5 ingrédients 15 minutes"),
    ("roxanne cuisine", "Roxanne Cuisine"),
    ("savourer x mordu", "Savourer x Mordu"),
    ("mordu", "Mordu"),
    ("ricardo", "Ricardo"),
    ("kraft", "Kraft"),
    ("recettes du québec", "Recettes du Québec"),
    ("recettes québecoises", "Recettes Québécoises"),
    ("recettes iga", "IGA"),
    ("je cuisine", "Je Cuisine"),
    ("radio-canada", "Radio-Canada"),
    ("coup de pouce", "Coup de pouce"),
    ("trois fois par jour", "Trois fois par jour"),
    ("les recettes de caty", "Les recettes de Caty"),
    ("tupperware", "Tupperware"),
    ("eagle brand", "Eagle Brand"),
    ("snackworks", "Snackworks"),
    ("chocolats favoris", "Chocolats Favoris"),
]

def match_source(seg):
    if not seg:
        return None
    low = seg.lower()
    flat = re.sub(r"[^a-zà-ÿ0-9]", "", low)
    for key, name in SOURCES:
        if key in low or re.sub(r"[^a-zà-ÿ0-9]", "", key) in flat:
            return name
    return None

def clean_title(t):
    t = t.strip(" -|–—")
    t = re.sub(r"^recette (de |d['’]|du |des )", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t)
    return t[:1].upper() + t[1:]

def parse_name(stem):
    stem = nfc(stem).replace("_", " ")
    title, source = stem, None
    if " | " in stem:
        parts = [p.strip() for p in stem.split(" | ")]
        title = parts[0]
        source = match_source(" ".join(parts[1:])) or parts[1].title() if parts[1].isupper() else (match_source(parts[1]) or parts[1])
    elif " - " in stem:
        parts = [p.strip() for p in stem.split(" - ")]
        if match_source(parts[0]) and len(parts) > 1:      # « Eagle Brand® - Barres magiques »
            source, title = match_source(parts[0]), " - ".join(parts[1:])
        else:
            title = parts[0]
            source = match_source(parts[1]) or parts[1]
    m = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", title)          # « Barres Smores (Guylaine) »
    if m and not source:
        title, source = m.group(1), m.group(2)
    if source:
        source = re.sub(r"^recettes? ", "", source, flags=re.I) if not match_source(source) else source
        source = source[:1].upper() + source[1:]
    return clean_title(title), source

# ---------------------------------------------------------------- nettoyage du texte

BOILER = [
    re.compile(r"^\d{4}-\d{2}-\d{2},? \d{1,2}:\d{2}"),        # 2026-02-01, 19:54
    re.compile(r"^page \d+ (of|sur|de) \d+$", re.I),
    re.compile(r"^https?://\S+$"),
    re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4},? \d{1,2}:\d{2}"),
]

def clean_text(raw, title, stem=""):
    raw = unicodedata.normalize("NFKC", raw)
    out, tnorm = [], title.lower()
    snorm = unicodedata.normalize("NFKC", nfc(stem)).lower()[:40]
    for line in raw.splitlines():
        s = line.strip()
        if not s or any(p.search(s) for p in BOILER):
            continue
        if s.lower() == tnorm or (len(snorm) > 12 and s.lower().startswith(snorm)):
            continue
        out.append(s)
    text = "\n".join(out)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def find_url(raw):
    m = re.search(r"https?://[^\s<>\"]+", raw)
    if not m:
        return None
    url = m.group(0).rstrip(".,)")
    return url

# ---------------------------------------------------------------- traitement d'un PDF

def is_scan(page):
    """Page sans texte, couverte par une seule grande image."""
    if len(page.get_text().strip()) > 30:
        return False
    area = abs(page.rect)
    for im in page.get_images(full=True):
        for r in page.get_image_rects(im[0]):
            if abs(r) > 0.6 * area:
                return True
    return False

def best_photo(doc):
    """Plus grande photo affichée (en ignorant logos, icônes, filets et scans pleine page)."""
    best = None
    for pno, page in enumerate(doc):
        parea = abs(page.rect)
        scan = is_scan(page)
        for im in page.get_images(full=True):
            xref, w, h = im[0], im[2], im[3]
            if w < 150 or h < 150:
                continue
            if max(w, h) / min(w, h) > 2.5:
                continue
            rects = page.get_image_rects(xref)
            if not rects:
                continue
            shown = max(abs(r) for r in rects)
            if (scan and shown > 0.6 * parea) or shown < 4000:
                continue
            score = shown + (w * h) / 400.0
            if best is None or score > best[0]:
                best = (score, xref)
    if not best:
        return None
    try:
        img = pix_to_pil(fitz.Pixmap(doc, best[1]))
        if img.width < 150:
            return None
        return img
    except Exception:
        return None

def page_is_empty(page, text):
    if len(text) > 60:
        return False
    parea = abs(page.rect)
    for im in page.get_images(full=True):
        for r in page.get_image_rects(im[0]):
            if abs(r) > 0.05 * parea:
                return False
    return True

def process_pdf(path, title, cover):
    stem = os.path.splitext(os.path.basename(path))[0]
    doc = fitz.open(path)
    raw_all, texts, pages, page_imgs = [], [], [], []
    first_render = None
    for page in doc:
        raw = page.get_text()
        raw_all.append(raw)
        if is_scan(page):
            img = render_page(page, 2000)
            angle = best_rotation(img)
            if angle:
                img = img.rotate(angle, expand=True)
            text = clean_text(ocr_image(img), title, stem)
            texts.append(text)
            pages.append(jpeg_data_uri(img, PAGE_W, 62))
            page_imgs.append(img)
            continue
        text = clean_text(raw, title, stem)
        if page_is_empty(page, text) and pages:
            continue
        img = render_page(page, PAGE_W)
        pages.append(jpeg_data_uri(img, PAGE_W, 62))
        page_imgs.append(img)
        texts.append(text)
    if not pages:
        img = render_page(doc[0], PAGE_W)
        pages.append(jpeg_data_uri(img, PAGE_W, 62))
        page_imgs.append(img)

    # Miniature : couverture perso > plus grande photo > page la plus remplie
    thumb_kind = "photo"
    if cover:
        thumb = open_image(cover)
    else:
        thumb = best_photo(doc)
        if thumb is None:
            thumb_kind = "page"
            idx = max(range(len(page_imgs)), key=lambda i: len(texts[i]) if i < len(texts) else 0)
            thumb = page_imgs[idx]
    return {
        "text": "\n\n".join(t for t in texts if t),
        "url": find_url("\n".join(raw_all)),
        "pages": pages,
        "thumb": jpeg_data_uri(thumb, THUMB_W, 72),
        "thumbKind": thumb_kind,
        "nPages": len(doc),
    }

def process_image(path, title, cover):
    img = open_image(path)
    text = clean_text(ocr_image(img), title)
    th = open_image(cover) if cover else img
    return {
        "text": text, "url": None,
        "pages": [jpeg_data_uri(img, PAGE_W, 70)],
        "thumb": jpeg_data_uri(th, THUMB_W, 72),
        "thumbKind": "photo", "nPages": 1,
    }

# ---------------------------------------------------------------- inventaire

def scan_folder():
    items = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS)
        rel_dir = os.path.relpath(dirpath, ROOT)
        names = {os.path.splitext(f)[0]: f for f in filenames}
        stems_pdf = {os.path.splitext(f)[0] for f in filenames if os.path.splitext(f)[1].lower() in PDF_EXT}
        for f in sorted(filenames):
            if f.startswith("."):
                continue
            stem, ext = os.path.splitext(f)
            ext = ext.lower()
            if ext in IMG_EXT and stem in stems_pdf:
                continue                     # image de couverture d'un PDF
            if ext not in PDF_EXT | IMG_EXT:
                continue
            if rel_dir == "." :
                continue                     # on ne prend que les fichiers dans les catégories
            cover = None
            if ext in PDF_EXT:
                for f2 in filenames:
                    s2, e2 = os.path.splitext(f2)
                    if s2 == stem and e2.lower() in IMG_EXT:
                        cover = os.path.join(dirpath, f2)
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
            items.append({
                "id": nfc(rel), "rel": rel, "full": full, "ext": ext, "cover": cover,
                "cat": nfc(rel_dir.split(os.sep)[0]),
                "sub": nfc(" / ".join(rel_dir.split(os.sep)[1:])),
            })
    return items

# ---------------------------------------------------------------- programme principal

def main():
    t0 = time.time()
    log(f"📂 Dossier : {ROOT}")
    cache = {}
    if os.path.exists(CACHE_PATH):
        try:
            c = json.load(open(CACHE_PATH, encoding="utf-8"))
            if c.get("version") == CACHE_VERSION:
                cache = c.get("items", {})
        except Exception:
            cache = {}

    by_md5 = {v.get("md5"): v for v in cache.values() if v.get("md5")}
    items = scan_folder()
    log(f"🔎 {len(items)} recettes trouvées — moteur OCR : {ocr_engine()}")
    new_cache, recipes, n_new = {}, [], 0
    for it in items:
        st = os.stat(it["full"])
        sig_parts = [str(st.st_size)]
        quick = f'{st.st_size}:{int(st.st_mtime)}'
        if it["cover"]:
            cst = os.stat(it["cover"])
            quick += f'|{cst.st_size}:{int(cst.st_mtime)}'
        old = cache.get(it["id"])
        data = None
        if old and old.get("quick") == quick:
            data = old
        else:
            md5 = file_md5(it["full"]) + (("|" + file_md5(it["cover"])) if it["cover"] else "")
            if old and old.get("md5") == md5:
                data = dict(old, quick=quick)
            elif md5 in by_md5:                      # fichier déplacé ou renommé : rien à retraiter
                data = dict(by_md5[md5], quick=quick)
                t2, s2 = parse_name(os.path.splitext(os.path.basename(it["rel"]))[0])
                data["title"] = t2
                data["source"] = s2 or data.get("source")
                log(f"  ↪︎ déplacé : {it['cat']} / {t2}")
            else:
                n_new += 1
                title, source = parse_name(os.path.splitext(os.path.basename(it["rel"]))[0])
                log(f"  ➕ {it['cat']} / {title}")
                try:
                    proc = process_pdf if it["ext"] in PDF_EXT else process_image
                    data = proc(it["full"], title, it["cover"])
                except Exception as e:
                    log(f"    ⚠️  Impossible de lire ce fichier : {e}")
                    continue
                if not source:   # pas de source dans le nom : on la devine depuis l'URL ou le début du texte
                    source = match_source(data.get("url")) or match_source(data["text"][:300])
                data.update(title=title, source=source, md5=md5, quick=quick)
        new_cache[it["id"]] = data
        recipes.append({
            "id": it["id"], "file": it["rel"], "cat": it["cat"], "sub": it["sub"],
            "key": data["md5"].split("|")[0][:16],
            "title": data["title"], "source": data["source"], "url": data["url"],
            "thumb": data["thumb"], "thumbKind": data.get("thumbKind", "photo"),
            "text": data["text"], "pages": data["pages"],
            "added": int(st.st_mtime),
            "type": "pdf" if it["ext"] in PDF_EXT else "image",
        })

    kept = {v.get("md5") for v in new_cache.values()}
    removed = sum(1 for v in cache.values() if v.get("md5") not in kept)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"version": CACHE_VERSION, "items": new_cache}, f, ensure_ascii=False)

    write_html(recipes)
    size = os.path.getsize(OUTPUT_PATH) / 1e6
    log(f"\n✅ Guide.html à jour : {len(recipes)} recettes "
        f"({n_new} nouvelle(s), {removed} retirée(s)) — {size:.1f} Mo — {time.time() - t0:.0f} s")

def write_html(recipes):
    recipes.sort(key=lambda r: unicodedata.normalize("NFD", r["title"].lower()))
    meta, page_blocks = [], []
    for i, r in enumerate(recipes):
        m = {k: r[k] for k in ("id", "key", "file", "cat", "sub", "title", "source", "url", "thumb",
                                "thumbKind", "text", "added", "type")}
        m["n"] = len(r["pages"])
        m["k"] = i
        meta.append(m)
        page_blocks.append(
            f'<script type="text/plain" id="pg{i}">' + "\n".join(r["pages"]) + "</script>")
    cats = sorted({r["cat"] for r in recipes}, key=lambda c: unicodedata.normalize("NFD", c.lower()))
    payload = {"generated": int(time.time()), "cats": cats, "recipes": meta}
    js = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    tpl = open(TEMPLATE_PATH, encoding="utf-8").read()
    html = tpl.replace("/*__DATA__*/null", js).replace("<!--__PAGES__-->", "\n".join(page_blocks))
    tmp = OUTPUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    os.replace(tmp, OUTPUT_PATH)

if __name__ == "__main__":
    main()
