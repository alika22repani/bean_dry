# TA-06 — Random Forest: Klasifikasi Jenis Kacang Kering (Flask + Railway)

## Struktur
```
app.py                      server Flask (halaman + API /api/predict + /health)
templates/index.html        halaman web
static/style.css, app.js    tampilan & interaksi
model/                      ISI DARI NOTEBOOK: rf_dry_bean.joblib + metadata.json
figures/                    gambar hasil notebook (untuk laporan)
TA06_RandomForest_DryBean.ipynb
requirements.txt            dependensi untuk server (ringan)
requirements-notebook.txt   dependensi untuk menjalankan notebook
Procfile, railway.json, .python-version   konfigurasi deploy
```

## 1. Latih model (sekali saja)
1. `pip install -r requirements-notebook.txt`
2. Taruh `Dry_Bean_Dataset.xlsx` di folder ini (atau biarkan notebook mengunduh via `ucimlrepo`).
3. Jalankan semua sel notebook → terbentuk `model/rf_dry_bean.joblib`, `model/metadata.json`, dan gambar di `figures/`.
4. Cek ukuran file model: harus **< 100 MB** (batas GitHub). Jika lebih, kecilkan `n_estimators` atau isi `max_depth`.

## 2. Coba di komputer sendiri
```
pip install -r requirements.txt
python app.py            # buka http://localhost:5000
```
Atau seperti di Railway: `gunicorn app:app --bind 0.0.0.0:5000`

## 3. Samakan versi scikit-learn (penting)
Model `.joblib` harus dimuat dengan versi scikit-learn yang sama dengan saat melatih. Versinya tercatat di `model/metadata.json` (`sklearn_version`).
Buka `requirements.txt`, ganti baris `scikit-learn` menjadi mis. `scikit-learn==1.5.2` sesuai versi tersebut.

## 4. Deploy ke Railway
1. Buat repo GitHub baru, lalu push seluruh folder ini **termasuk folder `model/` yang sudah terisi**.
   ```
   git init && git add . && git commit -m "TA-06 random forest"
   git branch -M main && git remote add origin <URL-REPO> && git push -u origin main
   ```
2. Buka https://railway.com → **New Project → Deploy from GitHub repo** → pilih repo tadi.
3. Railway mendeteksi Python dari `requirements.txt` dan menjalankan perintah di `railway.json`/`Procfile` (gunicorn, port otomatis dari `$PORT`).
4. Setelah build selesai: **Settings → Networking → Generate Domain** → dapat URL publik `https://xxxx.up.railway.app`.
5. Tes: buka `/health` (harus `{"status":"ok"}`), lalu halaman utama.

### Jika bermasalah
- **Build gagal karena versi Python**: tambahkan variabel `RAILPACK_PYTHON_VERSION=3.11` (atau `NIXPACKS_PYTHON_VERSION=3.11`) di tab Variables.
- **Halaman "Model belum ditemukan"**: folder `model/` belum ikut di-push (cek `.gitignore` dan `git status`).
- **Error saat memuat model / peringatan versi**: samakan versi scikit-learn (langkah 3).
- **Memori habis**: kecilkan ukuran model; konfigurasi sudah memakai 1 worker agar model hanya dimuat sekali.

## Kerangka Laporan (template jurnal)
Lihat file `Laporan_TA06_RandomForest_DryBean.docx`. Cantumkan URL Railway di bagian Implementasi Aplikasi Web.
