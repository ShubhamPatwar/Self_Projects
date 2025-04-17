from flask import Flask, request, send_file, render_template, jsonify
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
from PIL import Image
import os
import io

app = Flask(__name__)

# Use absolute paths to avoid errors when running from different directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def remove_white_background(image_path):
    img = Image.open(image_path).convert("RGBA")
    datas = img.getdata()
    new_data = []
    for item in datas:
        if item[0] > 200 and item[1] > 200 and item[2] > 200:
            new_data.append((255, 255, 255, 0))  # Transparent
        else:
            new_data.append(item)
    img.putdata(new_data)

    transparent_io = io.BytesIO()
    img.save(transparent_io, format="PNG")
    transparent_io.seek(0)
    return transparent_io

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sign-pdf', methods=['POST'])
def sign_pdf():
    if 'pdf' not in request.files or 'signature' not in request.files:
        return jsonify({"error": "Missing file(s). Require 'pdf' and 'signature'."}), 400

    pdf_file = request.files['pdf']
    signature_file = request.files['signature']

    pdf_filename = secure_filename(pdf_file.filename)
    sig_filename = secure_filename(signature_file.filename)

    pdf_path = os.path.join(UPLOAD_FOLDER, pdf_filename)
    sig_path = os.path.join(UPLOAD_FOLDER, sig_filename)

    pdf_file.save(pdf_path)
    signature_file.save(sig_path)

    try:
        x = int(request.form.get('x'))
        y = int(request.form.get('y'))
        width = int(request.form.get('width', 150))
        height = int(request.form.get('height', 50))
        page_num = int(request.form.get('page', 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid coordinate or size input."}), 400

    transparent_sig_io = remove_white_background(sig_path)

    try:
        doc = fitz.open(pdf_path)
        if page_num < 0 or page_num >= len(doc):
            return jsonify({"error": "Page number out of range."}), 400

        page = doc[page_num]
        rect = fitz.Rect(x, y, x + width, y + height)
        page.insert_image(rect, stream=transparent_sig_io, keep_proportion=True)

        output_filename = f"signed_{pdf_filename}"
        output_path = os.path.join(UPLOAD_FOLDER, output_filename)
        doc.save(output_path)
        doc.close()

        return send_file(output_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500

if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5005, debug=True)

