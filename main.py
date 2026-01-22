"""
Microservicio para convertir PDF a imágenes base64.
Uso: n8n envía PDF, recibe imágenes para GPT-4o Vision.
"""

import base64
import io
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF

app = FastAPI(title="PDF to Images Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/pdf-to-images")
async def pdf_to_images(
    file: UploadFile = File(...),
    dpi: int = 150,
    format: str = "png"
):
    """
    Convierte PDF a imágenes base64.

    - file: PDF a convertir
    - dpi: Resolución (default 150, suficiente para Vision)
    - format: png o jpeg

    Retorna: { "pages": [{ "index": 0, "image_base64": "data:image/png;base64,..." }] }
    """

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(400, "El archivo debe ser PDF")

    try:
        pdf_bytes = await file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        pages = []
        zoom = dpi / 72  # 72 es el DPI base de PDF
        matrix = fitz.Matrix(zoom, zoom)

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Renderizar página a imagen
            if format == "jpeg":
                pix = page.get_pixmap(matrix=matrix)
                img_bytes = pix.tobytes("jpeg", quality=85)
                mime = "image/jpeg"
            else:
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                img_bytes = pix.tobytes("png")
                mime = "image/png"

            # Convertir a base64
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
