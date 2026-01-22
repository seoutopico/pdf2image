# PDF to Images Service

Microservicio para convertir PDF a imagenes base64. Pensado para usar con n8n Cloud + GPT-4o Vision.

## Uso con n8n

1. Despliega este servicio en Coolify (o cualquier servidor)
2. En n8n, usa HTTP Request para enviar el PDF
3. Recibe las imagenes en base64
4. Envia cada imagen a GPT-4o Vision

## API

### Health Check
```
GET /health
```

### Convertir PDF a Imagenes
```
POST /pdf-to-images
Content-Type: multipart/form-data

Params:
- file: PDF (required)
- dpi: 150 (default)
- format: jpeg|png (default: png)
```

**Response:**
```json
{
  "filename": "documento.pdf",
  "total_pages": 5,
  "dpi": 150,
  "format": "png",
  "pages": [
    {
      "index": 0,
      "width": 1275,
      "height": 1650,
      "image_base64": "data:image/png;base64,..."
    }
  ]
}
```

## Despliegue en Coolify

1. Conecta este repositorio en Coolify
2. Coolify detectara el Dockerfile automaticamente
3. Configura el puerto 8000
4. Despliega

## Desarrollo Local

```bash
pip install -r requirements.txt
python main.py
```

El servicio estara en http://localhost:8000

## Docs

Una vez desplegado, accede a `/docs` para ver la documentacion interactiva de FastAPI.
