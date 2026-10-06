import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Render'daki kalıcı bulut veritabanı bağlantısı
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///ogretmen.db')

def get_db():
    if DATABASE_URL.startswith("postgres"):
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    else:
        import sqlite3
        conn = sqlite3.connect('ogretmen.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # SQLite / PostgreSQL uyumlu tablo oluşturma
    if DATABASE_URL.startswith("postgres"):
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ogrenciler (
                id SERIAL PRIMARY KEY,
                ad_soyad TEXT NOT NULL,
                sinif TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sinavlar (
                id SERIAL PRIMARY KEY,
                ogrenci_id INTEGER REFERENCES ogrenciler(id) ON DELETE CASCADE,
                sinav_turu TEXT NOT NULL,
                ay TEXT NOT NULL,
                net REAL NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raporlar (
                id SERIAL PRIMARY KEY,
                ogrenci_id INTEGER REFERENCES ogrenciler(id) ON DELETE CASCADE,
                notlar TEXT,
                ses_dosyasi TEXT,
                tarih TEXT
            )
        ''')
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ogrenciler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_soyad TEXT NOT NULL,
                sinif TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sinavlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ogrenci_id INTEGER,
                sinav_turu TEXT NOT NULL,
                ay TEXT NOT NULL,
                net REAL NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raporlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ogrenci_id INTEGER,
                notlar TEXT,
                ses_dosyasi TEXT,
                tarih TEXT
            )
        ''')
    
    conn.commit()
    cursor.close()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/ogrenciler', methods=['GET', 'POST'])
def handle_ogrenciler():
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.json
        cursor.execute('INSERT INTO ogrenciler (ad_soyad, sinif) VALUES (%s, %s)' if DATABASE_URL.startswith("postgres") else 'INSERT INTO ogrenciler (ad_soyad, sinif) VALUES (?, ?)',
                       (data['ad_soyad'], data['sinif']))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'message': 'Öğrenci eklendi'}), 201
    else:
        cursor.execute('SELECT * FROM ogrenciler ORDER BY ad_soyad')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([dict(r) for r in rows])

@app.route('/api/sinav_ekle', methods=['POST'])
def sinav_ekle():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO sinavlar (ogrenci_id, sinav_turu, ay, net) VALUES (%s, %s, %s, %s)' if DATABASE_URL.startswith("postgres") else 'INSERT INTO sinavlar (ogrenci_id, sinav_turu, ay, net) VALUES (?, ?, ?, ?)',
                   (data['ogrenci_id'], data['sinav_turu'], data['ay'], data['net']))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Sınav eklendi'})

@app.route('/api/sinavlar', methods=['GET'])
def sinavlar():
    ogrenci_id = request.args.get('ogrenci_id')
    conn = get_db()
    cursor = conn.cursor()
    
    query = '''
        SELECT s.id, o.ad_soyad, s.sinav_turu, s.ay, s.net 
        FROM sinavlar s 
        JOIN ogrenciler o ON s.ogrenci_id = o.id
    '''
    if ogrenci_id:
        query += ' WHERE s.ogrenci_id = %s ORDER BY s.id DESC' if DATABASE_URL.startswith("postgres") else ' WHERE s.ogrenci_id = ? ORDER BY s.id DESC'
        cursor.execute(query, (ogrenci_id,))
    else:
        query += ' ORDER BY s.id DESC'
        cursor.execute(query)
        
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/sinav_sil/<int:id>', methods=['DELETE'])
def sinav_sil(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sinavlar WHERE id = %s' if DATABASE_URL.startswith("postgres") else 'DELETE FROM sinavlar WHERE id = ?', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Sınav silindi'})

@app.route('/api/siralama', methods=['GET'])
def siralama():
    sinav_turu = request.args.get('sinav_turu', 'TYT')
    conn = get_db()
    cursor = conn.cursor()
    query = '''
        SELECT o.ad_soyad, o.sinif, 
               ROUND(AVG(s.net)::numeric, 2) as ortalama, 
               COUNT(s.id) as sinav_sayisi
        FROM ogrenciler o
        JOIN sinavlar s ON o.id = s.ogrenci_id
        WHERE s.sinav_turu = %s
        GROUP BY o.id, o.ad_soyad, o.sinif
        ORDER BY ortalama DESC
    ''' if DATABASE_URL.startswith("postgres") else '''
        SELECT o.ad_soyad, o.sinif, 
               ROUND(AVG(s.net), 2) as ortalama, 
               COUNT(s.id) as sinav_sayisi
        FROM ogrenciler o
        JOIN sinavlar s ON o.id = s.ogrenci_id
        WHERE s.sinav_turu = ?
        GROUP BY o.id, o.ad_soyad, o.sinif
        ORDER BY ortalama DESC
    '''
    cursor.execute(query, (sinav_turu,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/rapor_ekle', methods=['POST'])
def rapor_ekle():
    ogrenci_id = request.form.get('ogrenci_id')
    notlar = request.form.get('notlar', '')
    ses_dosyasi = request.files.get('ses_dosyasi')
    
    filename = None
    if ses_dosyasi:
        filename = f"{int(datetime.now().timestamp())}_{ses_dosyasi.filename}"
        ses_dosyasi.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
    tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO raporlar (ogrenci_id, notlar, ses_dosyasi, tarih) VALUES (%s, %s, %s, %s)' if DATABASE_URL.startswith("postgres") else 'INSERT INTO raporlar (ogrenci_id, notlar, ses_dosyasi, tarih) VALUES (?, ?, ?, ?)',
                   (ogrenci_id, notlar, filename, tarih))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Rapor kaydedildi'})

@app.route('/api/raporlar', methods=['GET'])
def raporlar():
    ogrenci_id = request.args.get('ogrenci_id')
    conn = get_db()
    cursor = conn.cursor()
    query = '''
        SELECT r.id, o.ad_soyad, o.sinif, r.notlar, r.ses_dosyasi, r.tarih 
        FROM raporlar r 
        JOIN ogrenciler o ON r.ogrenci_id = o.id
    '''
    if ogrenci_id:
        query += ' WHERE r.ogrenci_id = %s ORDER BY r.id DESC' if DATABASE_URL.startswith("postgres") else ' WHERE r.ogrenci_id = ? ORDER BY r.id DESC'
        cursor.execute(query, (ogrenci_id,))
    else:
        query += ' ORDER BY r.id DESC'
        cursor.execute(query)
        
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/not_sil/<int:id>', methods=['DELETE'])
def not_sil(id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM raporlar WHERE id = %s' if DATABASE_URL.startswith("postgres") else 'DELETE FROM raporlar WHERE id = ?', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({'message': 'Not silindi'})
import webview
import threading
import multiprocessing

def start_desktop():
    # Arka planda Flask sunucusunu başlat
    t = threading.Thread(
        target=lambda: app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False),
        daemon=True
    )
    t.start()
    
    # Masaüstü penceresini aç
    webview.create_window('Öğrenci Takip Sistemi', 'http://127.0.0.1:5000')
    webview.start()

if __name__ == '__main__':
    # PyInstaller sonsuz süreç hatasını önler
    multiprocessing.freeze_support()
    start_desktop()
