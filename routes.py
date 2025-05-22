from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from models import UMKM
from extensions import db
from openpyxl.utils.dataframe import dataframe_to_rows
from io import BytesIO
from openpyxl import Workbook
import pandas as pd
import os
from werkzeug.utils import secure_filename

# Membuat Blueprint untuk rute-rute aplikasi
bp = Blueprint('routes', __name__)

# Kredensial admin untuk login
ADMIN_CREDENTIALS = {'username': 'admin', 'password': 'password123'}

# Define upload folder for PDFs
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'pdfs')
# Ensure the upload folder exists. This will create the directory if it doesn't exist.
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Definisi kriteria penilaian UMKM
KRITERIA = {
    "Legalitas": ["Tidak memiliki izin usaha", "Sedang dalam proses izin usaha", "Memiliki izin lengkap (NIB, NPWP, Sertifikat Halal)"],
    "Umur Usaha": ["< 1 tahun", "1-3 tahun", "> 2 tahun"],
    "Omset Tahunan": ["< 60 juta", "> 80 juta", "> 100 juta"],
    "Produk/jasa": ["Tidak unik, persaingan tinggi", "Cukup unik dan punya pasar khusus", "Inovatif dan potensial berkembang"],
    "Potensi Pertumbuhan": ["Potensi kecil, pasar terbatas", "Ada peluang pasar lokal", "Berpotensi ekspansi regional/nasional/digital"],
    "Komitmen": ["Tidak antusias atau pasif dalam program", "Cukup antusias perlu dorongan", "Sangat antusias, proaktif ingin berkembang"],
    "Dampak Sosial": ["Tidak berdampak sosial signifikan", "Sedikit berdampak (tenaga kerja lokal, komunitas kecil)", "Besar dampaknya (pemberdayaan, lingkungan, komunitas besar)"],
    "Kebutuhan Pembinaan": ["Tidak membutuhkan banyak pembinaan", "Ada beberapa kebutuhan pembinaan", "Banyak aspek membutuhkan pembinaan (produksi, manajemen dll)"],
    "Administrasi Usaha": ["Tidak ada laporan keuangan sama sekali", "Ada pencatatan sederhana (manual)", "Ada laporan sederhana dan rapi"]
}

# Skala fuzzy untuk setiap pilihan kriteria
fuzzy_scale = {
    "Legalitas": {
        "Tidak memiliki izin usaha": 0.3,
        "Sedang dalam proses izin usaha": 0.45,
        "Memiliki izin lengkap (NIB, NPWP, Sertifikat Halal)": 0.75
    },
    "Umur Usaha": {
        "< 1 tahun": 0.2,
        "1-3 tahun": 0.3,
        "> 2 tahun": 0.5
    },
    "Omset Tahunan": {
        "< 60 juta": 0.3,
        "Di atas 80 juta": 0.45, # Corrected based on common sense for Omset
        "Di atas 100 juta": 0.75 # Corrected based on common sense for Omset
    },
    "Produk/jasa": {
        "Tidak unik, persaingan tinggi": 0.2,
        "Cukup unik dan punya pasar khusus": 0.3,
        "Inovatif dan potensial berkembang": 0.5
    },
    "Potensi Pertumbuhan": {
        "Potensi kecil, pasar terbatas": 0.2,
        "Ada peluang pasar lokal": 0.3,
        "Berpotensi ekspansi regional/nasional/digital": 0.5
    },
    "Komitmen": {
        "Tidak antusias atau pasif dalam program": 0.3,
        "Cukup antusias perlu dorongan": 0.45,
        "Sangat antusias, proaktif ingin berkembang": 0.75
    },
    "Dampak Sosial": {
        "Tidak berdampak sosial signifikan": 0.2,
        "Sedikit berdampak (tenaga kerja lokal, komunitas kecil)": 0.3,
        "Besar dampaknya (pemberdayaan, lingkungan, komunitas besar)": 0.5
    },
    "Kebutuhan Pembinaan": {
        "Tidak membutuhkan banyak pembinaan": 0.2,
        "Ada beberapa kebutuhan pembinaan": 0.3,
        "Banyak aspek membutuhkan pembinaan (produksi, manajemen dll)": 0.5
    },
    "Administrasi Usaha": {
        "Tidak ada laporan keuangan sama sekali": 0.1,
        "Ada pencatatan sederhana (manual)": 0.15,
        "Ada laporan sederhana dan rapi": 0.25
    }
}


# Bobot untuk setiap kriteria
weights = {
    "Legalitas": 0.15,
    "Umur Usaha": 0.10,
    "Omset Tahunan": 0.15,
    "Produk/jasa": 0.10,
    "Potensi Pertumbuhan": 0.10,
    "Komitmen": 0.15,
    "Dampak Sosial": 0.10,
    "Kebutuhan Pembinaan": 0.10,
    "Administrasi Usaha": 0.05
}

# Rute untuk halaman utama
@bp.route('/')
def index():
    return render_template('index.html')

# Rute untuk halaman "Tentang"
@bp.route('/tentang')
def tentang():
    return render_template('tentang.html')

# Rute untuk pendaftaran UMKM baru
@bp.route('/daftar', methods=['GET', 'POST'])
def daftar():
    if request.method == 'POST':
        try:
            nama_umkm = request.form.get('nama_umkm')
            data = {}
            angka = {}
            # Mengambil data dari form dan menghitung nilai fuzzy
            for kriteria in KRITERIA:
                nilai = request.form.get(kriteria)
                data[kriteria] = nilai
                angka[kriteria] = fuzzy_scale[kriteria].get(nilai, 0)

            berkas_pdf_filename = None
            # Check if 'berkas_pdf' file was uploaded
            if 'berkas_pdf' in request.files:
                file = request.files['berkas_pdf']
                # If a file was selected and has a filename
                if file.filename != '':
                    # Check if the file is a PDF
                    if file.content_type == 'application/pdf':
                        # Secure the filename before saving to prevent directory traversal attacks
                        filename = secure_filename(file.filename)
                        file_path = os.path.join(UPLOAD_FOLDER, filename)
                        file.save(file_path)
                        berkas_pdf_filename = filename
                    else:
                        flash("Jenis file tidak didukung. Harap unggah file PDF.", "danger")
                        return redirect(url_for('routes.daftar'))
                else: # If file input is present but no file is selected, and it's required.
                    flash("Harap unggah berkas PDF yang diperlukan.", "danger")
                    return redirect(url_for('routes.daftar'))


            # Membuat objek UMKM baru
            new_umkm = UMKM(
                nama=nama_umkm,
                **{k.lower().replace('/', '_').replace(' ', '_'): data[k] for k in KRITERIA},
                **{k.lower().replace('/', '_').replace(' ', '_') + '_angka': angka[k] for k in KRITERIA},
                skor=sum([angka[k] * weights[k] for k in weights]), # Menghitung skor akhir
                berkas_pdf=berkas_pdf_filename # Menyimpan nama file PDF ke database
            )
            db.session.add(new_umkm)
            db.session.commit()
            flash("Data sudah terkirim!", "success")
            return redirect(url_for('routes.daftar'))
        except Exception as e:
            db.session.rollback()
            flash(f"Gagal menyimpan data: {e}", "danger")

    return render_template('daftar.html', kriteria=KRITERIA)

# Rute untuk menampilkan hasil penilaian UMKM
@bp.route('/result')
def result():
    umkms = UMKM.query.all()
    scores = []
    for u in umkms:
        try:
            # Menghitung skor untuk setiap UMKM
            score = sum([
                u.legalitas_angka * weights["Legalitas"],
                u.umur_usaha_angka * weights["Umur Usaha"],
                u.omset_tahunan_angka * weights["Omset Tahunan"],
                u.produk_jasa_angka * weights["Produk/jasa"],
                u.potensi_pertumbuhan_angka * weights["Potensi Pertumbuhan"],
                u.komitmen_angka * weights["Komitmen"],
                u.dampak_sosial_angka * weights["Dampak Sosial"],
                u.kebutuhan_pembinaan_angka * weights["Kebutuhan Pembinaan"],
                u.administrasi_usaha_angka * weights["Administrasi Usaha"]
            ])
            nilai = score * 100 # Mengubah skor menjadi persentase
            # Menentukan keterangan berdasarkan nilai
            keterangan = "Sangat layak dibina" if nilai >= 60 else (
                                 "Layak dibina dengan prioritas" if nilai >= 45 else (
                                 "Dipertimbangkan (butuh verifikasi tambahan)" if nilai >= 30 else
                                 "Tidak direkomendasikan"))
            scores.append({
                'id': u.id,
                'nama_umkm': u.nama,
                'score': round(score, 4),
                'nilai': round(nilai, 2),
                'keterangan': keterangan
            })
        except Exception as e:
            flash(f"Gagal memproses {u.nama}: {e}", "danger")

    scores.sort(key=lambda x: x['score'], reverse=True) # Mengurutkan UMKM berdasarkan skor
    return render_template('result.html', scores=scores, weights=weights)

# Rute untuk halaman login admin
@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_CREDENTIALS['username'] and request.form.get('password') == ADMIN_CREDENTIALS['password']:
            session['logged_in'] = True
            flash("Login berhasil!", "success")
            return redirect(url_for('routes.admin_dashboard'))
        flash("Username atau password salah", "danger")
    return render_template('admin.html')

# Rute untuk logout admin
@bp.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('routes.login'))

# Rute untuk dashboard admin
@bp.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('routes.logout'))
    umkm_data = UMKM.query.all()
    return render_template('admin.html', data=umkm_data)

# Rute untuk mengedit data UMKM
@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_umkm(id):
    umkm = UMKM.query.get_or_404(id)
    if request.method == 'POST':
        try:
            umkm.nama = request.form.get('nama_umkm')
            for kriteria in KRITERIA:
                pilihan = request.form.get(kriteria)
                setattr(umkm, kriteria.lower().replace('/', '_').replace(' ', '_'), pilihan)
                setattr(umkm, kriteria.lower().replace('/', '_').replace(' ', '_') + '_angka', fuzzy_scale[kriteria].get(pilihan, 0))
            # Menghitung ulang skor setelah perubahan
            umkm.skor = sum([
                umkm.legalitas_angka * weights["Legalitas"],
                umkm.umur_usaha_angka * weights["Umur Usaha"],
                umkm.omset_tahunan_angka * weights["Omset Tahunan"],
                umkm.produk_jasa_angka * weights["Produk/jasa"],
                umkm.potensi_pertumbuhan_angka * weights["Potensi Pertumbuhan"],
                umkm.komitmen_angka * weights["Komitmen"],
                umkm.dampak_sosial_angka * weights["Dampak Sosial"],
                umkm.kebutuhan_pembinaan_angka * weights["Kebutuhan Pembinaan"],
                umkm.administrasi_usaha_angka * weights["Administrasi Usaha"]
            ])
            db.session.commit()
            flash("Data berhasil diperbarui!", "success")
            return redirect(url_for('routes.admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"Update gagal: {e}", "danger")
    return render_template('edit_umkm.html', umkm=umkm, kriteria=KRITERIA)

# Rute untuk menghapus data UMKM
@bp.route('/delete/<int:id>')
def delete_umkm(id):
    umkm = UMKM.query.get_or_404(id)
    # Optionally, delete the associated PDF file when UMKM is deleted
    if umkm.berkas_pdf:
        file_path = os.path.join(UPLOAD_FOLDER, umkm.berkas_pdf)
        if os.path.exists(file_path):
            os.remove(file_path)
            flash(f"Berkas PDF '{umkm.berkas_pdf}' juga telah dihapus.", "info")
    
    db.session.delete(umkm)
    db.session.commit()
    flash("Data UMKM berhasil dihapus", "success")
    return redirect(url_for('routes.admin_dashboard'))

# Rute untuk mengunduh data UMKM dalam format Excel (dari admin dashboard)
@bp.route('/download_excel')
def download_excel():
    umkms = UMKM.query.all()
    # Membuat DataFrame dari data UMKM
    df = pd.DataFrame([{
        'Nama UMKM': u.nama,
        **{k: getattr(u, k.lower().replace('/', '_').replace(' ', '_')) for k in KRITERIA},
        **{f"{k} (angka)": getattr(u, k.lower().replace('/', '_').replace(' ', '_') + '_angka') for k in KRITERIA},
        'Skor': u.skor,
        'Berkas PDF': u.berkas_pdf # Include PDF filename in Excel
    } for u in umkms])

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Data UMKM')
    output.seek(0)

    return send_file(output, download_name="data_umkm.xlsx", as_attachment=True)

# New route to download processed results as Excel (from result page)
@bp.route('/download_result_excel')
def download_result_excel():
    umkms = UMKM.query.all()
    scores_data = []
    for u in umkms:
        try:
            score = sum([
                u.legalitas_angka * weights["Legalitas"],
                u.umur_usaha_angka * weights["Umur Usaha"],
                u.omset_tahunan_angka * weights["Omset Tahunan"],
                u.produk_jasa_angka * weights["Produk/jasa"],
                u.potensi_pertumbuhan_angka * weights["Potensi Pertumbuhan"],
                u.komitmen_angka * weights["Komitmen"],
                u.dampak_sosial_angka * weights["Dampak Sosial"],
                u.kebutuhan_pembinaan_angka * weights["Kebutuhan Pembinaan"],
                u.administrasi_usaha_angka * weights["Administrasi Usaha"]
            ])
            nilai = score * 100
            keterangan = "Sangat layak dibina" if nilai >= 60 else (
                                 "Layak dibina dengan prioritas" if nilai >= 45 else (
                                 "Dipertimbangkan (butuh verifikasi tambahan)" if nilai >= 30 else
                                 "Tidak direkomendasikan"))
            scores_data.append({
                'Nama UMKM': u.nama,
                'Skor (0-1)': round(score, 4),
                'Nilai (%)': round(nilai, 2),
                'Keterangan': keterangan
            })
        except Exception as e:
            # Handle error for specific UMKM if needed, or log it
            print(f"Error processing UMKM {u.nama}: {e}")
            continue # Skip to the next UMKM

    # Sort data by score in descending order
    scores_data.sort(key=lambda x: x['Skor (0-1)'], reverse=True)

    df_results = pd.DataFrame(scores_data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_results.to_excel(writer, index=False, sheet_name='Hasil Seleksi UMKM')
    output.seek(0)

    return send_file(output, download_name="hasil_seleksi_umkm_final.xlsx", as_attachment=True)


# New route to download PDF file
@bp.route('/download_pdf/<filename>')
def download_pdf(filename):
    # Ensure the filename is secure to prevent directory traversal
    safe_filename = secure_filename(filename)
    file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash("Berkas tidak ditemukan.", "danger")
        return redirect(url_for('routes.admin_dashboard')) # Redirect to admin dashboard if file not found
