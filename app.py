import os
import requests
from flask import Flask, request, jsonify, send_file
from pdf2image import convert_from_bytes
from io import BytesIO

app = Flask(__name__)

# Función para descargar el PDF desde la URL
def download_pdf(pdf_url):
    response = requests.get(pdf_url)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception("No se pudo descargar el PDF. Verifica la URL.")

# Función para convertir PDF a imágenes PNG
def convert_pdf_to_png(pdf_content):
    images = convert_from_bytes(pdf_content)
    image_files = []
    
    for i, image in enumerate(images):
        img_io = BytesIO()
        image.save(img_io, 'PNG')
        img_io.seek(0)
        image_files.append(img_io)
    
    return image_files

# Endpoint para recibir la URL del PDF y devolver un PNG
@app.route('/convert', methods=['POST'])
def convert_pdf():
    data = request.get_json()
    pdf_url = data.get('pdf_url')
    
    if not pdf_url:
        return jsonify({"error": "Se requiere la URL del PDF"}), 400

    try:
        # Descargar el PDF desde la URL
        pdf_content = download_pdf(pdf_url)

        # Convertir el PDF a PNG
        png_images = convert_pdf_to_png(pdf_content)

        # Devolver la primera página del PDF como PNG (puedes cambiarlo si quieres más páginas)
        return send_file(png_images[0], mimetype='image/png', as_attachment=True, download_name='page_1.png')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
