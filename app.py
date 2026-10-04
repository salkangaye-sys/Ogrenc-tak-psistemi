import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_from_directory

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --------------------------------------------------
# 1. VERİTABANI KURULUMU
# --------------------------------------------------
def init_db():
    conn = sqlite3.connect('ogretmen.db')
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
        CREATE TABLE IF NOT EXISTS muziker (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baslik TEXT NOT NULL,
            dosya_yolu TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --------------------------------------------------
# 2. ANA SAYFA ROTASI (RENDER/FLASK İÇİN)
# --------------------------------------------------
@app.route('/')
def index():
    return render_template_string(HTML_LAYOUT)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --------------------------------------------------
# 3. API ROTALARI
# --------------------------------------------------
@app.route('/api/ogrenciler', methods=['GET', 'POST'])
def api_ogrenciler():
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.json
        cursor.execute("INSERT INTO ogrenciler (ad_soyad, sinif) VALUES (?, ?)", 
                       (data['ad_soyad'], data['sinif']))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    else:
        cursor.execute("SELECT * FROM ogrenciler")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{"id": r[0], "ad_soyad": r[1], "sinif": r[2]} for r in rows])

@app.route('/api/ogrenci_sil/<int:id>', methods=['DELETE'])
def api_ogrenci_sil(id):
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM raporlar WHERE ogrenci_id = ?", (id,))
    cursor.execute("DELETE FROM ogrenciler WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/rapor_ekle', methods=['POST'])
def api_rapor_ekle():
    ogrenci_id = request.form.get('ogrenci_id')
    notlar = request.form.get('notlar')
    tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    ses_dosyasi_adi = None
    if 'ses_dosyasi' in request.files:
        file = request.files['ses_dosyasi']
        if file.filename != '':
            ses_dosyasi_adi = f"{datetime.now().timestamp()}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], ses_dosyasi_adi))

    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO raporlar (ogrenci_id, tarih, notlar, ses_dosyasi) VALUES (?, ?, ?, ?)",
                   (ogrenci_id, tarih, notlar, ses_dosyasi_adi))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/raporlar', methods=['GET'])
def api_raporlar():
    ogrenci_id = request.args.get('ogrenci_id')
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    if ogrenci_id:
        cursor.execute("""
            SELECT raporlar.id, ogrenciler.ad_soyad, ogrenciler.sinif, raporlar.tarih, raporlar.notlar, raporlar.ses_dosyasi 
            FROM raporlar 
            JOIN ogrenciler ON raporlar.ogrenci_id = ogrenciler.id 
            WHERE ogrenci_id = ? ORDER BY raporlar.id DESC
        """, (ogrenci_id,))
    else:
        cursor.execute("""
            SELECT raporlar.id, ogrenciler.ad_soyad, ogrenciler.sinif, raporlar.tarih, raporlar.notlar, raporlar.ses_dosyasi 
            FROM raporlar 
            JOIN ogrenciler ON raporlar.ogrenci_id = ogrenciler.id 
            ORDER BY raporlar.id DESC
        """)
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "ad_soyad": r[1], "sinif": r[2], "tarih": r[3], "notlar": r[4], "ses_dosyasi": r[5]} for r in rows])

@app.route('/api/not_sil/<int:id>', methods=['DELETE'])
def api_not_sil(id):
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM raporlar WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/muzik_ekle', methods=['POST'])
def api_muzik_ekle():
    baslik = request.form.get('baslik')
    file = request.files.get('muzik')
    if file:
        dosya_adi = f"muzik_{datetime.now().timestamp()}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], dosya_adi))
        conn = sqlite3.connect('ogretmen.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO muziker (baslik, dosya_yolu) VALUES (?, ?)", (baslik, dosya_adi))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

@app.route('/api/muzikler', methods=['GET'])
def api_muzikler():
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM muziker ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "baslik": r[1], "dosya_yolu": r[2]} for r in rows])

# --------------------------------------------------
# 4. HTML/CSS/JS ARAYÜZ ŞABLONU
# --------------------------------------------------
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Öğrenci Takip Sistemi</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        h1, h2 { color: #2c3e50; margin-bottom: 20px; }
        .section { margin-bottom: 30px; padding: 20px; border-radius: 8px; background: #fafafa; border: 1px solid #eee; }
        input[type="text"], select, textarea, input[type="file"] { width: 100%; padding: 10px; margin-top: 8px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
        button { background-color: #3498db; color: white; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: background 0.2s; }
        button:hover { background-color: #2980b9; }
        .delete-btn { background-color: #e74c3c; padding: 5px 10px; font-size: 12px; float: right; }
        .delete-btn:hover { background-color: #c0392b; }
        .card { background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 12px; position: relative; }
        .card-header { font-weight: bold; font-size: 16px; color: #2c3e50; }
        .card-date { font-size: 12px; color: #888; margin-top: 4px; }
        audio { width: 100%; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎓 Öğrenci Takip & Not Sistemi</h1>

        <!-- Öğrenci Ekleme -->
        <div class="section">
            <h2>Yeni Öğrenci Ekle</h2>
            <input type="text" id="ogrenciAd" placeholder="Öğrenci Adı Soyadı">
            <input type="text" id="ogrenciSinif" placeholder="Sınıfı (Örn: 9-A)">
            <button onclick="ogrenciEkle()">Öğrenci Kaydet</button>
        </div>

        <!-- Rapor / Not Ekleme -->
        <div class="section">
            <h2>Öğrenciye Not / Sesli Rapor Ekle</h2>
            <select id="ogrenciSec"><option value="">Öğrenci Seçin...</option></select>
            <textarea id="notMetni" rows="3" placeholder="Öğrenci ile ilgili gözlem ve notlarınız..."></textarea>
            <label>Ses Kaydı / Dosyası Ekleyin (Opsiyonel):</label>
            <input type="file" id="sesDosyasi" accept="audio/*">
            <button onclick="raporEkle()">Raporu Kaydet</button>
        </div>

        <!-- Müzik Ekleme -->
        <div class="section">
            <h2>Müzik / Ses Dosyası Yükle</h2>
            <input type="text" id="muzikBaslik" placeholder="Müzik Başlığı">
            <input type="file" id="muzikDosyasi" accept="audio/*">
            <button onclick="muzikYukle()">Müzik Yükle</button>
        </div>

        <!-- Geçmiş Notlar -->
        <div class="section">
            <h2>Gözlem ve Not Geçmişi</h2>
            <select id="filtreOgrenci" onchange="notlariGetir()">
                <option value="">Tüm Öğrencileri Göster</option>
            </select>
            <div id="gecmisNotlarListesi" style="margin-top: 15px;"></div>
        </div>
    </div>

    <script>
        document.addEventListener("DOMContentLoaded", () => {
            ogrencileriGetir();
            notlariGetir();
        });

        function ogrencileriGetir() {
            fetch('/api/ogrenciler')
                .then(r => r.json())
                .then(data => {
                    const sec = document.getElementById('ogrenciSec');
                    const filtre = document.getElementById('filtreOgrenci');
                    sec.innerHTML = '<option value="">Öğrenci Seçin...</option>';
                    filtre.innerHTML = '<option value="">Tüm Öğrencileri Göster</option>';
                    
                    data.forEach(o => {
                        const opt = `<option value="${o.id}">${o.ad_soyad} (${o.sinif})</option>`;
                        sec.innerHTML += opt;
                        filtre.innerHTML += opt;
                    });
                });
        }

        function ogrenciEkle() {
            const ad = document.getElementById('ogrenciAd').value;
            const sinif = document.getElementById('ogrenciSinif').value;
            if (!ad) return alert('Lütfen öğrenci adını girin!');

            fetch('/api/ogrenciler', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ad_soyad: ad, sinif: sinif})
            }).then(() => {
                document.getElementById('ogrenciAd').value = '';
                document.getElementById('ogrenciSinif').value = '';
                ogrencileriGetir();
                alert('Öğrenci eklendi!');
            });
        }

        function raporEkle() {
            const ogrenciId = document.getElementById('ogrenciSec').value;
            const notlar = document.getElementById('notMetni').value;
            const ses = document.getElementById('sesDosyasi').files[0];

            if (!ogrenciId) return alert('Lütfen bir öğrenci seçin!');

            const formData = new FormData();
            formData.append('ogrenci_id', ogrenciId);
            formData.append('notlar', notlar);
            if (ses) formData.append('ses_dosyasi', ses);

            fetch('/api/rapor_ekle', {
                method: 'POST',
                body: formData
            }).then(() => {
                document.getElementById('notMetni').value = '';
                document.getElementById('sesDosyasi').value = '';
                notlariGetir();
                alert('Not kaydedildi!');
            });
        }

        function notlariGetir() {
            const ogrenciId = document.getElementById('filtreOgrenci').value;
            let url = '/api/raporlar';
            if (ogrenciId) url += '?ogrenci_id=' + ogrenciId;

            fetch(url)
                .then(r => r.json())
                .then(data => {
                    let html = '';
                    if (!data || data.length === 0) {
                        html = '<p style="padding:10px; color:#666;">Henüz kaydedilmiş bir not bulunamadı.</p>';
                    } else {
                        data.forEach(item => {
                            html += `<div class="card">
                                <button class="delete-btn" onclick="notSil(${item.id})">Bu Notu Sil</button>
                                <div class="card-header">👤 ${item.ad_soyad} (${item.sinif})</div>
                                <div class="card-date">📅 ${item.tarih}</div>
                                <div style="margin-top:8px;">${item.notlar ? item.notlar : '<i>Metin notu girilmedi.</i>'}</div>`;
                            if (item.ses_dosyasi) {
                                html += `<audio controls src="/uploads/${item.ses_dosyasi}"></audio>`;
                            }
                            html += `</div>`;
                        });
                    }
                    document.getElementById('gecmisNotlarListesi').innerHTML = html;
                });
        }

        function notSil(id) {
            if (!confirm('Bu notu silmek istediğinize emin misiniz?')) return;
            fetch('/api/not_sil/' + id, { method: 'DELETE' })
                .then(() => notlariGetir());
        }

        function muzikYukle() {
            let baslik = document.getElementById('muzikBaslik').value;
            let muzikFile = document.getElementById('muzikDosyasi').files[0];

            if (!baslik || !muzikFile) return alert('Lütfen müzik başlığı ve dosyasını seçin!');

            let formData = new FormData();
            formData.append('baslik', baslik);
            formData.append('muzik', muzikFile);

            fetch('/api/muzik_ekle', {
                method: 'POST',
                body: formData
            }).then(() => {
                document.getElementById('muzikBaslik').value = '';
                document.getElementById('muzikDosyasi').value = '';
                alert('Müzik başarıyla yüklendi!');
                location.reload();
            });
        }
    </script>
</body>
</html>
"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
