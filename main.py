"""
Microservicio para convertir PDF a imagenes base64.
Uso: n8n envia PDF, recibe imagenes para GPT-4o Vision.

v2: Soporte para procesar pagina por pagina (evita memoria en n8n Cloud)
"""

import base64
import uuid
import os
import time
import threading
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF

app = FastAPI(title="PDF to Images Service", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Almacenamiento temporal de PDFs (en memoria)
pdf_storage = {}
STORAGE_TTL = 600  # 10 minutos

def cleanup_old_pdfs():
    """Limpia PDFs antiguos cada 5 minutos"""
    while True:
        time.sleep(300)
        now = time.time()
        to_delete = [k for k, v in pdf_storage.items() if now - v["timestamp"] > STORAGE_TTL]
        for k in to_delete:
            del pdf_storage[k]

# Iniciar limpieza en background
cleanup_thread = threading.Thread(target=cleanup_old_pdfs, daemon=True)
cleanup_thread.start()


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0", "stored_pdfs": len(pdf_storage)}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Sube un PDF y devuelve un ID para procesar paginas individualmente.

    Response: { "id": "uuid", "filename": "doc.pdf", "total_pages": 30 }
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "El archivo debe ser PDF")

    try:
        pdf_bytes = await file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_pages = len(doc)
        doc.close()

        pdf_id = str(uuid.uuid4())
        pdf_storage[pdf_id] = {
            "bytes": pdf_bytes,
            "filename": file.filename,
            "total_pages": total_pages,
            "timestamp": time.time()
        }

        return {
            "id": pdf_id,
            "filename": file.filename,
            "total_pages": total_pages
        }
    except Exception as e:
        raise HTTPException(500, f"Error procesando PDF: {str(e)}")


@app.get("/page/{pdf_id}/{page_number}")
def get_page(pdf_id: str, page_number: int, dpi: int = 150, format: str = "jpeg"):
    """
    Obtiene una pagina especifica de un PDF previamente subido.

    - pdf_id: ID devuelto por /upload
    - page_number: Numero de pagina (0-indexed)
    - dpi: Resolucion (default 150)
    - format: jpeg o png (default jpeg para menor tamanio)

    Response: { "page": 0, "total_pages": 30, "image_base64": "data:image/jpeg;base64,..." }
    """
    if pdf_id not in pdf_storage:
        raise HTTPException(404, "PDF no encontrado. Sube el archivo primero con /upload")

    stored = pdf_storage[pdf_id]

    if page_number < 0 or page_number >= stored["total_pages"]:
        raise HTTPException(400, f"Pagina invalida. El PDF tiene {stored['total_pages']} paginas (0-{stored['total_pages']-1})")

    try:
        doc = fitz.open(stream=stored["bytes"], filetype="pdf")
        page = doc[page_number]

        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        pix = page.get_pixmap(matrix=matrix, alpha=False)
        if format == "png":
            img_bytes = pix.tobytes("png")
            mime = "image/png"
        else:
            img_bytes = pix.tobytes("jpeg")
            mime = "image/jpeg"

        b64 = base64.b64encode(img_bytes).decode('utf-8')
        doc.close()

        # Actualizar timestamp para extender TTL
        stored["timestamp"] = time.time()

        return {
            "page": page_number,
            "total_pages": stored["total_pages"],
            "width": pix.width,
            "height": pix.height,
            "image_base64": f"data:{mime};base64,{b64}"
        }
    except Exception as e:
        raise HTTPException(500, f"Error procesando pagina: {str(e)}")


@app.delete("/pdf/{pdf_id}")
def delete_pdf(pdf_id: str):
    """Elimina un PDF del almacenamiento temporal"""
    if pdf_id in pdf_storage:
        del pdf_storage[pdf_id]
        return {"status": "deleted"}
    raise HTTPException(404, "PDF no encontrado")


# Mantener endpoint original para compatibilidad (PDFs pequenios)
@app.post("/pdf-to-images")
async def pdf_to_images(
    file: UploadFile = File(...),
    dpi: int = 150,
    format: str = "jpeg"
):
    """
    Convierte PDF completo a imagenes base64.
    ADVERTENCIA: Puede causar problemas de memoria con PDFs grandes.
    Para PDFs grandes, usar /upload + /page/{id}/{page}
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "El archivo debe ser PDF")

    try:
        pdf_bytes = await file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        pages = []
        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        for page_num in range(len(doc)):
            page = doc[page_num]

            pix = page.get_pixmap(matrix=matrix, alpha=False)
            if format == "png":
                img_bytes = pix.tobytes("png")
                mime = "image/png"
            else:
                img_bytes = pix.tobytes("jpeg")
                mime = "image/jpeg"

            b64 = base64.b64encode(img_bytes).decode('utf-8')

            pages.append({
                "index": page_num,
                "width": pix.width,
                "height": pix.height,
                "image_base64": f"data:{mime};base64,{b64}"
            })

        doc.close()

        return {
            "filename": file.filename,
            "total_pages": len(pages),
            "dpi": dpi,
            "format": format,
            "pages": pages
        }

    except Exception as e:
        raise HTTPException(500, f"Error procesando PDF: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
