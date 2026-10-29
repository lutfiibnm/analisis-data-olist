# Proyek Analisis Data: E-Commerce Public Dataset (Olist)

Analisis data penjualan e-commerce Brasil (Olist) meliputi tren pesanan dan pendapatan, sebaran wilayah (geospatial), segmentasi pelanggan (RFM), serta hubungan keterlambatan pengiriman dengan skor ulasan. Hasil akhir ditampilkan dalam dashboard interaktif menggunakan Streamlit.

## Struktur Direktori

```
submission
├── dashboard
│   ├── main_data.csv      # tabel hasil wrangling (sumber data dashboard)
│   └── dashboard.py       # kode dashboard Streamlit
├── data                   # 9 file CSV dataset asli
├── notebook.ipynb         # proses analisis lengkap (wrangling, EDA, visualisasi, RFM, geospatial)
├── README.md
├── requirements.txt
└── url.txt                # tautan dashboard di Streamlit Cloud
```

## Setup Environment

Disarankan memakai Python 3.9 atau lebih baru.

### Menggunakan virtual environment (venv)

```
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Menggunakan Anaconda

```
conda create --name main-ds python=3.9
conda activate main-ds
pip install -r requirements.txt
```

## Menjalankan Dashboard

Jalankan perintah berikut dari folder `submission`:

```
streamlit run dashboard/dashboard.py
```

Perintah `cd dashboard` lalu `streamlit run dashboard.py` juga berfungsi, karena path data dibaca relatif terhadap lokasi `dashboard.py`. Dashboard akan terbuka di browser (biasanya `http://localhost:8501`). Gunakan filter rentang tanggal dan state di sidebar untuk mengubah tampilan.

## Menjalankan Notebook

Buka `notebook.ipynb` dari folder `submission` (path data dibaca relatif ke folder tersebut), lalu jalankan semua sel secara berurutan. Sel terakhir pada tahap *cleaning* akan menulis ulang `dashboard/main_data.csv`.

## Deploy ke Streamlit Cloud

1. Unggah folder proyek ke repositori GitHub.
2. Masuk ke [share.streamlit.io](https://share.streamlit.io) dan buat aplikasi baru dari repositori tersebut.
3. Isi *Main file path* dengan `dashboard/dashboard.py`.
4. Setelah aplikasi aktif, salin tautannya ke `url.txt`.

## Catatan Metodologi

- Hanya pesanan berstatus *delivered* yang dianalisis. Pendapatan = jumlah `price` (tanpa ongkos kirim).
- Pelanggan diidentifikasi dengan `customer_unique_id`.
- Periode tren dibatasi Januari 2017 - Agustus 2018 (periode lain datanya belum lengkap).
- Segmentasi RFM memakai skor kuartil untuk Recency dan Monetary, serta pengelompokan manual untuk Frequency.
- Koordinat pada peta adalah titik tengah (median) kode pos, bukan alamat pelanggan.
