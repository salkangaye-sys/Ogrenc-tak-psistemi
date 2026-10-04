import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_from_directory

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ----------------------------------------------------
# 1. VERİTABANI KURULUMU
# ----------------------------------------------------
def init_db():
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    
    # Öğrenciler Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ogrenciler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL,
            sinif TEXT
        )
    ''')
    
    # Notlar & Ses Kayıtları Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS raporlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ogrenci_id INTEGER,
            tarih TEXT,
            notlar TEXT,
            ses_dosyasi TEXT,
            FOREIGN KEY (ogrenci_id) REFERENCES ogrenciler (id) ON DELETE CASCADE
        )
    ''')
    
    # TYT / AYT Net Takip Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS netler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ogrenci_id INTEGER,
            ay TEXT,
            tyt_net REAL,
            ayt_net REAL,
            FOREIGN KEY (ogrenci_id) REFERENCES ogrenciler (id) ON DELETE CASCADE
        )
    ''')
    
    # Eğlence / Müzik Tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS muzikler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baslik TEXT NOT NULL,
            dosya_adi TEXT NOT NULL,
            tarih TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ----------------------------------------------------
# 2. ARAYÜZ (HTML / CSS / JAVASCRIPT - BLOKLU & SİLME ÖZELLİKLİ)
# ----------------------------------------------------
HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Öğrenci Takip Portalı</title>
    <style>
        * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background-color: #f4f7f6; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
        h1 { text-align: center; color: #2c3e50; margin-bottom: 25px; }
        
        /* SEKME (BLOK) BUTONLARI */
        .tab-buttons { display: flex; gap: 8px; margin-bottom: 25px; border-bottom: 2px solid #eee; padding-bottom: 10px; overflow-x: auto; }
        .tab-btn { flex: 1; padding: 12px 10px; border: none; background: #e9ecef; color: #495057; font-weight: bold; border-radius: 8px; cursor: pointer; transition: 0.3s; white-space: nowrap; font-size: 14px; }
        .tab-btn:hover { background: #dee2e6; }
        .tab-btn.active { background: #007bff; color: white; }
        
        /* BLOK İÇERİKLERİ */
        .tab-content { display: none; background: #fafafa; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; }
        .tab-content.active { display: block; }
        
        /* FORM ELEMANLARI */
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: 600; }
        input, select, textarea { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; }
        button.submit-btn { width: 100%; padding: 12px; background: #28a745; color: white; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 16px; margin-top: 10px; }
        button.submit-btn:hover { background: #218838; }
        .delete-btn { background: #dc3545; color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-weight: bold; font-size: 12px; float: right; }
        .delete-btn:hover { background: #bd2130; }
        
        /* TABLOLAR VE KARTLAR */
        table { width: 100%; border-collapse: collapse; margin-top: 15px; background: white; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background: #007bff; color: white; }
        .card { background: white; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); position: relative; }
        .card-header { font-weight: bold; color: #007bff; margin-bottom: 5px; }
        .card-date { font-size: 12px; color: #777; margin-bottom: 8px; }
        audio { width: 100%; margin-top: 10px; }
        
        ul.ogrenci-list { list-style: none; padding: 0; }
        ul.ogrenci-list li { background: white; padding: 12px; margin-bottom: 8px; border-radius: 6px; border: 1px solid #ddd; display: flex; justify-content: space-between; align-items: center; }
    </style>
</head>
<body>

<div class="container">
    <h1>🎓 Öğrenci Takip Portalı</h1>
    
    <!-- BLOK MENÜSÜ -->
    <div class="tab-buttons">
        <button class="tab-btn active" onclick="openTab('ogrenci-block', this)">🗂️ Öğrenciler</button>
        <button class="tab-btn" onclick="openTab('sesli-not-block', this)">🎙️ Sesli Not Ekle</button>
        <button class="tab-btn" onclick="openTab('net-block', this)">📈 TYT / AYT Netleri</button>
        <button class="tab-btn" onclick="openTab('gecmis-notlar-block', this)">📝 Geçmiş Notlar</button>
        <button class="tab-btn" onclick="openTab('eglence-block', this)">🎵 Eğlence & Müzik</button>
    </div>

    <!-- 1. BLOK: ÖĞRENCİ EKLE & LİSTELE (SİLME ÖZELLİKLİ) -->
    <div id="ogrenci-block" class="tab-content active">
        <h3>Yeni Öğrenci Ekle</h3>
        <div class="form-group"><input type="text" id="adSoyad" placeholder="Öğrenci Adı Soyadı"></div>
        <div class="form-group"><input type="text" id="sinif" placeholder="Sınıfı (Örn: 12-A / TYT)"></div>
        <button class="submit-btn" onclick="ogrenciEkle()">Kaydet</button>
        
        <h3 style="margin-top: 30px;">Kayıtlı Öğrenciler</h3>
        <div id="ogrenciListesi"></div>
    </div>

    <!-- 2. BLOK: SESLİ NOT EKLE -->
    <div id="sesli-not-block" class="tab-content">
        <h3>Öğrenciye Not & Ses Kaydı Ekle</h3>
        <div class="form-group">
            <label>Öğrenci Seçin:</label>
            <select id="notOgrenciSelect"><option value="">Yükleniyor...</option></select>
        </div>
        <div class="form-group">
            <label>Ders Notu / Açıklama:</label>
            <textarea id="dersNotu" rows="4" placeholder="Öğrencinin durumuyla ilgili notlar..."></textarea>
        </div>
        <div class="form-group">
            <label>🎙️️ Ses Dosyası Yükle:</label>
            <input type="file" id="sesDosyasi" accept="audio/*">
        </div>
        <button class="submit-btn" onclick="notKaydet()">Notu Kaydet</button>
    </div>

    <!-- 3. BLOK: TYT / AYT NET TAKİBİ -->
    <div id="net-block" class="tab-content">
        <h3>Aylık TYT / AYT Net Kaydı</h3>
        <div class="form-group">
            <label>Öğrenci Seçin:</label>
            <select id="netOgrenciSelect"><option value="">Yükleniyor...</option></select>
        </div>
        <div class="form-group">
            <label>Ay Seçin:</label>
            <select id="netAySelect">
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
        </div>
        <div style="display: flex; gap: 10px;">
            <div class="form-group" style="flex:1;">
                <label>TYT Net:</label>
                <input type="number" step="0.25" id="tytNet" placeholder="Örn: 65.5">
            </div>
            <div class="form-group" style="flex:1;">
                <label>AYT Net:</label>
                <input type="number" step="0.25" id="aytNet" placeholder="Örn: 42.0">
            </div>
        </div>
        <button class="submit-btn" onclick="netKaydet()">Netleri Kaydet</button>

        <h3 style="margin-top: 30px;">Tüm Aylık Net Tablosu</h3>
        <table>
            <thead>
                <tr>
                    <th>Öğrenci</th>
                    <th>Ay</th>
                    <th>TYT Net</th>
                    <th>AYT Net</th>
                </tr>
            </thead>
            <tbody id="netlerTableBody"></tbody>
        </table>
    </div>

    <!-- 4. BLOK: GEÇMİŞ NOTLAR VE SESLER (SİLME ÖZELLİKLİ) -->
    <div id="gecmis-notlar-block" class="tab-content">
        <h3>Öğrenciler Hakkında Yazılan Geçmiş Notlar</h3>
        <div class="form-group">
            <label>Filtrele (Öğrenci Seçin):</label>
            <select id="filtreOgrenciSelect" onchange="gecmisNotlariYukle()">
                <option value="">Tüm Öğrenciler</option>
            </select>
        </div>
        <div id="gecmisNotlarListesi"></div>
    </div>

    <!-- 5. BLOK: EĞLENCE & MÜZİK -->
    <div id="eglence-block" class="tab-content">
        <h3>🎵 Müzik / Eğlence Alanı</h3>
        <p>Aşağıdan dinlemek istediğiniz şarkı veya müzik dosyalarını yükleyebilirsiniz.</p>
        <div class="form-group">
            <label>Müzik / Şarkı Adı:</label>
            <input type="text" id="muzikBaslik" placeholder="Örn: Odaklanma Müzik 1">
        </div>
        <div class="form-group">
            <label>Müzik Dosyası (MP3/WAV):</label>
            <input type="file" id="muzikDosyasi" accept="audio/*">
        </div>
        <button class="submit-btn" onclick="muzikYukle()">Müziği Yükle</button>

        <h3 style="margin-top: 30px;">Müzik Listeniz</h3>
        <div id="muzikListesi"></div>
    </div>
</div>

<script>
    // BLOK SEÇİMİ
    function openTab(tabId, btn) {
        document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
        document.getElementById(tabId).classList.add('active');
        btn.classList.add('active');
        
        if(tabId === 'gecmis-notlar-block') gecmisNotlariYukle();
        if(tabId === 'net-block') netleriYukle();
        if(tabId === 'eglence-block') muzikleriYukle();
    }

    // SAYFA YÜKLENİNCE
    window.onload = function() {
        ogrencileriYukle();
    };

    function ogrencileriYukle() {
        fetch('/api/ogrenciler')
        .then(r => r.json())
        .then(data => {
            let html = '<ul class="ogrenci-list">';
            let selectOptions = '<option value="">-- Öğrenci Seçin --</option>';
            data.forEach(o => {
                html += `<li>
                    <span><strong>${o.ad_soyad}</strong> - ${o.sinif}</span>
                    <button class="delete-btn" onclick="ogrenciSil(${o.id})">Sil</button>
                </li>`;
                selectOptions += `<option value="${o.id}">${o.ad_soyad} (${o.sinif})</option>`;
            });
            html += '</ul>';
            
            document.getElementById('ogrenciListesi').innerHTML = html;
            document.getElementById('notOgrenciSelect').innerHTML = selectOptions;
            document.getElementById('netOgrenciSelect').innerHTML = selectOptions;
            document.getElementById('filtreOgrenciSelect').innerHTML = '<option value="">Tüm Öğrenciler</option>' + selectOptions.replace('<option value="">-- Öğrenci Seçin --</option>', '');
        });
    }

    function ogrenciEkle() {
        let ad_soyad = document.getElementById('adSoyad').value;
        let sinif = document.getElementById('sinif').value;
        if(!ad_soyad) return alert('Lütfen isim yazın!');

        fetch('/api/ogrenci_ekle', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ad_soyad, sinif})
        }).then(() => {
            document.getElementById('adSoyad').value = '';
            document.getElementById('sinif').value = '';
            ogrencileriYukle();
            alert('Öğrenci eklendi!');
        });
    }

    function ogrenciSil(id) {
        if(!confirm('Bu öğrenciyi ve öğrenciye ait tüm notları/netleri silmek istediğinizden emin misiniz?')) return;
        fetch('/api/ogrenci_sil/' + id, { method: 'DELETE' })
        .then(() => {
            ogrencileriYukle();
            alert('Öğrenci silindi!');
        });
    }

    function notKaydet() {
        let ogrenci_id = document.getElementById('notOgrenciSelect').value;
        let notlar = document.getElementById('dersNotu').value;
        let sesFile = document.getElementById('sesDosyasi').files[0];

        if(!ogrenci_id) return alert('Lütfen öğrenci seçin!');

        let formData = new FormData();
        formData.append('ogrenci_id', ogrenci_id);
        formData.append('notlar', notlar);
        if(sesFile) formData.append('ses', sesFile);

        fetch('/api/not_ekle', {
            method: 'POST',
            body: formData
        }).then(() => {
            document.getElementById('dersNotu').value = '';
            document.getElementById('sesDosyasi').value = '';
            alert('Not ve ses kaydı başarıyla kaydedildi!');
        });
    }

    function notSil(id) {
        if(!confirm('Bu notu silmek istediğinizden emin misiniz?')) return;
        fetch('/api/not_sil/' + id, { method: 'DELETE' })
        .then(() => {
            gecmisNotlariYukle();
            alert('Not silindi!');
        });
    }

    function netKaydet() {
        let ogrenci_id = document.getElementById('netOgrenciSelect').value;
        let ay = document.getElementById('netAySelect').value;
        let tyt_net = document.getElementById('tytNet').value;
        let ayt_net = document.getElementById('aytNet').value;

        if(!ogrenci_id) return alert('Lütfen öğrenci seçin!');

        fetch('/api/net_ekle', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ogrenci_id, ay, tyt_net, ayt_net})
        }).then(() => {
            document.getElementById('tytNet').value = '';
            document.getElementById('aytNet').value = '';
            netleriYukle();
            alert('Netler kaydedildi!');
        });
    }

    function netleriYukle() {
        fetch('/api/netler')
        .then(r => r.json())
        .then(data => {
            let html = '';
            data.forEach(n => {
                html += `<tr>
                    <td>${n.ad_soyad}</td>
                    <td>${n.ay}</td>
                    <td><strong>${n.tyt_net}</strong></td>
                    <td><strong>${n.ayt_net}</strong></td>
                </tr>`;
            });
            document.getElementById('netlerTableBody').innerHTML = html;
        });
    }

    function gecmisNotlariYukle() {
        let ogrenci_id = document.getElementById('filtreOgrenciSelect').value;
        fetch('/api/gecmis_notlar?ogrenci_id=' + ogrenci_id)
        .then(r => r.json())
        .then(data => {
            let html = '';
            if(data.length === 0) html = '<p>Henüz kayıtlı bir not bulunamadı.</p>';
            data.forEach(item => {
                html += `<div class="card">
                    <button class="delete-btn" onclick="notSil(${item.id})">Bu Notu Sil</button>
                    <div class="card-header">👤 ${item.ad_soyad} (${item.sinif})</div>
                    <div class="card-date">📅 ${item.tarih}</div>
                    <div>${item.notlar || '<i>Not metni girilmemiş.</i>'}</div>`;
                if(item.ses_dosyasi) {
                    html += `<audio controls src="/uploads/${item.ses_dosyasi}"></audio>`;
                }
                html += `</div>`;
            });
            document.getElementById('gecmisNotlarListesi').innerHTML = html;
        });
    }

    // EĞLENCE & MÜZİK FONKSİYONLARI
    function muzikYukle() {
        let baslik = document.getElementById('muzikBaslik').value;
        let muzikFile = document.getElementById('muzikDosyasi').files[0];

        if(!baslik || !muzikFile) return alert('Lütfen müzik başlığı ve dosyasını seçin!');

        let formData = new FormData();
        formData.append('baslik', baslik);
        formData.append('muzik', muzikFile);

        fetch('/api/muzik_ekle', {
            method: 'POST',
            body: formData
        }).then(() => {
            document.getElementById('muzikBaslik').value = '';
            document.getElementById('muzikDosyasi').value = '';
            muzikleriYukle();
            alert('Müzik yüklendi!');
        });
    }

    function muzikleriYukle() {
        fetch('/api/muzikler')
        .then(r => r.json())
        .then(data => {
            let html = '';
            if(data.length === 0) html = '<p>Henüz yüklenmiş müzik bulunmuyor.</p>';
            data.forEach(m => {
                html += `<div class="card">
                    <button class="delete-btn" onclick="muzikSil(${m.id})">Sil</button>
                    <div class="card-header">🎵 ${m.baslik}</div>
                    <div class="card-date">📅 Yükleme Tarihi: ${m.tarih}</div>
                    <audio controls src="/uploads/${m.dosya_adi}"></audio>
                </div>`;
            });
            document.getElementById('muzikListesi').innerHTML = html;
        });
    }

    function muzikSil(id) {
        if(!confirm('Bu müziği silmek istediğinizden emin misiniz?')) return;
        fetch('/api/muzik_sil/' + id, { method: 'DELETE' })
        .then(() => {
            muzikleriYukle();
            alert('Müzik silindi!');
        });
    }
</script>
</body>
</html>
"""

# ----------------------------------------------------
# 3. SUNUCU ROTALARI VE API (BACKEND)
# ----------------------------------------------------
@app.route('/')
def index():
    return render_template_string(HTML_LAYOUT)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/ogrenciler', methods=['GET'])
def get_ogrenciler():
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, ad_soyad, sinif FROM ogrenciler ORDER BY ad_soyad ASC')
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"id": r[0], "ad_soyad": r[1], "sinif": r[2]} for r in rows])

@app.route('/api/ogrenci_ekle', methods=['POST'])
def add_ogrenci():
    data = request.json
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO ogrenciler (ad_soyad, sinif) VALUES (?, ?)', (data['ad_soyad'], data['sinif']))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/ogrenci_sil/<int:id>', methods=['DELETE'])
def delete_ogrenci(id):
    conn = sqlite3.connect('ogretmen.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM ogrenciler WHERE id = ?', (id,))
    cursor.execute('DELETE FROM raporlar WHERE ogrenci_id = ?', (id,))
    cursor.execute('DELETE FROM netler WHERE ogrenci_id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/not_ekle', methods=['POST'])
def add_not():
    ogrenci_id = request.form.get('ogrenci_id')
    notlar = request.form.get('notlar')
    ses_file = request.files.get('ses')
    
    filename = None
    if ses_file:
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{ses_file.filename}"
        ses_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
    tarih = datetime.now().strfti
