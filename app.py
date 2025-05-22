from flask import Flask
from extensions import db
import os
from routes import bp  # Blueprint dari routes.py

# Inisialisasi Flask app
app = Flask(__name__)
app.secret_key = 'secret-key'

# Konfigurasi database SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'umkm.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inisialisasi database dan blueprint
db.init_app(app)
app.register_blueprint(bp)

# Import model agar dikenali oleh SQLAlchemy
import models

# Buat tabel jika belum ada
with app.app_context():
    db.create_all()

# Error handler
@app.errorhandler(404)
def page_not_found(e):
    return f"Halaman tidak ditemukan: {e}", 404

@app.errorhandler(500)
def internal_error(e):
    return f"Kesalahan server: {e}", 500

# Menjalankan aplikasi
if __name__ == '__main__':
    app.run(debug=True)
