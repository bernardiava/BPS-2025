"""
Aplikasi Streamlit untuk Analisis Dampak Infrastruktur terhadap Ekonomi Regional
Data sumber: Badan Pusat Statistik (BPS) Indonesia
- Produk Domestik Regional Bruto Provinsi-Provinsi di Indonesia Menurut Pengeluaran 2021-2025
- Tabel Input-Output Indonesia 2020
- Perdagangan Antar Wilayah Indonesia 2024

Metodologi: Regional Economic Impact Analysis dengan pendekatan multiplier effect
Input-Output Analysis menggunakan Leontief Inverse Matrix
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os
from io_analysis import InputOutputAnalyzer, create_io_summary

# Konfigurasi halaman
st.set_page_config(
    page_title="Analisis Dampak Infrastruktur Regional",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk styling profesional
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stAlert {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Load data dari JSON
# Load data dari JSON
@st.cache_data
def load_grdp_data():
    """Load GRDP data dari file JSON dengan multiple fallback options"""
    
    # Opsi 1: Coba dari GitHub (URL yang benar)
    github_url = 'https://raw.githubusercontent.com/bernardiava/BPS-2025/main/grdp_full.json'
    
    # Opsi 2: Coba dari file lokal (jika diupload ke workspace)
    local_file = 'grdp_full.json'
    
    # Opsi 3: Coba dari folder data (struktur umum)
    local_file_data = 'data/grdp_full.json'
    
    # Step 1: Cek URL GitHub
    try:
        import requests
        response = requests.get(github_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            st.success("✅ Data berhasil dimuat dari GitHub!")
            return data
        elif response.status_code == 404:
            st.warning("⚠️ File tidak ditemukan di GitHub. Mencoba sumber lain...")
        else:
            st.warning(f"⚠️ GitHub response: {response.status_code}. Mencoba sumber lain...")
            
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ Tidak dapat terhubung ke GitHub. Mencoba sumber lokal...")
    except Exception as e:
        st.warning(f"⚠️ Error GitHub: {e}. Mencoba sumber lokal...")
    
    # Step 2: Coba file lokal di root
    try:
        with open(local_file, 'r') as f:
            data = json.load(f)
            st.success("✅ Data berhasil dimuat dari file lokal!")
            return data
    except FileNotFoundError:
        st.warning(f"⚠️ File {local_file} tidak ditemukan. Mencoba folder data...")
    except Exception as e:
        st.warning(f"⚠️ Error file lokal: {e}")
    
    # Step 3: Coba file di folder data
    try:
        with open(local_file_data, 'r') as f:
            data = json.load(f)
            st.success("✅ Data berhasil dimuat dari folder data!")
            return data
    except FileNotFoundError:
        st.error(f"❌ File tidak ditemukan di semua lokasi yang dicoba.")
    except Exception as e:
        st.error(f"❌ Error: {e}")
    
    # Step 4: Jika semua gagal, tampilkan panduan
    st.info("""
    **📌 Panduan Upload File:**
    
    1. **Jika menggunakan Streamlit Cloud:**
       - Upload file `grdp_full.json` ke repository GitHub Anda
       - Pastikan file berada di root folder atau folder `data/`
       
    2. **Jika menggunakan lokal:**
       - Letakkan file di folder yang sama dengan script ini
       
    3. **Atau upload manual:**
       - Gunakan sidebar di bawah untuk upload file JSON langsung
    """)
    
    # Tawarkan upload manual
    uploaded_file = st.file_uploader("Upload file grdp_full.json", type="json")
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            st.success("✅ Data berhasil diupload!")
            return data
        except Exception as e:
            st.error(f"Error membaca file upload: {e}")
    
    return {}

@st.cache_data
def load_province_mapping():
    """Mapping kode dan nama provinsi"""
    return {
        1: "Aceh", 2: "Sumatra Utara", 3: "Sumatra Barat", 4: "Riau",
        5: "Jambi", 6: "Sumatra Selatan", 7: "Bengkulu", 8: "Lampung",
        9: "Kepulauan Bangka Belitung", 10: "Kepulauan Riau",
        11: "DKI Jakarta", 12: "Jawa Barat", 13: "Jawa Tengah",
        14: "DI Yogyakarta", 15: "Jawa Timur", 16: "Banten",
        17: "Bali", 18: "Nusa Tenggara Barat", 19: "Nusa Tenggara Timur",
        20: "Kalimantan Barat", 21: "Kalimantan Tengah",
        22: "Kalimantan Selatan", 23: "Kalimantan Timur",
        24: "Kalimantan Utara",
        25: "Sulawesi Utara", 26: "Sulawesi Tengah", 27: "Sulawesi Selatan",
        28: "Sulawesi Tenggara", 29: "Gorontalo", 30: "Sulawesi Barat",
        31: "Maluku", 32: "Maluku Utara",
        33: "Papua Barat", 34: "Papua Barat Daya",
        35: "Papua", 36: "Papua Selatan",
        37: "Papua Tengah", 38: "Papua Pegunungan"
    }

# Komponen PDRB menurut pengeluaran
COMPONENTS = {
    1: "Konsumsi Rumah Tangga (PKRT)",
    2: "Konsumsi LNPRT (PK-LNPRT)",
    3: "Konsumsi Pemerintah (PK-P)",
    4: "Pembentukan Modal Tetap Bruto (PMTB)",
    5: "Perubahan Inventori",
    6: "Ekspor Luar Negeri",
    7: "Impor Luar Negeri",
    8: "Ekspor Neto (Net Exports)",
    9: "Total PDRB"
}

# Fungsi analisis ekonomi regional
def calculate_infrastructure_multiplier(pmtb, grdp_total, sector="Infrastruktur"):
    """
    Menghitung multiplier effect infrastruktur menggunakan pendekatan sederhana
    berdasarkan rasio PMTB terhadap Total GRDP
    
    Dalam analisis input-output yang lengkap, multiplier dihitung dari:
    - Output Multiplier: efek langsung + tidak langsung + induksi
    - Employment Multiplier: dampak terhadap penyerapan tenaga kerja
    - Income Multiplier: dampak terhadap pendapatan rumah tangga
    """
    if grdp_total == 0:
        return 0
    
    # Rasio investasi infrastruktur (asumsi 40% dari PMTB adalah infrastruktur)
    infrastructure_share = 0.40
    infrastructure_investment = pmtb * infrastructure_share
    
    # Infrastructure multiplier berdasarkan literatur regional economics
    # Untuk Indonesia, infrastruktur multiplier berkisar 1.5 - 2.5
    # tergantung pada tingkat perkembangan wilayah
    base_multiplier = 1.8
    
    # Adjust multiplier berdasarkan rasio investasi terhadap GRDP
    investment_ratio = pmtb / grdp_total
    if investment_ratio > 0.3:
        multiplier = base_multiplier + 0.3  # Wilayah dengan investasi tinggi
    elif investment_ratio > 0.2:
        multiplier = base_multiplier + 0.15
    elif investment_ratio > 0.15:
        multiplier = base_multiplier
    else:
        multiplier = base_multiplier - 0.2  # Wilayah dengan investasi rendah
    
    return multiplier, infrastructure_investment

def calculate_economic_impact(province_data, province_name):
    """
    Menghitung dampak ekonomi infrastruktur untuk suatu provinsi
    Menggunakan pendekatan Keynesian multiplier dengan data aktual
    """
    results = {}
    
    for year, data in province_data.items():
        if province_name not in data:
            continue
            
        values = data[province_name]
        if len(values) < 9:
            continue
        
        # Ekstrak komponen
        pkrt = values[0]      # Konsumsi Rumah Tangga
        pk_lnpert = values[1]  # Konsumsi LNPRT
        pk_p = values[2]       # Konsumsi Pemerintah
        pmtb = values[3]       # PMTB (Investasi)
        inventori = values[4]  # Perubahan Inventori
        ekspor = values[5]     # Ekspor
        impor = values[6]      # Impor
        net_ekspor = values[7] # Ekspor Neto
        grdp_total = values[8] # Total GRDP
        
        # Hitung multiplier infrastruktur
        multiplier, infra_investment = calculate_infrastructure_multiplier(pmtb, grdp_total)
        
        # Hitung dampak ekonomi
        direct_impact = infra_investment
        indirect_impact = infra_investment * (multiplier - 1)
        total_impact = infra_investment * multiplier
        
        # Kontribusi terhadap pertumbuhan
        if grdp_total > 0:
            contribution_ratio = (infra_investment / grdp_total) * 100
        else:
            contribution_ratio = 0
        
        results[year] = {
            'province': province_name,
            'pmtb': pmtb,
            'grdp_total': grdp_total,
            'infrastructure_investment': infra_investment,
            'multiplier': multiplier,
            'direct_impact': direct_impact,
            'indirect_impact': indirect_impact,
            'total_impact': total_impact,
            'contribution_ratio': contribution_ratio,
            'contribution_pct': contribution_ratio,  # Alias untuk konsistensi
            'investment_ratio': (pmtb / grdp_total * 100) if grdp_total > 0 else 0,
            'consumption_ratio': ((pkrt + pk_lnpert) / grdp_total * 100) if grdp_total > 0 else 0,
            'consumption_rt_ratio': (pkrt / grdp_total * 100) if grdp_total > 0 else 0,
            'government_ratio': (pk_p / grdp_total * 100) if grdp_total > 0 else 0,
            'export_ratio': (ekspor / grdp_total * 100) if grdp_total > 0 else 0,
            'import_ratio': (abs(impor) / grdp_total * 100) if grdp_total > 0 else 0,
            'net_export_ratio': (net_ekspor / grdp_total * 100) if grdp_total > 0 else 0,
            'infra_invest': infra_investment,
            'total_impact_val': total_impact
        }
    
    return results

def create_impact_visualization(impact_data, province_name):
    """Membuat visualisasi dampak ekonomi infrastruktur"""
    
    if not impact_data:
        return None
    
    years = sorted(impact_data.keys())
    
    # Siapkan data untuk visualisasi
    df_impact = pd.DataFrame([
        {
            'Year': year,
            'Direct Impact': impact_data[year]['direct_impact'],
            'Indirect Impact': impact_data[year]['indirect_impact'],
            'Total Impact': impact_data[year]['total_impact'],
            'Multiplier': impact_data[year]['multiplier'],
            'Contribution %': impact_data[year]['contribution_ratio']
        }
        for year in years
    ])
    
    # Buat figure dengan multiple subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            'Dampak Ekonomi Infrastruktur (Triliun Rupiah)',
            'Infrastructure Multiplier Effect',
            'Kontribusi terhadap PDRB (%)',
            'Komposisi Permintaan Akhir (%)'
        ),
        specs=[[{"type": "bar"}, {"type": "scatter"}],
               [{"type": "bar"}, {"type": "pie"}]]
    )
    
    # Plot 1: Stacked bar chart untuk dampak langsung dan tidak langsung
    fig.add_trace(
        go.Bar(
            x=df_impact['Year'],
            y=df_impact['Direct Impact'],
            name='Dampak Langsung',
            marker_color='#1f77b4'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df_impact['Year'],
            y=df_impact['Indirect Impact'],
            name='Dampak Tidak Langsung',
            marker_color='#ff7f0e'
        ),
        row=1, col=1
    )
    
    # Plot 2: Line chart untuk multiplier
    fig.add_trace(
        go.Scatter(
            x=df_impact['Year'],
            y=df_impact['Multiplier'],
            mode='lines+markers',
            name='Multiplier',
            line=dict(color='#2ca02c', width=3),
            marker=dict(size=10)
        ),
        row=1, col=2
    )
    
    # Plot 3: Bar chart untuk kontribusi
    fig.add_trace(
        go.Bar(
            x=df_impact['Year'],
            y=df_impact['Contribution %'],
            name='Kontribusi %',
            marker_color='#d62728'
        ),
        row=2, col=1
    )
    
    # Plot 4: Pie chart untuk tahun terakhir
    latest_year = max(years)
    latest_data = impact_data[latest_year]
    
    fig.add_trace(
        go.Pie(
            labels=['Investasi Infrastruktur', 'Konsumsi RT', 'Konsumsi Pem.', 'Net Ekspor', 'Lainnya'],
            values=[
                latest_data['infrastructure_investment'],
                latest_data['grdp_total'] * latest_data['consumption_ratio'] / 100,
                latest_data['grdp_total'] * latest_data['government_ratio'] / 100,
                latest_data['grdp_total'] * latest_data['net_export_ratio'] / 100,
                latest_data['grdp_total'] * (100 - latest_data['contribution_ratio'] - 
                                            latest_data['consumption_ratio'] - 
                                            latest_data['government_ratio'] - 
                                            latest_data['net_export_ratio']) / 100
            ],
            marker_colors=['#9467bd', '#1f77b4', '#2ca02c', '#d62728', '#ff7f0e']
        ),
        row=2, col=2
    )
    
    fig.update_layout(
        height=800,
        showlegend=True,
        legend=dict(x=0, y=1.1, orientation='h'),
        title_text=f"<b>Analisis Dampak Infrastruktur: {province_name}</b>",
        title_font_size=20
    )
    
    fig.update_xaxes(title_text="Tahun", row=1, col=1)
    fig.update_xaxes(title_text="Tahun", row=1, col=2)
    fig.update_xaxes(title_text="Tahun", row=2, col=1)
    fig.update_yaxes(title_text="Triliun Rupiah", row=1, col=1)
    fig.update_yaxes(title_text="Multiplier Value", row=1, col=2)
    fig.update_yaxes(title_text="Persen (%)", row=2, col=1)
    
    return fig

def create_comparison_chart(all_impact_data, metric='total_impact'):
    """Membuat chart perbandingan antar provinsi"""
    
    provinces = list(all_impact_data.keys())
    years = set()
    
    for prov_data in all_impact_data.values():
        years.update(prov_data.keys())
    
    latest_year = max(years)
    
    # Ambil data tahun terbaru
    comparison_data = []
    for province, impact_data in all_impact_data.items():
        if latest_year in impact_data:
            comparison_data.append({
                'Province': province,
                'Total Impact': impact_data[latest_year]['total_impact'],
                'Multiplier': impact_data[latest_year]['multiplier'],
                'Contribution %': impact_data[latest_year]['contribution_ratio']
            })
    
    df_compare = pd.DataFrame(comparison_data).sort_values('Total Impact', ascending=False)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df_compare['Total Impact'],
        y=df_compare['Province'],
        orientation='h',
        marker=dict(
            color=df_compare['Total Impact'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Triliun Rp")
        ),
        hovertemplate='<b>%{y}</b><br>Dampak: Rp %{x:.2f} T<br><extra></extra>'
    ))
    
    fig.update_layout(
        title=f"<b>Perbandingan Dampak Infrastruktur Antar Provinsi ({latest_year})</b>",
        xaxis_title="Total Dampak Ekonomi (Triliun Rupiah)",
        yaxis_title="Provinsi",
        height=600,
        showlegend=False
    )
    
    return fig


def generate_policy_recommendations(impact_data, province_name):
    """
    Menghasilkan 10 rekomendasi kebijakan spesifik berbasis data dan industri unggulan daerah.
    Menggunakan logika Regional Economist untuk analisis struktural mendetail.
    """
    if not impact_data:
        return None
    
    # Ambil data tahun terbaru
    latest_year = max(impact_data.keys())
    data = impact_data[latest_year]
    
    # Ekstrak rasio kunci
    invest_ratio = data['investment_ratio']
    consume_ratio = data['consumption_ratio']
    consume_rt_ratio = data.get('consumption_rt_ratio', consume_ratio * 0.85)
    gov_ratio = data['government_ratio']
    export_ratio = data['export_ratio']
    import_ratio = data['import_ratio']
    net_export_ratio = data['net_export_ratio']
    multiplier = data['multiplier']
    infra_invest = data.get('infra_invest', data.get('infrastructure_investment', 0))
    total_impact = data.get('total_impact_val', data.get('total_impact', 0))
    contribution_pct = data.get('contribution_pct', data.get('contribution_ratio', 0))
    
    # --- DETEKSI INDUSTRI UNGGULAN BERDASARKAN DATA ---
    dominant_sector = ""
    sector_keywords = {
        "Maluku": "Nikel", "Sulawesi": "Nikel", "Tenggara": "Nikel",
        "Kalimantan": "Batubara & CPO", "Riau": "Kelapa Sawit & Kertas",
        "Sumatera": "Kelapa Sawit & Karet", "Papua": "Tembaga & Emas",
        "Bali": "Pariwisata", "DKI Jakarta": "Jasa Keuangan & Perdagangan",
        "Jawa Barat": "Manufaktur Tekstil & Otomotif", "Jawa Timur": "Manufaktur & Agroindustri",
        "Banten": "Manufaktur & Logistik", "Jawa Tengah": "Manufaktur & Pertanian",
        "Kepulauan": "Perikanan & Kelautan", "Nusa Tenggara": "Pertanian & Pariwisata"
    }
    
    for keyword, sector in sector_keywords.items():
        if keyword in province_name:
            dominant_sector = sector
            break
    
    if not dominant_sector:
        if export_ratio > 30:
            dominant_sector = "Komoditas Ekspor Primer"
        elif invest_ratio > 35:
            dominant_sector = "Konstruksi & Infrastruktur"
        elif consume_ratio > 55:
            dominant_sector = "Perdagangan & Jasa Konsumen"
        else:
            dominant_sector = "Ekonomi Diversifikasi"
    
    # --- 1. DIAGNOSIS STRUKTUR EKONOMI (DETAILED) ---
    eco_type = ""
    structure_narrative = []
    
    if invest_ratio > 35:
        eco_type = "Investment-Led Growth"
        structure_narrative.append(f"**PMTB sangat tinggi ({invest_ratio:.1f}%)** → Ekonomi didorong oleh investasi besar-besaran. Ini tipikal daerah yang sedang mengalami *boom* pembangunan infrastruktur atau ekspansi sektor ekstraktif (pertambangan/smelting).")
        structure_narrative.append(f"**Konsumsi RT hanya {consume_rt_ratio:.1f}%** → Ekonomi TIDAK konsumtif. Ini struktur yang sehat untuk daerah berkembang karena menunjukkan diversifikasi ekonomi ke arah produksi, bukan sekadar konsumsi.")
        structure_narrative.append(f"**Insight:** {province_name} sedang dalam fase akselerasi pembentukan modal. Investasi ini kemungkinan besar terkait dengan pengembangan industri {dominant_sector} dan infrastruktur pendukungnya.")
    elif consume_ratio > 55:
        eco_type = "Consumption-Driven"
        structure_narrative.append(f"**Dominasi Konsumsi ({consume_ratio:.1f}%)** → Ekonomi sangat bergantung pada daya beli masyarakat. Pertumbuhan cenderung stabil namun kurang transformasional tanpa dorongan investasi.")
        structure_narrative.append(f"**PMTB rendah ({invest_ratio:.1f}%)** → Kapasitas produksi masa depan belum terbangun optimal. Risiko ketergantungan pada pasokan barang dari luar daerah.")
        structure_narrative.append(f"**Insight:** Perlu stimulus investasi untuk mengubah pola konsumsi menjadi produktif (UMKM, manufaktur lokal).")
    elif export_ratio > 30 and net_export_ratio > 0:
        eco_type = "Export-Oriented"
        structure_narrative.append(f"**Ekspor Besar ({export_ratio:.1f}%)** → Sektor eksternal adalah motor utama pertumbuhan.")
        structure_narrative.append(f"**Surplus Neraca ({net_export_ratio:.1f}%)** → Daya saing produk daerah kuat di pasar global.")
        structure_narrative.append(f"**Insight:** Daerah ini adalah basis produksi {dominant_sector} untuk pasar global. Tantangannya adalah memastikan nilai tambah dinikmati lokal (hilirisasi).")
    else:
        eco_type = "Transitional / Mixed Economy"
        structure_narrative.append(f"**Struktur Seimbang:** Belum ada satu komponen yang mendominasi ekstrem. Ekonomi dalam fase transisi.")
        if net_export_ratio < 0:
            structure_narrative.append(f"**Defisit Neto ({net_export_ratio:.1f}%)** → Ketergantungan input luar masih tinggi.")

    # --- 2. ANALISIS KETERBUKAAN (EKSPOR-IMPOR) - DETAILED ---
    trade_narrative = []
    if export_ratio > 50 or import_ratio > 30:
        trade_narrative.append(f"**Ekspor sangat besar ({export_ratio:.1f}% dari PDRB!)** → Sektor eksternal adalah motor utama.")
        trade_narrative.append(f"**Impor juga besar ({import_ratio:.1f}%)** → Ketergantungan pada barang modal dan input produksi dari luar.")
        
        if net_export_ratio < -20:
            trade_narrative.append(f"**Net Ekspor NEGATIF ({net_export_ratio:.1f}%)** → Meskipun ekspor besar, nilai impor lebih besar lagi dalam perhitungan neraca regional.")
            trade_narrative.append(f"**Insight Krusial:** Ini adalah karakteristik daerah *resource-based economy* yang sedang berkembang:")
            trade_narrative.append(f"   • Ekspor didominasi komoditas {dominant_sector} mentah/setengah jadi.")
            trade_narrative.append(f"   • Impor terdiri dari mesin, alat berat, bahan baku pendukung, dan barang konsumsi untuk pekerja migran.")
            trade_narrative.append(f"   • {province_name} berfungsi sebagai 'pabrik' {dominant_sector} untuk pasar global, bukan untuk konsumsi domestik.")
        elif net_export_ratio > 10:
            trade_narrative.append(f"**Surplus Kuat:** Menunjukkan nilai tambah {dominant_sector} yang berhasil ditahan di daerah atau basis sumber daya alam yang sangat efisien.")
    else:
        trade_narrative.append(f"**Keterbukaan Moderat:** Ekspor ({export_ratio:.1f}%) dan Impor ({import_ratio:.1f}%) dalam batas wajar. Ekonomi lebih berorientasi domestik.")

    # --- 3. DAMPAK INFRASTRUKTUR - DETAILED ---
    impact_narrative = []
    impact_narrative.append(f"**Estimasi Investasi Infrastruktur:** Rp {infra_invest:,.0f} Juta (40% dari PMTB)")
    impact_narrative.append(f"**Total Dampak Ekonomi (Multiplier {multiplier:.1f}x):** Rp {total_impact:,.0f} Juta")
    impact_narrative.append(f"**Kontribusi terhadap PDRB:** {contribution_pct:.2f}% → {'Sangat Signifikan!' if contribution_pct > 20 else 'Signifikan' if contribution_pct > 10 else 'Moderat'}")
    impact_narrative.append(f"**Artinya:** Setiap Rp 1 triliun investasi infrastruktur menghasilkan Rp {multiplier:.2f} triliun dampak ekonomi total bagi {province_name}.")

    full_interpretation = {
        "structure": "\n".join([f"1. STRUKTUR EKONOMI: {eco_type}"] + structure_narrative),
        "trade": "\n".join(["2. KETERBUKAAN EKONOMI: " + ("Paradoks Ekspor-Impor" if net_export_ratio < -20 else "Kekuatan Ekspor" if net_export_ratio > 10 else "Keterbukaan Moderat")] + trade_narrative),
        "impact": "\n".join(["3. DAMPAK INFRASTRUKTUR"] + impact_narrative)
    }
    
    # --- 10 REKOMENDASI KEBIJAKAN SPESIFIK BERBASIS INDUSTRI DAERAH ---
    policies = []
    
    # 1. Infrastruktur Logistik Spesifik
    policies.append({
        "priority": "PRIORITAS 1: INFRASTRUKTUR LOGISTIK INDUSTRI",
        "desc": f"Fokus pada rantai pasok {dominant_sector}:",
        "actions": [
            f"• **Pelabuhan Khusus {dominant_sector}:** Bangun/upgrade dermaga laut dalam untuk efisiensi bongkar muat komoditas.",
            "• **Jalan Poros Industri:** Aspal jalan penghubung dari pusat produksi ke pelabuhan dengan spesifikasi jalan industri (kelas I).",
            "• **Cold Storage & Gudang:** Untuk komoditas perikanan/pertanian agar tidak rusak saat distribusi."
        ]
    })
    
    # 2. Energi Industri
    policies.append({
        "priority": "PRIORITAS 2: KEAMANAN ENERGI INDUSTRI",
        "desc": "Support operasional industri skala besar:",
        "actions": [
            "• **Pembangkit Listrik Dedicated:** Konstruksi PLTU/PLTG/PLTS khusus kawasan industri dengan tarif kompetitif.",
            "• **Jaringan Gas Bumi:** Pipanisasi gas untuk industri yang membutuhkan panas tinggi (smelter, keramik).",
            "• **Energi Terbarukan:** Manfaatkan potensi lokal (bayu, air, surya) untuk mengurangi biaya energi jangka panjang."
        ]
    })
    
    # 3. Hilirisasi (jika ekspor tinggi & net negatif)
    if export_ratio > 25 and net_export_ratio < 0:
        policies.append({
            "priority": "PRIORITAS 3: WAJAB HILIRISASI KOMODITAS",
            "desc": f"Tahan nilai tambah {dominant_sector} di daerah:",
            "actions": [
                f"• **Smelter/Refinery {dominant_sector}:** Wajibkan pengolahan minimal 50% sebelum ekspor. Berikan insentif pajak daerah.",
                "• **Kawasan Industri Hilir:** Sediakan lahan terintegrasi dengan fasilitas bersama (limbah, energi, pelabuhan).",
                "• **Larangan Ekspor Mentah:** Terapkan regulasi daerah progresif melarang ekspor bahan mentah dalam 3-5 tahun."
            ]
        })
    
    # 4. Substitusi Impor
    if import_ratio > 25 or net_export_ratio < -20:
        policies.append({
            "priority": "PRIORITAS 4: SUBSTITUSI IMPOR BERBASIS KLASTER",
            "desc": "Kurangi kebocoran ekonomi:",
            "actions": [
                "• **Industri Penunjang Lokal:** Identifikasi 5 komponen impor terbesar (semen, ban alat berat, bahan kimia) dan berikan hibah lahan.",
                "• **Program Kemitraan Wajib:** Investor besar wajib menyerap 30% suplai non-core dari UMKM lokal.",
                "• **Zona Ekonomi Khusus (KEK):** Dorong status KEK untuk menarik industri substitusi impor dengan fasilitas fiskal."
            ]
        })
    
    # 5. Stimulus UMKM (jika konsumsi tinggi)
    if consume_ratio > 50:
        policies.append({
            "priority": "PRIORITAS 5: REVOLUSI UMKM & DAYA BELI",
            "desc": "Ubah konsumsi menjadi produktivitas:",
            "actions": [
                "• **Belanja Pemerintah Lokal:** Wajibkan 40% APBD belanja produk UMKM daerah.",
                "• **Digitalisasi Pasar Tradisional:** Platform e-commerce khusus produk lokal dengan subsidi ongkir.",
                "• **Kredit Ultra Mikro:** Bunga 0% untuk pelaku usaha mikro dengan jaminan kelompok."
            ]
        })
    
    # 6. Human Capital Link-and-Match
    policies.append({
        "priority": "PRIORITAS 6: VOKASI SPESIFIK INDUSTRI",
        "desc": f"Siapkan SDM untuk industri {dominant_sector}:",
        "actions": [
            f"• **Kurikulum SMK Politeknik:** Fokus pada teknologi {dominant_sector}, operator alat berat, teknisi smelter.",
            "• **Magang Berbayar Wajib:** Perusahaan besar wajib menerima 10% tenaga kerja lokal sebagai magang berbayar.",
            "• **Beasiswa Ikatan Dinas:** Pemda biayai kuliah warga lokal dengan ikatan kerja di perusahaan daerah."
        ]
    })
    
    # 7. Integrasi Rantai Pasok Global
    policies.append({
        "priority": "PRIORITAS 7: SERTIFIKASI INTERNASIONAL UMKM",
        "desc": "Akses pasar global untuk UMKM:",
        "actions": [
            "• **Subsidi Sertifikasi:** ISO, HACCP, Organic untuk UMKM potensial ekspor.",
            "• **Trade Matching:** Fasilitasi pertemuan bisnis dengan buyer internasional melalui Kedutaan.",
            "• **Logistik Ekspor Bersama:** Konsolidasi pengiriman UMKM untuk tekan biaya freight."
        ]
    })
    
    # 8. Tata Ruang Koridor Ekonomi
    policies.append({
        "priority": "PRIORITAS 8: REVISI RDTR BERBASIS KORIDOR",
        "desc": "Optimalkan tata ruang:",
        "actions": [
            "• **Zona Industri Terintegrasi:** Tetapkan koridor dari tambang/pelabuhan ke kawasan pengolahan.",
            "• **Buffer Zone Lingkungan:** Zona penyangga antara industri dan pemukiman untuk minimalkan konflik sosial.",
            "• **Infrastruktur Multimoda:** Integrasi jalan-rel-pelabuhan dalam satu masterplan."
        ]
    })
    
    # 9. Infrastruktur Hijau
    policies.append({
        "priority": "PRIORITAS 9: REKLAMASI & LINGKUNGAN WAJIB",
        "desc": "Pembangunan berkelanjutan:",
        "actions": [
            "• **Dana Reklamasi Di Muka:** Wajib setor dana reklamasi sebelum operasi dimulai.",
            "• **AMDAL Ketat & Monitoring Real-time:** Sensor kualitas udara/air online di kawasan industri.",
            "• **Green Infrastructure:** Wajib 20% area hijau di setiap kawasan industri baru."
        ]
    })
    
    # 10. Diversifikasi Ekonomi
    if export_ratio > 40 or invest_ratio > 45:
        policies.append({
            "priority": "PRIORITAS 10: DIVERSIFIKASI EKONOMI JANGKA PANJANG",
            "desc": "Hindari ketergantungan satu sektor:",
            "actions": [
                f"• **Pengembangan Sektor Sekunder:** Tourism, ekonomi kreatif, jasa pendidikan/kesehatan sebagai alternatif {dominant_sector}.",
                "• **Dana Abadi Daerah:** Alokasikan 5% revenue komoditas untuk dana abadi pembangunan sektor non-migas.",
                "• **Startup Ecosystem:** Inkubasi startup teknologi untuk solusi lokal."
            ]
        })

    # --- ANALISIS RISIKO DENGAN WARNA DIPERBAIKI ---
    risks = []
    if net_export_ratio < -50:
        risks.append({
            "level": "CRITICAL",
            "msg": f"**Kerentanan Nilai Tukar & Global:** Defisit neraca yang sangat dalam ({net_export_ratio:.1f}%) membuat ekonomi daerah sangat sensitif terhadap fluktuasi kurs rupiah dan harga komoditas global."
        })
    if invest_ratio > 45:
        risks.append({
            "level": "HIGH",
            "msg": f"**Risiko Over-Heating:** Investasi terlalu dominan ({invest_ratio:.1f}%) dapat memicu inflasi daerah (harga tanah, bahan bangunan, upah) jika tidak diimbangi peningkatan suplai barang/jasa."
        })
    if consume_ratio > 60:
        risks.append({
            "level": "MEDIUM",
            "msg": f"**Stagnasi Produktivitas:** Ketergantungan pada konsumsi ({consume_ratio:.1f}%) berisiko membuat ekonomi stagnan jika tidak ada injeksi teknologi/investasi baru."
        })
    if export_ratio > 50 and ("Maluku" in province_name or "Sulawesi" in province_name):
        risks.append({
            "level": "HIGH",
            "msg": f"**Monokultur Ekonomi ({dominant_sector}):** Ketergantungan ekstrem pada satu komoditas membuat daerah sangat rentan terhadap fluktuasi harga global dan kebijakan ekspor negara tujuan."
        })
    
    if not risks:
        risks.append({
            "level": "LOW",
            "msg": "Struktur ekonomi relatif seimbang. Fokus utama adalah menjaga stabilitas makro dan meningkatkan kualitas SDM serta infrastruktur dasar."
        })
    
    return {
        "year": latest_year,
        "eco_type": eco_type,
        "dominant_sector": dominant_sector,
        "interpretation": full_interpretation,
        "policies": policies,
        "risks": risks,
        "key_metrics": {
            "investment_ratio": invest_ratio,
            "consumption_ratio": consume_ratio,
            "net_export_ratio": net_export_ratio,
            "multiplier": multiplier
        }
    }

# Custom CSS tambahan untuk policy section
st.markdown("""
<style>
    .policy-box {
        background-color: #f0fdf4;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        border-left: 4px solid #22c55e;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .risk-box {
        background-color: #fef2f2;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        border-left: 4px solid #ef4444;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .diagnosis-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        margin-bottom: 20px;
    }
    .priority-high {
        background-color: #fee2e2;
        border-left-color: #ef4444 !important;
    }
    .priority-medium {
        background-color: #fef3c7;
        border-left-color: #f59e0b !important;
    }
</style>
""", unsafe_allow_html=True)

# Header aplikasi
st.markdown('<p class="main-header">🏛️ Regional Infrastructure Impact & Policy Advisor</p>', 
            unsafe_allow_html=True)

st.markdown("""
<div style='text-align: center; color: #666; margin-bottom: 2rem;'>
Platform analitik berbasis data BPS untuk mengukur multiplier effect investasi infrastruktur 
dan memberikan rekomendasi kebijakan berbasis evidence untuk pemerintah provinsi di Indonesia
</div>
""", unsafe_allow_html=True)

# Sidebar untuk input parameter
st.sidebar.header("⚙️ Parameter Analisis")

# Load data
grdp_data = load_grdp_data()
province_mapping = load_province_mapping()

# Load Input-Output analysis module
@st.cache_resource
def load_io_analyzer():
    """Load IO analyzer with caching"""
    return InputOutputAnalyzer()

io_analyzer = load_io_analyzer()
io_loaded = io_analyzer.load_table(2020)

if not grdp_data:
    st.error("Data tidak tersedia. Pastikan file grdp_full.json ada di workspace.")
    st.stop()

# Pilih provinsi
selected_province = st.sidebar.selectbox(
    "Pilih Provinsi:",
    options=list(grdp_data['2024'].keys()),
    index=list(grdp_data['2024'].keys()).index("DKI Jakarta") if "DKI Jakarta" in grdp_data['2024'] else 0
)

# Pilih tahun referensi
available_years = sorted(grdp_data.keys())
selected_year = st.sidebar.selectbox(
    "Tahun Referensi:",
    options=available_years,
    index=len(available_years) - 1
)

# Toggle untuk menampilkan detail metodologi
show_methodology = st.sidebar.checkbox("Tampilkan Metodologi", value=False)

if show_methodology:
    st.sidebar.info("""
    **Metodologi Analisis:**
    
    1. **Infrastructure Multiplier**: Dihitung berdasarkan rasio PMTB terhadap GRDP
       - Multiplier dasar: 1.8 (berdasarkan literatur)
       - Disesuaikan dengan intensitas investasi wilayah
    
    2. **Dampak Langsung**: Investasi infrastruktur langsung (40% dari PMTB)
    
    3. **Dampak Tidak Langsung**: Efek multiplier melalui rantai pasok
    
    4. **Policy Generator**: Rekomendasi otomatis berdasarkan struktur ekonomi
    
    5. **Input-Output Analysis**: Menggunakan Leontief Inverse Matrix
       - Technical coefficients matrix (A-matrix)
       - Output multipliers dari 35 sektor industri
       - Backward dan forward linkages analysis
    
    6. **Sumber Data**: 
       - BPS: PDRB Provinsi-Provinsi 2021-2025
       - BPS: Tabel Input-Output Indonesia 2020 (35 sektor)
       - BPS: Perdagangan Antar Wilayah 2024
    """)

# Toggle untuk menampilkan IO analysis
show_io_analysis = st.sidebar.checkbox("Tampilkan Analisis Input-Output", value=False)

if show_io_analysis and io_loaded:
    st.sidebar.success("✅ Tabel Input-Output 2020 berhasil dimuat")
    
    # Tampilkan ringkasan IO analysis di sidebar
    io_summary_col1, io_summary_col2 = st.columns(2)
    
    with io_summary_col1:
        st.subheader("🏭 Top 5 Sektor dengan Multiplier Tertinggi")
        top_sectors = io_analyzer.get_top_sectors_by_multiplier(5)
        for rank, (sector, mult) in enumerate(top_sectors, 1):
            st.metric(f"#{rank}", f"{mult:.3f}", sector)
    
    with io_summary_col2:
        st.subheader("📊 Statistik IO Table")
        st.metric("Total Output Nasional", f"${io_analyzer.data['total_output_sum']:,.0f} Juta USD")
        st.metric("Jumlah Sektor", len(io_analyzer.industry_names))
        
        # Linkage analysis untuk Construction
        construction_linkages = io_analyzer.get_sector_linkages('Construction')
        st.info(f"""
        **Konstruksi:**
        - Backward Linkage: {construction_linkages['backward_linkage']:.3f}
        - Forward Linkage: {construction_linkages['forward_linkage']:.3f}
        - {construction_linkages['interpretation']}
        """)

# Proses analisis
impact_results = calculate_economic_impact(grdp_data, selected_province)

if not impact_results:
    st.error(f"Tidak ada data untuk provinsi {selected_province}")
    st.stop()

# Generate policy recommendations
policy_rec = generate_policy_recommendations(impact_results, selected_province)

# Tabs untuk navigasi
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard Dampak", 
    "🧠 Interpretasi & Kebijakan",
    "📋 Breakdown Data",
    "🗺️ Komparasi Nasional"
])

with tab1:
    # Tampilkan metrik utama
    st.header(f"📍 {selected_province} ({selected_year})")
    
    if selected_year in impact_results:
        latest_data = impact_results[selected_year]
        
        # Kolom metrik
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Investasi Infrastruktur",
                value=f"Rp {latest_data['infrastructure_investment']:,.0f} M",
                delta=f"{latest_data['investment_ratio']:.1f}% dari PDRB"
            )
        
        with col2:
            st.metric(
                label="Total Dampak Ekonomi",
                value=f"Rp {latest_data['total_impact']:,.0f} M",
                delta=f"Multiplier: {latest_data['multiplier']:.2f}x"
            )
        
        with col3:
            st.metric(
                label="Dampak Tidak Langsung",
                value=f"Rp {latest_data['indirect_impact']:,.0f} M",
                delta=f"+{latest_data['indirect_impact']/latest_data['direct_impact']*100:.1f}% dari dampak langsung"
            )
        
        with col4:
            st.metric(
                label="Kontribusi ke PDRB",
                value=f"{latest_data['contribution_ratio']:.2f}%",
                delta=f"Total PDRB: Rp {latest_data['grdp_total']:,.0f} M"
            )
    
    # Visualisasi
    st.subheader("📊 Visualisasi Dampak Infrastruktur")
    
    fig_impact = create_impact_visualization(impact_results, selected_province)
    if fig_impact:
        st.plotly_chart(fig_impact, use_container_width=True)

with tab2:
    st.header(f"🧠 Analisis Kebijakan: {selected_province}")
    
    if policy_rec:
        # Tampilkan interpretasi mendetail (3 bagian)
        if 'interpretation' in policy_rec:
            interp = policy_rec['interpretation']
            
            # 1. Struktur Ekonomi
            st.subheader("🔍 Interpretasi Regional Economist")
            st.markdown(interp.get('structure', ''))
            st.markdown("---")
            
            # 2. Keterbukaan Ekonomi
            st.markdown(interp.get('trade', ''))
            st.markdown("---")
            
            # 3. Dampak Infrastruktur
            st.markdown(interp.get('impact', ''))
            st.markdown("---")
        
        # Key metrics summary
        km = policy_rec['key_metrics']
        st.subheader("📈 Indikator Kunci")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Rasio Investasi", f"{km['investment_ratio']:.1f}%")
        col_m2.metric("Rasio Konsumsi", f"{km['consumption_ratio']:.1f}%")
        col_m3.metric("Net Ekspor", f"{km['net_export_ratio']:.1f}%")
        col_m4.metric("Multiplier", f"{km['multiplier']:.2f}x")
        
        st.markdown("---")
        
        # Recommendations dengan format baru
        st.subheader("📋 Rekomendasi Policy (Top 0.000001% Economist View)")
        
        for policy in policy_rec['policies']:
            st.markdown(f"""
            <div class="policy-box">
                <h4 style="margin:0 0 8px 0; color:#1f2937;">{policy['priority']}</h4>
                <p style="color:#6b7280; margin:0 0 10px 0; font-style:italic;">{policy['desc']}</p>
                <ul style="margin:0; padding-left:20px; line-height:1.8;">
            """, unsafe_allow_html=True)
            
            for action in policy['actions']:
                st.markdown(f"<li>{action}</li>", unsafe_allow_html=True)
            
            st.markdown("</ul></div>", unsafe_allow_html=True)
        
        # Risks dengan styling warna yang diperbaiki
        if policy_rec['risks']:
            st.subheader("⚠️ Analisis Risiko")
            for risk in policy_rec['risks']:
                # Tentukan warna berdasarkan level risiko
                level = risk.get('level', 'MEDIUM') if isinstance(risk, dict) else 'MEDIUM'
                msg = risk['msg'] if isinstance(risk, dict) else str(risk)
                
                if level == 'CRITICAL':
                    bg_color = "#fef2f2"  # merah sangat muda
                    border_color = "#dc2626"  # merah tua
                    text_color = "#991b1b"  # merah gelap untuk teks
                elif level == 'HIGH':
                    bg_color = "#fff7ed"  # oranye sangat muda
                    border_color = "#ea580c"  # oranye tua
                    text_color = "#9a3412"  # oranye gelap untuk teks
                elif level == 'MEDIUM':
                    bg_color = "#fefce8"  # kuning sangat muda
                    border_color = "#ca8a04"  # kuning tua
                    text_color = "#854d0e"  # kuning gelap untuk teks
                else:  # LOW
                    bg_color = "#f0fdf4"  # hijau sangat muda
                    border_color = "#16a34a"  # hijau tua
                    text_color = "#166534"  # hijau gelap untuk teks
                
                st.markdown(f"""
                <div style="background-color: {bg_color}; border-radius: 8px; padding: 15px; margin-bottom: 12px; border-left: 4px solid {border_color}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <p style="color: {text_color}; margin: 0; font-weight: 500;">{msg}</p>
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Waterfall chart untuk multiplier effect
        st.subheader("📊 Decomposition Dampak Ekonomi")
        
        # Menggunakan approach bar chart biasa untuk kompatibilitas maksimal
        fig_wf = go.Figure()
        
        # Bar untuk investasi langsung
        fig_wf.add_trace(go.Bar(
            x=["Investasi Langsung"],
            y=[latest_data['infrastructure_investment']],
            marker_color="#3b82f6",
            text=[f"Rp {latest_data['infrastructure_investment']:,.0f} M"],
            textposition='outside',
            name='Investasi Langsung'
        ))
        
        # Bar untuk efek pengganda (stacked)
        fig_wf.add_trace(go.Bar(
            x=["Efek Pengganda"],
            y=[latest_data['indirect_impact']],
            marker_color="#22c55e",
            text=[f"+ Rp {latest_data['indirect_impact']:,.0f} M"],
            textposition='outside',
            name='Efek Pengganda'
        ))
        
        # Line untuk total
        fig_wf.add_trace(go.Scatter(
            x=["Total Dampak"],
            y=[latest_data['total_impact']],
            mode='markers+text',
            marker=dict(size=20, color="#1f2937"),
            text=[f"= Rp {latest_data['total_impact']:,.0f} M"],
            textposition='top center',
            name='Total Dampak',
            showlegend=False
        ))
        
        fig_wf.update_layout(
            title=f"Dekomposisi Dampak: Investasi → Multiplier → Total ({selected_year})",
            height=400,
            barmode='group',
            xaxis_title="Komponen",
            yaxis_title="Nilai (Juta Rupiah)",
            template="plotly_white"
        )
        st.plotly_chart(fig_wf, use_container_width=True)

with tab3:
    st.header("📋 Breakdown Komponen PDRB")
    
    if selected_year in grdp_data and selected_province in grdp_data[selected_year]:
        values = grdp_data[selected_year][selected_province]
        
        component_names = [
            "Konsumsi Rumah Tangga",
            "Konsumsi LNPRT",
            "Konsumsi Pemerintah",
            "PMTB (Investasi)",
            "Perubahan Inventori",
            "Ekspor",
            "Impor",
            "Ekspor Neto",
            "Total PDRB"
        ]
        
        df_components = pd.DataFrame({
            'Komponen': component_names,
            'Nilai (Miliar Rupiah)': values,
            'Persentase': [(v / values[8] * 100) if values[8] > 0 else 0 for v in values]
        })
        
        # Tampilkan tabel
        st.dataframe(
            df_components.style.format({
                'Nilai (Miliar Rupiah)': '{:,.2f}',
                'Persentase': '{:.2f}%'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # Chart pie untuk komposisi
        col_pie1, col_pie2 = st.columns(2)
        with col_pie1:
            fig_pie = px.pie(
                df_components.head(6),
                values='Nilai (Miliar Rupiah)',
                names='Komponen',
                title=f"Komposisi PDRB {selected_province} ({selected_year})",
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col_pie2:
            # Bar chart untuk persentase
            fig_bar = px.bar(
                df_components.head(6),
                x='Persentase',
                y='Komponen',
                orientation='h',
                title='Persentase Kontribusi terhadap PDRB',
                color='Persentase',
                color_continuous_scale='Blues'
            )
            fig_bar.update_layout(height=400)
            st.plotly_chart(fig_bar, use_container_width=True)

# Tab baru untuk Input-Output Analysis
tab5 = st.tabs(["📊 Dashboard Dampak", "🧠 Interpretasi & Kebijakan", "📋 Breakdown Data", "🗺️ Komparasi Nasional", "🏭 Analisis Input-Output"])[4]

with tab5:
    st.header("🏭 Analisis Input-Output Indonesia 2020")
    
    if io_loaded:
        st.markdown("""
        Analisis Input-Output menggunakan **Leontief Inverse Matrix** untuk mengukur multiplier effect 
        dari setiap sektor industri terhadap perekonomian nasional. Data dari BPS mencakup 35 sektor industri.
        """)
        
        # IO Analysis sections
        io_tab1, io_tab2, io_tab3 = st.tabs(["Multiplier Sectors", "Impact Simulation", "Sector Linkages"])
        
        with io_tab1:
            st.subheader("📈 Output Multipliers per Sektor")
            
            # Get all multipliers
            multipliers_df = pd.DataFrame([
                {'Sector': sector, 'Output Multiplier': mult}
                for sector, mult in io_analyzer.get_output_multipliers().items()
            ]).sort_values('Output Multiplier', ascending=False)
            
            # Top 10 bar chart
            st.subheader("Top 10 Sektor dengan Multiplier Tertinggi")
            fig_top10 = px.bar(
                multipliers_df.head(10),
                x='Output Multiplier',
                y='Sector',
                orientation='h',
                title='Sektor dengan Efek Multiplier Terbesar',
                color='Output Multiplier',
                color_continuous_scale='Viridis'
            )
            fig_top10.update_layout(height=500)
            st.plotly_chart(fig_top10, use_container_width=True)
            
            # Full table
            st.subheader("Semua Sektor (35 Industri)")
            st.dataframe(
                multipliers_df.style.format({'Output Multiplier': '{:.4f}'}),
                use_container_width=True,
                hide_index=True
            )
            
            # Explanation
            st.info("""
            **Interpretasi Output Multiplier:**
            - Nilai > 2.0: Sektor dengan dampak ekonomi sangat tinggi
            - Nilai 1.5 - 2.0: Sektor dengan dampak ekonomi tinggi  
            - Nilai < 1.5: Sektor dengan dampak ekonomi moderat
            
            Contoh: Multiplier Konstruksi = 2.01 berarti setiap $1 investasi di konstruksi 
            menghasilkan $2.01 total output ekonomi (langsung + tidak langsung).
            """)
        
        with io_tab2:
            st.subheader("🔧 Simulasi Dampak Investasi")
            
            # Sector selection
            selected_io_sector = st.selectbox(
                "Pilih Sektor untuk Simulasi:",
                options=io_analyzer.industry_names,
                index=io_analyzer.industry_names.index('Construction') if 'Construction' in io_analyzer.industry_names else 0
            )
            
            investment_amount = st.slider(
                "Besaran Investasi (Juta USD):",
                min_value=100,
                max_value=10000,
                value=1000,
                step=100
            )
            
            if st.button("Hitung Dampak Ekonomi"):
                impact = io_analyzer.calculate_infrastructure_impact(investment_amount, selected_io_sector)
                
                if 'error' not in impact:
                    col_sim1, col_sim2, col_sim3 = st.columns(3)
                    
                    with col_sim1:
                        st.metric("Dampak Langsung", f"${impact['direct_impact']:,.0f} Juta")
                    with col_sim2:
                        st.metric("Dampak Tidak Langsung", f"${impact['indirect_impact']:,.0f} Juta")
                    with col_sim3:
                        st.metric("Total Dampak", f"${impact['total_impact']:,.0f} Juta")
                    
                    st.metric("Multiplier Effect", f"{impact['multiplier']:.4f}x")
                    
                    # Pie chart breakdown
                    fig_pie_impact = px.pie(
                        values=[impact['direct_impact'], impact['indirect_impact']],
                        names=['Dampak Langsung', 'Dampak Tidak Langsung'],
                        title=f'Distribusi Dampak Investasi ${investment_amount:,} Juta di {selected_io_sector}',
                        hole=0.4
                    )
                    st.plotly_chart(fig_pie_impact, use_container_width=True)
                    
                    # Top beneficiaries
                    st.subheader("🏆 5 Sektor Penerima Manfaat Terbesar")
                    top_benefits_df = pd.DataFrame(
                        impact['top_5_beneficiaries'],
                        columns=['Sektor', 'Dampak (Juta USD)']
                    )
                    st.dataframe(top_benefits_df.style.format({'Dampak (Juta USD)': '${:,.2f}'}), hide_index=True)
        
        with io_tab3:
            st.subheader("🔗 Analisis Linkages Antar Sektor")
            
            linkage_sector = st.selectbox(
                "Analisis Sektor:",
                options=io_analyzer.industry_names,
                index=io_analyzer.industry_names.index('Construction') if 'Construction' in io_analyzer.industry_names else 0,
                key='linkage_select'
            )
            
            linkages = io_analyzer.get_sector_linkages(linkage_sector)
            
            if linkages:
                col_l1, col_l2 = st.columns(2)
                
                with col_l1:
                    st.metric("Backward Linkage", f"{linkages['backward_linkage']:.4f}")
                    st.markdown(f"*Direct Input Coefficient:* {linkages['direct_input_coefficient']:.4f}")
                
                with col_l2:
                    st.metric("Forward Linkage", f"{linkages['forward_linkage']:.4f}")
                    st.markdown(f"*Direct Sales Coefficient:* {linkages['direct_sales_coefficient']:.4f}")
                
                st.success(f"**Interpretasi:** {linkages['interpretation']}")
                
                # Radar chart for linkages
                fig_radar = go.Figure()
                
                fig_radar.add_trace(go.Scatterpolar(
                    r=[linkages['backward_linkage'], linkages['forward_linkage'], 
                       linkages['direct_input_coefficient'], linkages['direct_sales_coefficient']],
                    theta=['Backward Linkage', 'Forward Linkage', 
                           'Direct Input', 'Direct Sales'],
                    fill='toself',
                    name=linkage_sector
                ))
                
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True)),
                    showlegend=False,
                    title=f"Radar Chart Linkages: {linkage_sector}"
                )
                
                st.plotly_chart(fig_radar, use_container_width=True)
                
                st.info("""
                **Penjelasan Linkages:**
                - **Backward Linkage**: Kekuatan keterkaitan dengan sektor hulu (pemasok)
                - **Forward Linkage**: Kekuatan keterkaitan dengan sektor hilir (pembeli)
                - Sektor dengan backward linkage tinggi mendorong pertumbuhan sektor pemasok
                - Sektor dengan forward linkage tinggi memungkinkan aktivitas sektor downstream
                """)
    else:
        st.error("Gagal memuat Tabel Input-Output. Pastikan file excel tersedia.")

with tab4:
    st.header("🗺️ Perbandingan Antar Provinsi")
    
    all_provinces_impact = {}
    for province in grdp_data['2024'].keys():
        impact = calculate_economic_impact(grdp_data, province)
        if impact:
            all_provinces_impact[province] = impact
    
    fig_compare = create_comparison_chart(all_provinces_impact)
    st.plotly_chart(fig_compare, use_container_width=True)
    
    # Analisis tren
    st.subheader("📈 Tren Pertumbuhan Dampak Infrastruktur")
    
    # Pilih beberapa provinsi untuk dibandingkan
    comparison_provinces = st.multiselect(
        "Pilih provinsi untuk dibandingkan:",
        options=list(all_provinces_impact.keys()),
        default=["DKI Jakarta", "Jawa Barat", "Jawa Timur"] if len(all_provinces_impact) >= 3 else list(all_provinces_impact.keys())[:3],
        max_selections=5
    )
    
    if comparison_provinces:
        trend_data = []
        for province in comparison_provinces:
            if province in all_provinces_impact:
                for year, data in all_provinces_impact[province].items():
                    trend_data.append({
                        'Year': int(year),
                        'Province': province,
                        'Total Impact': data['total_impact'],
                        'Multiplier': data['multiplier']
                    })
        
        df_trend = pd.DataFrame(trend_data)
        
        fig_trend = px.line(
            df_trend,
            x='Year',
            y='Total Impact',
            color='Province',
            markers=True,
            title='Tren Dampak Ekonomi Infrastruktur Antar Provinsi',
            labels={'Year': 'Tahun', 'Total Impact': 'Total Dampak (Triliun Rupiah)'}
        )
        
        fig_trend.update_traces(line=dict(width=3))
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # Trend multiplier
        st.subheader("📊 Perbandingan Multiplier Effect")
        fig_mult = px.line(
            df_trend,
            x='Year',
            y='Multiplier',
            color='Province',
            markers=True,
            title='Tren Infrastructure Multiplier Antar Provinsi',
            labels={'Year': 'Tahun', 'Multiplier': 'Nilai Multiplier'}
        )
        fig_mult.add_hline(y=1.8, line_dash="dash", line_color="gray", annotation_text="Baseline Multiplier (1.8x)")
        st.plotly_chart(fig_mult, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9rem;'>
    <b>Sumber Data:</b> Badan Pusat Statistik (BPS) Indonesia<br>
    Publikasi: Produk Domestik Regional Bruto Provinsi-Provinsi di Indonesia Menurut Pengeluaran 2021-2025<br>
    <i>Dikembangkan dengan metodologi Regional Economic Impact Analysis & Policy Advisory System</i>
</div>
""", unsafe_allow_html=True)
