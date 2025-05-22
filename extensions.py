from flask_sqlalchemy import SQLAlchemy

# Inisialisasi instance SQLAlchemy
db = SQLAlchemy()

def init_app(app):
    """ Fungsi untuk menginisialisasi SQLAlchemy dengan aplikasi Flask """
    db.init_app(app)
