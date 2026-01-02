from flask import Flask, render_template, request
import requests
from io import BytesIO
from werkzeug.utils import secure_filename
from ubah1 import main as process_pdf
from ubah2 import main as process_excel

app = Flask(__name__)

ALLOWED_EXTENSIONS = {"pdf", "xlsx", "xls"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Render form or process uploaded files/links. Supports both POST submissions
    and GET requests with a `pdf_url` query parameter for extension integration.
    """
    # Handle GET with pdf_url query parameter
    if request.method == "GET":
        pdf_url = request.args.get("pdf_url", default="").strip()
        # If the pdf_url parameter is provided, process it directly
        if pdf_url:
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                response = requests.get(pdf_url, headers=headers, timeout=15)
                # Validate response status
                if response.status_code == 404:
                    return render_template("error.html", message="Link tidak ditemukan (404). Periksa kembali URL Anda.")
                elif response.status_code != 200:
                    return render_template("error.html", message=f"Gagal mengakses link. Status Code: {response.status_code}")
                # Determine file extension from Content-Type or URL
                file_obj = BytesIO(response.content)
                content_type = response.headers.get("Content-Type", "").lower()
                if "pdf" in content_type:
                    file_extension = "pdf"
                elif "excel" in content_type or "spreadsheet" in content_type:
                    file_extension = "xlsx"
                else:
                    # fallback to extension based on URL
                    if pdf_url.endswith(".xlsx"):
                        file_extension = "xlsx"
                    elif pdf_url.endswith(".xls"):
                        file_extension = "xls"
                    else:
                        file_extension = "pdf"
                # Process based on determined file type
                if file_extension == "pdf":
                    data_records = process_pdf(file_obj)
                elif file_extension in ["xlsx", "xls"]:
                    data_records = process_excel(file_obj)
                else:
                    return render_template("error.html", message="Tipe file tidak dapat diproses.")
                if not data_records:
                    return render_template("error.html", message="Data tidak ditemukan atau file kosong.")
                return render_template("preview.html", rows=data_records)
            except requests.exceptions.ConnectionError:
                return render_template("error.html", message="Gagal koneksi server. Pastikan link benar dan aktif.")
            except Exception as e:
                return render_template("error.html", message=f"Terjadi kesalahan pada link: {str(e)}")
        # Without pdf_url param, just render index page
        return render_template("index.html")

    # Handle POST submission (existing behaviour)
    if request.method == "POST":
        try:
            file_obj = None
            filename = "downloaded_file.pdf"
            file_extension = "pdf"

            # Process uploaded file
            if "file" in request.files and request.files["file"].filename != "":
                file = request.files["file"]
                if not allowed_file(file.filename):
                    return render_template("error.html", message="Format file tidak diizinkan! Hanya PDF (.pdf) dan Excel (.xlsx/.xls) yang diperbolehkan.")
                file_obj = file
                filename = secure_filename(file.filename)
                file_extension = filename.rsplit(".", 1)[1].lower()

            # Process link submitted via form
            elif "pdf_url" in request.form and request.form["pdf_url"].strip() != "":
                url = request.form["pdf_url"].strip()
                try:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code == 404:
                        return render_template("error.html", message="Link tidak ditemukan (404). Periksa kembali URL Anda.")
                    elif response.status_code != 200:
                        return render_template("error.html", message=f"Gagal mengakses link. Status Code: {response.status_code}")
                    file_obj = BytesIO(response.content)
                    content_type = response.headers.get("Content-Type", "").lower()
                    if "pdf" in content_type:
                        file_extension = "pdf"
                    elif "excel" in content_type or "spreadsheet" in content_type:
                        file_extension = "xlsx"
                    else:
                        if url.endswith(".xlsx"):
                            file_extension = "xlsx"
                        elif url.endswith(".xls"):
                            file_extension = "xls"
                        else:
                            file_extension = "pdf"
                except requests.exceptions.ConnectionError:
                    return render_template("error.html", message="Gagal koneksi server. Pastikan link benar dan aktif.")
                except Exception as e:
                    return render_template("error.html", message=f"Terjadi kesalahan pada link: {str(e)}")
            else:
                return render_template("error.html", message="Mohon pilih file atau masukkan link terlebih dahulu!")

            # Decide which processor to use
            if file_extension == "pdf":
                data_records = process_pdf(file_obj)
            elif file_extension in ["xlsx", "xls"]:
                data_records = process_excel(file_obj)
            else:
                return render_template("error.html", message="Tipe file tidak dapat diproses.")
            if not data_records:
                return render_template("error.html", message="Data tidak ditemukan atau file kosong.")
            return render_template("preview.html", rows=data_records)
        except Exception as e:
            print(f"System Error: {repr(e)}")
            return render_template("error.html", message=f"Terjadi kesalahan sistem: {str(e)}")

    # Fallback: render index page
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)

