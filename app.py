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
    conn.close()

init_db()

# --------------------------------------------------
# 2. ANA SAYFA VE STATİK DOSYALAR
# --------------------------------------------------
@app.route('/')
def index():
    return render_template_string(HTML_LAYOUT)

@app.route('/uploads/<path:filename>')
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
        data = request.json or {}
        cursor.execute("INSERT INTO ogrenciler (ad_soyad, sinif) VALUES (?, ?)", 
                       (data.get('ad_soyad', ''), data.get('sinif', '')))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    else:
        cursor.execute("SELECT * FROM ogrenciler")
        rows = cursor.fetchall()
        conn.close()
        return jsonify([{"id": r[0], "ad_soyad": r[1], "sinif": r[2]} for r in rows])

@app.route('/api/rapor_ekle', methods=['POST'])
def api_rapor_ekle():
    ogrenci_id = request.form.get('ogrenci_id')
    notlar = request.form.get('notlar')
    tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    ses_dosyasi_adi = None
    if 'ses_dosyasi' in request.files:
        file = request.files['ses_dosyasi']
        if file and file.filename != '':
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

@app.route('/api/sinav_ekle', methods=['POST'])
def api_sinav_ekle():
    data = request.json or {}
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO sinavlar (ogrenci_id, sinav_turu, ay, net) VALUES (?, ?, ?, ?)",
                   (data.get('ogrenci_id'), data.get('sinav_turu'), data.get('ay'), data.get('net')))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/sinavlar', methods=['GET'])
def api_sinavlar():
    ogrenci_id = request.args.get('ogrenci_id')
    conn = sqlite3.connect('ogretmen.db')
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
    conn.close()
    return jsonify([{"id": r[0], "ad_soyad": r[1], "sinav_turu": r[2], "ay": r[3], "net": r[4]} for r in rows])

@app.route('/api/sinav_sil/<int:id>', methods=['DELETE'])
def api_sinav_sil(id):
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sinavlar WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/siralama', methods=['GET'])
def api_siralama():
    sinav_turu = request.args.get('sinav_turu', 'TYT')
    conn = sqlite3.connect('ogretmen.db')
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
    conn.close()
    return jsonify([{"ad_soyad": r[0], "sinif": r[1], "ortalama": round(r[2], 2), "sinav_sayisi": r[3]} for r in rows])

# --------------------------------------------------
# 4. ARAYÜZ (HTML / CSS / JS)
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
        h1 { color: #2c3e50; text-align: center; margin-bottom: 25px; }
        
        .block-header {
            background-color: #34495e;
            color: white;
            padding: 15px 20px;
            font-size: 16px;
            font-weight: bold;
            border-radius: 8px;
            cursor: pointer;
            margin-top: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.3s;
        }
        .block-header:hover { background-color: #2c3e50; }
        .block-content {
            background: #fafafa;
            border: 1px solid #ddd;
            border-top: none;
            padding: 20px;
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
            display: none;
        }

        input, select, textarea { width: 100%; padding: 10px; margin-top: 8px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; }
        button { background-color: #3498db; color: white; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-size: 14px; }
        button:hover { background-color: #2980b9; }
        .delete-btn { background-color: #e74c3c; padding: 5px 10px; font-size: 12px; float: right; }
        .card { background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 12px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #2c3e50; color: white; }
        tr:nth-child(even) { background-color: #f9f9f9; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎓 Öğrenci Takip & Derece Sistemi</h1>

        <!-- BLOK 1: Öğrenci Kayıt -->
        <div class="block-header" onclick="toggleBlock('block1')">
            <span>👤 1. Öğrenci Kayıt Alanı</span>
            <span id="icon-block1">➕</span>
        </div>
        <div id="block1" class="block-content">
            <input type="text" id="ogrenciAd" placeholder="Öğrenci Adı Soyadı">
            <input type="text" id="ogrenciSinif" placeholder="Sınıfı (Örn: 12-A)">
            <button onclick="ogrenciEkle()">Öğrenci Kaydet</button>
        </div>

        <!-- BLOK 2: TYT / AYT Net Takip & Kayıt -->
        <div class="block-header" onclick="toggleBlock('block2')">
            <span>📊 2. TYT / AYT Net Kayıt ve Takibi</span>
            <span id="icon-block2">➕</span>
        </div>
        <div id="block2" class="block-content">
            <h3>Sınav Neti Ekle</h3>
            <select id="sinavOgrenciSec"></select>
            <select id="sinavTuru">
                <option value="TYT">TYT</option>
                <option value="AYT">AYT</option>
            </select>
            <select id="sinavAy">
                <option value="Eylül">Eylül</option>
                <option value="Ekim">Ekim</option>
                <option value="Kasım">Kasım</option>
                <option value="Aralık">Aralık</option>
                <option value="Ocak">Ocak</option>
                <option value="Şubat">Şubat</option>
                <option value="Mart">Mart</option>
                <option value="Nisan">Nisan</option>
                <option value="Mayıs">Mayıs</option>
                <option value="Haziran">Haziran</option>
            </select>
            <input type="number" step="0.25" id="sinavNet" placeholder="Toplam Net (Örn: 78.5)">
            <button onclick="sinavEkle()">Net Kaydet</button>

            <hr style="margin: 20px 0;">
            <h3>Geçmiş Sınav Netleri</h3>
            <select id="filtreSinavOgrenci" onchange="sinavlariGetir()">
                <option value="">Tüm Öğrencileri Göster</option>
            </select>
            <div id="sinavListesi"></div>
        </div>

        <!-- BLOK 3: Sınıf Sıralaması & Ortalama Dereceleri -->
        <div class="block-header" onclick="toggleBlock('block3')">
            <span>🏆 3. Sınıf Sıralaması & Net Ortalamaları</span>
            <span id="icon-block3">➕</span>
        </div>
        <div id="block3" class="block-content">
            <label>Sıralamak İstediğiniz Sınav Türünü Seçin:</label>
            <select id="siralamaTuru" onchange="siralamaGetir()">
                <option value="TYT">TYT Genel Sıralaması</option>
                <option value="AYT">AYT Genel Sıralaması</option>
            </select>
            <table>
                <thead>
                    <tr>
                        <th>Derece</th>
                        <th>Öğrenci Adı</th>
                        <th>Sınıf</th>
                        <th>Ortalama Net</th>
                        <th>Girdiği Sınav Sayısı</th>
                    </tr>
                </thead>
                <tbody id="siralamaTablosu"></tbody>
            </table>
        </div>

        <!-- BLOK 4: Gözlem / Sesli Rapor Ekleme -->
        <div class="block-header" onclick="toggleBlock('block4')">
            <span>📝 4. Gözlem ve Not Geçmişi</span>
            <span id="icon-block4">➕</span>
        </div>
        <div id="block4" class="block-content">
            <select id="ogrenciSec"><option value="">Öğrenci Seçin...</option></select>
            <textarea id="notMetni" rows="3" placeholder="Öğrenci ile ilgili gözlem notları..."></textarea>
            <label>Ses Kaydı / Dosyası Ekleyin:</label>
            <input type="file" id="sesDosyasi" accept="audio/*">
            <button onclick="raporEkle()">Notu Kaydet</button>

            <hr style="margin: 20px 0;">
            <select id="filtreOgrenci" onchange="notlariGetir()">
                <option value="">Tüm Öğrencilerin Notlarını Göster</option>
            </select>
            <div id="gecmisNotlarListesi"></div>
        </div>
    </div>

    <script>
        document.addEventListener("DOMContentLoaded", () => {
            ogrencileriGetir();
            notlariGetir();
            sinavlariGetir();
            siralamaGetir();
        });

        function toggleBlock(id) {
            const el = document.getElementById(id);
            const icon = document.getElementById('icon-' + id);
            if (el.style.display === "block") {
                el.style.display = "none";
                icon.innerText = "➕";
            } else {
                el.style.display = "block";
                icon.innerText = "➖";
            }
        }

        function ogrencileriGetir() {
            fetch('/api/ogrenciler')
                .then(r => r.json())
                .then(data => {
                    const list = ['ogrenciSec', 'filtreOgrenci', 'sinavOgrenciSec', 'filtreSinavOgrenci'];
                    list.forEach(id => {
                        const el = document.getElementById(id);
                        if (!el) return;
                        el.innerHTML = '<option value="">Öğrenci Seçin...</option>';
                        data.forEach(o => {
                            el.innerHTML += `<option value="${o.id}">${o.ad_soyad} (${o.sinif})</option>`;
                        });
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

        function sinavEkle() {
            const ogrenci_id = document.getElementById('sinavOgrenciSec').value;
            const sinav_turu = document.getElementById('sinavTuru').value;
            const ay = document.getElementById('sinavAy').value;
            const net = document.getElementById('sinavNet').value;

            if (!ogrenci_id || !net) return alert('Lütfen öğrenci ve net bilgisini eksiksiz girin!');

            fetch('/api/sinav_ekle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ogrenci_id, sinav_turu, ay, net: parseFloat(net)})
            }).then(() => {
                document.getElementById('sinavNet').value = '';
                sinavlariGetir();
                siralamaGetir();
                alert('Sınav neti başarıyla kaydedildi!');
            });
        }

        function sinavlariGetir() {
            const ogrenciId = document.getElementById('filtreSinavOgrenci').value;
            let url = '/api/sinavlar';
            if (ogrenciId) url += '?ogrenci_id=' + ogrenciId;

            fetch(url).then(r => r.json()).then(data => {
                let html = '';
                data.forEach(s => {
                    html += `<div class="card">
                        <button class="delete-btn" onclick="sinavSil(${s.id})">Sil</button>
                        <b>${s.ad_soyad}</b> - <span style="color:#e67e22;">${s.sinav_turu}</span> (${s.ay} Ayı): <b>${s.net} Net</b>
                    </div>`;
                });
                document.getElementById('sinavListesi').innerHTML = html || '<p>Henüz kayıtlı sınav yok.</p>';
            });
        }

        function sinavSil(id) {
            if (!confirm('Sınav kaydını silmek istiyor musunuz?')) return;
            fetch('/api/sinav_sil/' + id, { method: 'DELETE' }).then(() => {
                sinavlariGetir();
                siralamaGetir();
            });
        }

        function siralamaGetir() {
            const tur = document.getElementById('siralamaTuru').value;
            fetch('/api/siralama?sinav_turu=' + tur)
                .then(r => r.json())
                .then(data => {
                    let html = '';
                    data.forEach((item, index) => {
                        let rankBadge = `${index + 1}.`;
                        if (index === 0) rankBadge = '🥇 1.';
                        if (index === 1) rankBadge = '🥈 2.';
                        if (index === 2) rankBadge = '🥉 3.';

                        html += `<tr>
                            <td><b>${rankBadge}</b></td>
                            <td>${item.ad_soyad}</td>
                            <td>${item.sinif}</td>
                            <td><b>${item.ortalama} Net</b></td>
                            <td>${item.sinav_sayisi} Sınav</td>
                        </tr>`;
                    });
                    document.getElementById('siralamaTablosu').innerHTML = html || '<tr><td colspan="5">Henüz bu sınav türüne ait veri girilmedi.</td></tr>';
                });
        }

        function raporEkle() {
            const ogrenciId = document.getElementById('ogrenciSec').value;
            const notlar = document.getElementById('notMetni').value;
            const ses = document.getElementById('sesDosyasi').files[0];

            if (!ogrenciId) return alert('Lütfen öğrenci seçin!');

            const formData = new FormData();
            formData.append('ogrenci_id', ogrenciId);
            formData.append('notlar', notlar);
            if (ses) formData.append('ses_dosyasi', ses);

            fetch('/api/rapor_ekle', { method: 'POST', body: formData }).then(() => {
                document.getElementById('notMetni').value = '';
                document.getElementById('sesDosyasi').value = '';
                notlariGetir();
                alert('Not eklendi!');
            });
        }

        function notlariGetir() {
            const ogrenciId = document.getElementById('filtreOgrenci').value;
            let url = '/api/raporlar';
            if (ogrenciId) url += '?ogrenci_id=' + ogrenciId;

            fetch(url).then(r => r.json()).then(data => {
                let html =
