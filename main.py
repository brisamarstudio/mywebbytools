import os
import io
import zipfile
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

app = FastAPI(
    title="MyWebby Agency Tools - Private Media Suite",
    description="Suite riservata MyWebby Agency: Favicon Generator PRO, HEIC & Batch Image Resizer, Image Crop.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
IMAGES_DIR = os.path.join(BASE_DIR, "images")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if os.path.exists(IMAGES_DIR):
    app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

INDEX_HTML_PATH = os.path.join(STATIC_DIR, "index.html")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    if os.path.exists(INDEX_HTML_PATH):
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>MyWebby Agency Tools</h1><p>index.html non trovato.</p>")


@app.get("/health")
async def health_check():
    return {"status": "ok", "agency": "MyWebby Agency", "service": "mywebbytools", "version": "2.0.0"}


# --- API 1: FAVICON & APP ICON GENERATOR PRO ---
@app.post("/api/generate-favicons")
async def generate_favicons(file: UploadFile = File(...)):
    """
    Genera al volo il pacchetto completo Favicon & App Icons:
    - favicon.ico (16x16, 32x32, 48x48)
    - favicon-16x16.png
    - favicon-32x32.png
    - apple-touch-icon.png (180x180)
    - android-chrome-192x192.png
    - android-chrome-512x512.png
    - site.webmanifest
    """
    img_data = await file.read()
    try:
        base_img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # 1. favicon-16x16.png
            img16 = base_img.resize((16, 16), Image.Resampling.LANCZOS)
            b16 = io.BytesIO()
            img16.save(b16, format="PNG")
            zip_file.writestr("favicon-16x16.png", b16.getvalue())

            # 2. favicon-32x32.png
            img32 = base_img.resize((32, 32), Image.Resampling.LANCZOS)
            b32 = io.BytesIO()
            img32.save(b32, format="PNG")
            zip_file.writestr("favicon-32x32.png", b32.getvalue())

            # 3. apple-touch-icon.png (180x180)
            img180 = base_img.resize((180, 180), Image.Resampling.LANCZOS)
            b180 = io.BytesIO()
            img180.save(b180, format="PNG")
            zip_file.writestr("apple-touch-icon.png", b180.getvalue())

            # 4. android-chrome-192x192.png
            img192 = base_img.resize((192, 192), Image.Resampling.LANCZOS)
            b192 = io.BytesIO()
            img192.save(b192, format="PNG")
            zip_file.writestr("android-chrome-192x192.png", b192.getvalue())

            # 5. android-chrome-512x512.png
            img512 = base_img.resize((512, 512), Image.Resampling.LANCZOS)
            b512 = io.BytesIO()
            img512.save(b512, format="PNG")
            zip_file.writestr("android-chrome-512x512.png", b512.getvalue())

            # 6. favicon.ico
            img_ico = base_img.resize((48, 48), Image.Resampling.LANCZOS)
            b_ico = io.BytesIO()
            img_ico.save(b_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
            zip_file.writestr("favicon.ico", b_ico.getvalue())

            # 7. site.webmanifest
            manifest_content = """{
    "name": "MyWebby Site",
    "short_name": "WebbyApp",
    "icons": [
        {
            "src": "/android-chrome-192x192.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "/android-chrome-512x512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ],
    "theme_color": "#ffffff",
    "background_color": "#ffffff",
    "display": "standalone"
}"""
            zip_file.writestr("site.webmanifest", manifest_content)

        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=favicon_pack.zip"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore generazione favicon: {str(e)}")


# --- API 2: BATCH IMAGE RESIZER & HEIC TO WEBP CONVERTER ---
@app.post("/api/resize-images")
async def resize_images(
    files: List[UploadFile] = File(...),
    max_width: int = Form(1920),
    output_format: str = Form("webp"),
    quality: int = Form(80)
):
    if not files:
        raise HTTPException(status_code=400, detail="Nessuna immagine caricata.")
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file in files:
                img_data = await file.read()
                img = Image.open(io.BytesIO(img_data))
                
                # Auto rotate based on EXIF
                try:
                    from PIL import ImageOps
                    img = ImageOps.exif_transpose(img)
                except Exception:
                    pass

                w, h = img.size
                if w > max_width:
                    new_h = int((max_width / w) * h)
                    img = img.resize((max_width, new_h), Image.Resampling.LANCZOS)

                target_format = output_format.upper()
                if target_format == "JPG":
                    target_format = "JPEG"
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")

                out_b = io.BytesIO()
                img.save(out_b, format=target_format, quality=quality, optimize=True)
                ext = output_format.lower()
                clean_filename = os.path.splitext(file.filename)[0] + f"_ottimizzato.{ext}"
                zip_file.writestr(clean_filename, out_b.getvalue())

        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=immagini_ottimizzate.zip"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore ottimizzazione immagini: {str(e)}")
