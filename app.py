import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory, render_template_string

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DB_NAME = 'ogretmen.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ogrenciler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ad_soyad TEXT NOT NULL,
                sinif TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raporlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ogrenci_id INTEGER,
                tarih TEXT,
                notlar TEXT,
                ses_dosyasi TEXT,
                FOREIGN KEY(ogrenci_id) REFERENCES ogrenciler(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sinavlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ogrenci_id INTEGER,
                sinav_turu TEXT,
                ay TEXT,
                net REAL,
                FOREIGN KEY(ogrenci_id) REFERENCES ogrenciler(id)
            )
        ''')
        conn.commit()

init_db()

@app.route('/')
def index():
    # templates/index.html yoksa sunucunun çökmesini engeller
    if os.path.exists(os.path.join(app.template_folder, 'index.html')):
        return render_template('index.html')
    return render_template_string("<h2>Sistem Çalışıyor!</h2><p>Lütfen GitHub reponuza <b>templates/index.html</b> dosyasını ekleyin.</p>")

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/ogrenciler', methods=['GET', 'POST'])
def api_ogrenciler():
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            if request.method == 'POST':
                data = request.json or {}
                ad_soyad = data.get('ad_soyad', '').strip()
                sinif = data.get('sinif', '').strip()
                
                if not ad_soyad:
                    return jsonify({"error": "Ad soyad boş olamaz"}), 400
                    
                cursor.execute("INSERT INTO ogrenciler (ad_soyad, sinif) VALUES (?, ?)", (ad_soyad, sinif))
                conn.commit()
                return jsonify({"status": "ok"})
            else:
                cursor.execute("SELECT * FROM ogrenciler")
                rows = cursor.fetchall()
                return jsonify([{"id": r['id'], "ad_soyad": r['ad_soyad'], "sinif": r['sinif']} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/rapor_ekle', methods=['POST'])
def api_rapor_ekle():
    try:
        ogrenci_id = request.form.get('ogrenci_id')
        notlar = request.form.get('notlar', '')
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        if not ogrenci_id:
            return jsonify({"error": "Öğrenci seçilmedi"}), 400

        ses_dosyasi_adi = None
        if 'ses_dosyasi' in request.files:
            file = request.files['ses_dosyasi']
            if file and file.filename != '':
                safe_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ses_dosyasi_adi = f"{safe_timestamp}_{file.filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], ses_dosyasi_adi))

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO raporlar (ogrenci_id, tarih, notlar, ses_dosyasi) VALUES (?, ?, ?, ?)",
                           (ogrenci_id, tarih, notlar, ses_dosyasi_adi))
            conn.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/raporlar', methods=['GET'])
def api_raporlar():
    try:
        ogrenci_id = request.args.get('ogrenci_id')
        with get_db() as conn:
            cursor = conn.cursor()
            if ogrenci_id:
                cursor.execute("""
                    SELECT raporlar.id, ogrenciler.ad_soyad, ogrenciler.sinif, raporlar.tarih, raporlar.notlar, raporlar.ses_dosyasi 
                    FROM raporlar JOIN ogrenciler ON raporlar.ogrenci_id = ogrenciler.id 
                    WHERE ogrenci_id = ? ORDER BY raporlar.id DESC
                """, (ogrenci_id,))
            else:
                cursor.execute("""
                    SELECT raporlar.id, ogrenciler.ad_soyad, ogrenciler.sinif, raporlar.tarih, raporlar.notlar, raporlar.ses_dosyasi 
                    FROM raporlar JOIN ogrenciler ON raporlar.ogrenci_id = ogrenciler.id 
                    ORDER BY raporlar.id DESC
                """)
            rows = cursor.fetchall()
            return jsonify([{"id": r[0], "ad_soyad": r[1], "sinif": r[2], "tarih": r[3], "notlar": r[4], "ses_dosyasi": r[5]} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/not_sil/<int:id>', methods=['DELETE'])
def api_not_sil(id):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM raporlar WHERE id = ?", (id,))
            conn.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sinav_ekle', methods=['POST'])
def api_sinav_ekle():
    try:
        data = request.json or {}
        ogrenci_id = data.get('ogrenci_id')
        sinav_turu = data.get('sinav_turu')
        ay = data.get('ay')
        net = data.get('net')

        if not all([ogrenci_id, sinav_turu, ay, net is not None]):
            return jsonify({"error": "Eksik bilgi girdiniz"}), 400

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO sinavlar (ogrenci_id, sinav_turu, ay, net) VALUES (?, ?, ?, ?)",
                           (ogrenci_id, sinav_turu, ay, float(net)))
            conn.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sinavlar', methods=['GET'])
def api_sinavlar():
    try:
        ogrenci_id = request.args.get('ogrenci_id')
        with get_db() as conn:
            cursor = conn.cursor()
            if ogrenci_id:
                cursor.execute("""
                    SELECT sinavlar.id, ogrenciler.ad_soyad, sinavlar.sinav_turu, sinavlar.ay, sinavlar.net 
                    FROM sinavlar JOIN ogrenciler ON sinavlar.ogrenci_id = ogrenciler.id 
                    WHERE ogrenci_id = ? ORDER BY sinavlar.id DESC
                """, (ogrenci_id,))
            else:
                cursor.execute("""
                    SELECT sinavlar.id, ogrenciler.ad_soyad, sinavlar.sinav_turu, sinavlar.ay, sinavlar.net 
                    FROM sinavlar JOIN ogrenciler ON sinavlar.ogrenci_id = ogrenciler.id 
                    ORDER BY sinavlar.id DESC
                """)
            rows = cursor.fetchall()
            return jsonify([{"id": r[0], "ad_soyad": r[1], "sinav_turu": r[2], "ay": r[3], "net": r[4]} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sinav_sil/<int:id>', methods=['DELETE'])
def api_sinav_sil(id):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sinavlar WHERE id = ?", (id,))
            conn.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/siralama', methods=['GET'])
def api_siralama():
    try:
        sinav_turu = request.args.get('sinav_turu', 'TYT')
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ogrenciler.ad_soyad, ogrenciler.sinif, AVG(sinavlar.net) as ortalama_net, COUNT(sinavlar.id) as sinav_sayisi
                FROM sinavlar 
                JOIN ogrenciler ON sinavlar.ogrenci_id = ogrenciler.id
                WHERE sinavlar.sinav_turu = ?
                GROUP BY ogrenciler.id
                ORDER BY ortalama_net DESC
            """, (sinav_turu,))
            rows = cursor.fetchall()
            return jsonify([{"ad_soyad": r[0], "sinif": r[1], "ortalama": round(r[2], 2) if r[2] else 0, "sinav_sayisi": r[3]} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
