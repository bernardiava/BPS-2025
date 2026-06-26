# 🇮🇩 Analisis Dampak Infrastruktur & Ekonomi Indonesia (Input-Output Analysis 2025)

Aplikasi interaktif untuk menganalisis dampak ekonomi dari investasi infrastruktur dan sektor lainnya di Indonesia menggunakan model **Input-Output (I-O)** berdasarkan data BPS terbaru. Aplikasi ini dirancang untuk pembuat kebijakan, peneliti, dan masyarakat umum untuk memahami bagaimana pengeluaran di satu sektor dapat menciptakan efek berganda (*multiplier effect*) pada seluruh perekonomian.

🔗 **Akses Aplikasi Live:** [https://dampakinfrastruktur.streamlit.app/](https://dampakinfrastruktur.streamlit.app/)

---

## 🌟 Fitur Utama

### 1. 📊 Dashboard Dampak
Visualisasi cepat mengenai sektor-sektor dengan multiplier tertinggi dan kontribusinya terhadap PDB nasional.

### 2. 🏛️ Input-Output Analysis (Lengkap)
Analisis mendalam menggunakan kerangka kerja *Rasmussen-Hirschman* untuk mengklasifikasikan sektor menjadi:
- **Key Sector:** Sektor penggerak utama (Linkage Hulu & Hilir tinggi).
- **Base Industry:** Penggerak industri hulu (supplier).
- **Strategic Sector:** Enabler bagi industri hilir.
- **Standard Sector:** Sektor dengan peran standar.

**Termasuk di dalamnya:**
- **Interpretasi Awam:** Penjelasan sederhana tentang mengapa sektor seperti Listrik dan Konstruksi memiliki dampak besar.
- **Rekomendasi Kebijakan:** Saran strategis berbasis data untuk pemerintah dan investor.
- **Simulator Kebijakan:** Hitung sendiri dampak ekonomi dari sebuah rencana investasi (misal: "Jika pemerintah membangun jalan tol senilai Rp 1 Triliun, berapa total uang yang berputar?").

### 3. 🧠 Interpretasi & Kebijakan
Panduan praktis menerjemahkan angka statistik menjadi aksi nyata, disesuaikan dengan konteks sosial-budaya Indonesia.

### 4. 📋 Breakdown Data
Tabel data mentah yang dapat diunduh untuk keperluan riset lebih lanjut.

### 5. 🗺️ Komparasi Nasional
Perbandingan antar wilayah atau periode waktu (jika data tersedia).

---

## 📈 Metodologi

Aplikasi ini menggunakan model **Leontief Demand-Pull**:
1.  **Koefisien Teknis (A):** Menghitung proporsi input yang dibutuhkan setiap sektor untuk menghasilkan satu unit output.
2.  **Matriks Invers Leontief $(I-A)^{-1}$:** Menghitung total kebutuhan langsung dan tidak langsung dari seluruh sektor.
3.  **Output Multiplier:** Dijumlahkan per kolom dari Matriks Invers Leontief.
    *   *Contoh:* Multiplier 2.35x pada sektor Listrik berarti setiap kenaikan permintaan akhir sebesar Rp 1 Miliar di sektor listrik, akan meningkatkan total output perekonomian sebesar Rp 2.35 Miliar.

---

## 🚀 Cara Menjalankan Secara Lokal

Jika Anda ingin menjalankan aplikasi ini di komputer Anda sendiri:

### Prasyarat
- Python 3.8 atau lebih baru
- pip (Python package manager)

### Langkah Instalasi

1.  **Clone Repositori**
    ```bash
    git clone https://github.com/username-anda/bps-2025.git
    cd bps-2025
    ```

2.  **Instal Dependensi**
    ```bash
    pip install -r requirements.txt
    ```
    *(Pastikan file `requirements.txt` berisi: `streamlit`, `pandas`, `numpy`, `plotly`)*

3.  **Jalankan Aplikasi**
    ```bash
    streamlit run app.py
    ```

4.  **Buka Browser**
    Aplikasi akan otomatis terbuka di `http://localhost:8501`.

---

## 📂 Struktur Data

Data yang digunakan bersumber dari **Tabel Input-Output (TIO) Badan Pusat Statistik (BPS)** tahun terbaru (misal: 2020/2023).
- **Sektor:** 35 Kategori Industri (Berdasarkan KBLI).
- **Satuan:** Juta Rupiah / Juta USD (sesuai konfigurasi).
- **Komponen:** Transaksi Antar Sektor, Pajak, Impor, Permintaan Akhir.

---

## 📄 Laporan HTML

Selain aplikasi web, tersedia juga versi laporan statis interaktif (`io_analysis_report.html`) yang dapat dibuka langsung di browser tanpa perlu instalasi Python. Laporan ini mencakup grafik, tabel, dan simulator sederhana.

---

## 👥 Kontribusi

Kami sangat terbuka terhadap kontribusi untuk perbaikan data, penambahan fitur visualisasi, atau penyempurnaan interpretasi ekonomi. Silakan buat *Pull Request* atau buka *Issue* di repositori ini.

## 📜 Lisensi

Proyek ini dibuat untuk tujuan edukasi dan dukungan kebijakan publik. Data mentah tetap mengikuti lisensi dari Badan Pusat Statistik (BPS).

---

<div align="center">

**Dibuat dengan ❤️ untuk Pembangunan Indonesia**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://dampakinfrastruktur.streamlit.app/)

</div>
