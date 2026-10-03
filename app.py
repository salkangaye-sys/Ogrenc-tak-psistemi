import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_from_directory

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------------------------------------------------
# 1. VERİTABANI KURULUMU
# ---------------------------------------------------------
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
            ses_dosyasi TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# 2. ARAYÜZ (HTML / CSS / JAVASCRIPT)
# ---------------------------------------------------------
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Öğrenci Takip Portalı</title>
    <style>
        body { font-family: sans-serif; padding: 15px; background: #f0f2f5; margin: 0; }
        .box { background: white; padding: 15px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        input, button, textarea, select { width: 100%; padding: 10px; margin: 5px 0; border-radius: 5px; border: 1px solid #ccc; box-sizing: border-box; }
        button { background: #007bff; color: white; border: none; font-weight: bold; cursor: pointer; }
        .btn-danger { background: #dc3545; }
        .btn-warning { background: #ffc107; color: black; }
        .btn-success { background: #28a745; }
        .btn-sm { width: auto; padding: 5px 10px; font-size: 12px; margin-right: 5px; display: inline-block; }
        .ogrenci-card { background: #e9ecef; padding: 12px; margin-top: 10px; border-radius: 5px; }
        .rapor-card { background: #f8f9fa; border-left: 4px solid #007bff; padding: 10px; margin: 8px 0; border-radius: 4px; }
        .flex-btns { display: flex; gap: 5px; margin-top: 5px; }
        .audio-box { background: #e3f2fd; padding: 10px; border-radius: 5px; margin: 5px 0; }
    </style>
</head>
<body>
    <h2>🎓 Öğrenci Takip Sistemi</h2>
    
    <!-- Öğrenci Ekleme Formu -->
    <div class="box">
        <h3>Yeni Öğrenci Ekle</h3>
        <input type="text" id="ad" placeholder="Ad Soyad">
        <input type="text" id="sinif" placeholder="Sınıf">
        <button onclick="ogrenciEkle()">Kaydet</button>
    </div>

    <!-- Rapor / Not & Ses Ekleme Formu -->
    <div class="box">
        <h3>Öğrenciye Not & Ses Kaydı Ekle</h3>
        <select id="seciliOgrenci">
            <option value="">-- Öğrenci Seçin --</option>
            {% for o in ogrenciler %}
                <option value="{{ o[0] }}">{{ o[1] }} ({{ o[2] }})</option>
            {% endfor %}
        </select>
        <textarea id="notlar" rows="3" placeholder="Ders notu yazın..."></textarea>
        
        <div class="audio-box">
            <label><strong>🎙️ Ses Kaydı / Dosyası Ekle:</strong></label>
            <input type="file" id="sesDosyasi" accept="audio/*">
        </div>

        <button onclick="raporEkle()">Notu ve Sesi Kaydet</button>
    </div>

    <!-- Öğrenci ve Geçmiş Notlar Listesi -->
    <div class="box">
        <h3>Öğrenci Listesi ve Geçmiş Notlar</h3>
        {% for o in ogrenciler %}
            <div class="ogrenci-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong>{{ o[1] }}</strong> ({{ o[2] }})
                    <button class="btn-danger btn-sm" onclick="ogrenciSil({{ o[0] }})">Öğrenciyi Sil</button>
                </div>
                <button class="btn-sm btn-warning" onclick="raporlariYukle({{ o[0] }})">Geçmiş Notları Gör / Düzenle</button>
                <div id="raporlar-{{ o[0] }}" style="display:none; margin-top:10px;"></div>
            </div>
        {% endfor %}
    </div>

    <script>
        async function ogrenciEkle() {
            let ad = document.getElementById('ad').value;
            let sinif = document.getElementById('sinif').value;
            if(!ad) return alert('Lütfen isim girin');

            await fetch('/ogrenci-ekle', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ad_soyad: ad, sinif: sinif})
            });
            location.reload();
        }

        async function ogrenciSil(id) {
            if(!confirm("Bu öğrenciyi ve tüm notlarını silmek istediğinize emin misiniz?")) return;
            await fetch('/ogrenci-sil/' + id, { method: 'DELETE' });
            location.reload();
        }

        async function raporEkle() {
            let ogrenci_id = document.getElementById('seciliOgrenci').value;
            let notlar = document.getElementById('notlar').value;
            let sesInput = document.getElementById('sesDosyasi');

            if(!ogrenci_id) return alert('Lütfen öğrenci seçin');

            let formData = new FormData();
            formData.append('ogrenci_id', ogrenci_id);
            formData.append('notlar', notlar);

            if (sesInput.files.length > 0) {
                formData.append('ses', sesInput.files[0]);
            }

            await fetch('/rapor-ekle', {
                method: 'POST',
                body: formData
            });

            alert('Not ve Ses Kaydı Başarıyla Eklendi!');
            document.getElementById('notlar').value = '';
            sesInput.value = '';
            raporlariYukle(ogrenci_id);
        }

        async function raporlariYukle(ogrenci_id) {
            let div = document.getElementById('raporlar-' + ogrenci_id);
            if(div.style.display === 'block') {
                div.style.display = 'none';
                return;
            }

            let res = await fetch('/raporlar/' + ogrenci_id);
            let veriler = await res.json();
            let html = '';

            if(veriler.length === 0) {
                html = '<small>Henüz eklenmiş not yok.</small>';
            } else {
                veriler.forEach(r => {
                    html += `
                        <div class="rapor-card">
                            <small style="color:#666;">📅 ${r.tarih}</small>
                            <textarea id="not-text-${r.id}" rows="2">${r.notlar || ''}</textarea>
                            ${r.ses_dosyasi ? `<audio controls src="/uploads/${r.ses_dosyasi}" style="width:100%; margin-top:5px;"></audio>` : ''}
                            <div class="flex-btns">
                                <button class="btn-sm btn-warning" onclick="raporGuncelle(${r.id})">Güncelle</button>
                                <button class="btn-sm btn-danger" onclick="raporSil(${r.id}, ${ogrenci_id})">Sil</button>
                            </div>
                        </div>
                    `;
                });
            }
            div.innerHTML = html;
            div.style.display = 'block';
        }

        async function raporGuncelle(id) {
            let yeniNot = document.getElementById('not-text-' + id).value;
            await fetch('/rapor-guncelle/' + id, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({notlar: yeniNot})
            });
            alert('Not güncellendi!');
        }

        async function raporSil(rapor_id, ogrenci_id) {
            if(!confirm("Bu notu silmek istediğinize emin misiniz?")) return;
            await fetch('/rapor-sil/' + rapor_id, { method: 'DELETE' });
            raporlariYukle(ogrenci_id);
        }
    </script>
</body>
</html>
"""

# ---------------------------------------------------------
# 3. SUNUCU YÖNLENDİRMELERİ (ROUTES)
# ---------------------------------------------------------
@app.route('/')
def home():
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ogrenciler")
    ogrenciler = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_LAYOUT, ogrenciler=ogrenciler)

@app.route('/ogrenci-ekle', methods=['POST'])
def ogrenci_ekle():
    data = request.json
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ogrenciler (ad_soyad, sinif) VALUES (?, ?)", (data['ad_soyad'], data['sinif']))
    conn.commit()
    conn.close()
    return jsonify({"durum": "ok"})

@app.route('/ogrenci-sil/<int:id>', methods=['DELETE'])
def ogrenci_sil(id):
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ogrenciler WHERE id = ?", (id,))
    cursor.execute("DELETE FROM raporlar WHERE ogrenci_id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"durum": "ok"})

@app.route('/rapor-ekle', methods=['POST'])
def rapor_ekle():
    ogrenci_id = request.form.get('ogrenci_id')
    notlar = request.form.get('notlar')
    tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
    ses_dosya_adi = None

    if 'ses' in request.files:
        ses_file = request.files['ses']
        if ses_file.filename != '':
            uzanti = ses_file.filename.split('.')[-1]
            dosya_adi = f"ogrenci_{ogrenci_id}_{int(datetime.now().timestamp())}.{uzanti}"
            ses_file.save(os.path.join(app.config['UPLOAD_FOLDER'], dosya_adi))
            ses_dosya_adi = dosya_adi

    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO raporlar (ogrenci_id, tarih, notlar, ses_dosyasi) VALUES (?, ?, ?, ?)", 
                   (ogrenci_id, tarih, notlar, ses_dosya_adi))
    conn.commit()
    conn.close()
    return jsonify({"durum": "ok"})

@app.route('/raporlar/<int:ogrenci_id>')
def raporlari_getir(ogrenci_id):
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, tarih, notlar, ses_dosyasi FROM raporlar WHERE ogrenci_id = ? ORDER BY id DESC", (ogrenci_id,))
    raporlar = cursor.fetchall()
    conn.close()
    
    veri = []
    for r in raporlar:
        veri.append({
            "id": r[0],
            "tarih": r[1],
            "notlar": r[2],
            "ses_dosyasi": r[3]
        })
    return jsonify(veri)

@app.route('/rapor-guncelle/<int:id>', methods=['PUT'])
def rapor_guncelle(id):
    data = request.json
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE raporlar SET notlar = ? WHERE id = ?", (data['notlar'], id))
    conn.commit()
    conn.close()
    return jsonify({"durum": "ok"})

@app.route('/rapor-sil/<int:id>', methods=['DELETE'])
def rapor_sil(id):
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM raporlar WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"durum": "ok"})

@app.route('/uploads/<filename>')
def upload_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ---------------------------------------------------------
# 4. ÇALIŞTIRMA
# ---------------------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
