from extensions import db

class UMKM(db.Model):
    __tablename__ = 'umkm'

    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)

    # Data kualitatif dan kuantitatif untuk setiap kriteria
    legalitas = db.Column(db.String(100))
    legalitas_angka = db.Column(db.Float)

    umur_usaha = db.Column(db.String(100))
    umur_usaha_angka = db.Column(db.Float)

    omset_tahunan = db.Column(db.String(100))
    omset_tahunan_angka = db.Column(db.Float)

    produk_jasa = db.Column(db.String(100))
    produk_jasa_angka = db.Column(db.Float)

    potensi_pertumbuhan = db.Column(db.String(100))
    potensi_pertumbuhan_angka = db.Column(db.Float)

    komitmen = db.Column(db.String(100))
    komitmen_angka = db.Column(db.Float)

    dampak_sosial = db.Column(db.String(100))
    dampak_sosial_angka = db.Column(db.Float)

    kebutuhan_pembinaan = db.Column(db.String(100))
    kebutuhan_pembinaan_angka = db.Column(db.Float)

    administrasi_usaha = db.Column(db.String(100))
    administrasi_usaha_angka = db.Column(db.Float)

    skor = db.Column(db.Float)

    # Kolom untuk menyimpan berkas PDF
    berkas_pdf = db.Column(db.String(255))