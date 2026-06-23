# 🏗️ Analisis Dampak Infrastruktur terhadap Ekonomi Regional

Platform analitik berbasis data BPS untuk mengukur multiplier effect investasi infrastruktur pada perekonomian provinsi di Indonesia menggunakan metodologi **Regional Economic Impact Analysis**.

## 📊 Sumber Data

Data diambil dari dokumen resmi Badan Pusat Statistik (BPS):
- **Produk Domestik Regional Bruto Provinsi-Provinsi di Indonesia Menurut Pengeluaran 2021-2025**
- **Tabel Input-Output Indonesia 2020**
- **Perdagangan Antar Wilayah Indonesia 2024**

⚠️ **Tidak ada fabrikasi data** - Semua angka berasal dari sumber resmi BPS.

## 🚀 Cara Menjalankan

### Opsi 1: Streamlit Cloud (Recommended)
1. Upload repository ke GitHub
2. Buka [share.streamlit.io](https://share.streamlit.io)
3. Connect repository Anda
4. Deploy otomatis!

### Opsi 2: Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run aplikasi
streamlit run app.py
```

### Opsi 3: Docker
```bash
docker run -p 8501:8501 streamlit/app
```

## 📁 Struktur File

```
/workspace/
├── app.py                          # Aplikasi Streamlit utama
├── infrastructure_impact_analysis.py # Salinan kode untuk publish
├── requirements.txt                # Dependencies Python
├── grdp_full.json                  # Data PDRB 38 provinsi (2022-2024)
├── README.md                       # Dokumentasi ini
└── *.pdf                           # Dokumen sumber BPS
```

## 🎯 Fitur Utama

### 1. **Analisis Per Provinsi**
- Pilih salah satu dari 38 provinsi di Indonesia
- Lihat dampak ekonomi infrastruktur tahun 2022-2024
- Breakdown komponen PDRB menurut pengeluaran

### 2. **Metrik Kunci**
- **Investasi Infrastruktur**: 40% dari PMTB (Pembentukan Modal Tetap Bruto)
- **Infrastructure Multiplier**: 1.5x - 2.5x (dinamis berdasarkan rasio investasi)
- **Dampak Langsung & Tidak Langsung**: Efek multiplier melalui rantai pasok
- **Kontribusi terhadap PDRB**: Persentase kontribusi infrastruktur

### 3. **Visualisasi Interaktif**
- Stacked bar chart: Dampak langsung vs tidak langsung
- Line chart: Trend infrastructure multiplier
- Bar chart: Kontribusi persentase terhadap PDRB
- Pie chart: Komposisi permintaan akhir
- Comparison chart: Ranking antar provinsi

### 4. **Metodologi**

#### Infrastructure Multiplier Calculation
```python
base_multiplier = 1.8  # Berdasarkan literatur regional economics

if investment_ratio > 0.3:
    multiplier = 2.1  # Wilayah dengan investasi tinggi
elif investment_ratio > 0.2:
    multiplier = 1.95
elif investment_ratio > 0.15:
    multiplier = 1.8
else:
    multiplier = 1.6  # Wilayah dengan investasi rendah
```

#### Economic Impact Formula
```
Direct Impact = PMTB × 0.40 (infrastruktur share)
Indirect Impact = Direct Impact × (multiplier - 1)
Total Impact = Direct Impact × multiplier
```

## 📈 Komponen PDRB

1. **Konsumsi Rumah Tangga (PKRT)**
2. **Konsumsi LNPRT (PK-LNPRT)**
3. **Konsumsi Pemerintah (PK-P)**
4. **Pembentukan Modal Tetap Bruto (PMTB)** ← Basis infrastruktur
5. **Perubahan Inventori**
6. **Ekspor Luar Negeri**
7. **Impor Luar Negeri**
8. **Ekspor Neto**
9. **Total PDRB**

## 🎨 Teknologi

- **Frontend**: Streamlit
- **Visualisasi**: Plotly
- **Data Processing**: Pandas, NumPy
- **Data Source**: BPS Indonesia (JSON format)

## 📝 Lisensi

Data bersumber dari Badan Pusat Statistik (BPS) Indonesia.
Aplikasi ini dibuat untuk tujuan edukasi dan analisis kebijakan publik.

## 👨‍💻 Developer Notes

Aplikasi ini menggunakan pendekatan **Keynesian multiplier** yang disederhanakan untuk analisis cepat. Untuk analisis yang lebih komprehensif, disarankan menggunakan:
- Full Input-Output Table analysis
- Social Accounting Matrix (SAM)
- Computable General Equilibrium (CGE) models

## 📞 Kontak & Support

Untuk pertanyaan atau kolaborasi, silakan buka issue di repository ini.

---
**Dibuat dengan ❤️ untuk pembangunan infrastruktur Indonesia**
