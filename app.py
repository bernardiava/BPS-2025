"""
Aplikasi Streamlit untuk Analisis Dampak Infrastruktur terhadap Ekonomi Regional
Data sumber: Badan Pusat Statistik (BPS) Indonesia
- Produk Domestik Regional Bruto Provinsi-Provinsi di Indonesia Menurut Pengeluaran 2021-2025
- Tabel Input-Output Indonesia 2020
- Perdagangan Antar Wilayah Indonesia 2024

Metodologi: Regional Economic Impact Analysis dengan pendekatan multiplier effect
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os

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
            'investment_ratio': (pmtb / grdp_total * 100) if grdp_total > 0 else 0,
            'consumption_ratio': ((pkrt + pk_lnpert) / grdp_total * 100) if grdp_total > 0 else 0,
            'government_ratio': (pk_p / grdp_total * 100) if grdp_total > 0 else 0,
            'net_export_ratio': (net_ekspor / grdp_total * 100) if grdp_total > 0 else 0
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
    Menghasilkan interpretasi ekonomi dan rekomendasi kebijakan berbasis data
    Menggunakan logika Regional Economist untuk analisis struktural
    """
    if not impact_data:
        return None
    
    # Ambil data tahun terbaru
    latest_year = max(impact_data.keys())
    data = impact_data[latest_year]
    
    # Ekstrak rasio kunci
    invest_ratio = data['investment_ratio']
    consume_ratio = data['consumption_ratio']
    gov_ratio = data['government_ratio']
    net_export_ratio = data['net_export_ratio']
    multiplier = data['multiplier']
    
    # --- DIAGNOSIS TIPE EKONOMI ---
    if invest_ratio > 35:
        eco_type = "Investment-Driven Economy"
        eco_desc = f"Ekonomi {province_name} didorong oleh investasi tinggi ({invest_ratio:.1f}% PDRB). Ini mengindikasikan fase akselerasi pembangunan infrastruktur atau ekspansi sektor ekstraktif/manufaktur."
    elif consume_ratio > 55:
        eco_type = "Consumption-Driven Economy"
        eco_desc = f"Ekonomi {province_name} didominasi konsumsi rumah tangga ({consume_ratio:.1f}% PDRB). Ini menunjukkan pasar domestik yang kuat namun berpotensi bergantung pada impor."
    elif net_export_ratio > 15:
        eco_type = "Export-Oriented Economy"
        eco_desc = f"Ekonomi {province_name} berorientasi ekspor dengan surplus neraca perdagangan yang kuat ({net_export_ratio:.1f}% PDRB)."
    elif net_export_ratio < -15:
        eco_type = "Import-Dependent Economy"
        eco_desc = f"Ekonomi {province_name} mengalami defisit neraca perdagangan yang signifikan ({net_export_ratio:.1f}% PDRB), mengindikasikan ketergantungan tinggi pada barang modal/impor."
    else:
        eco_type = "Balanced Mixed Economy"
        eco_desc = f"Ekonomi {province_name} menunjukkan keseimbangan antara konsumsi, investasi, dan perdagangan eksternal."
    
    # --- REKOMENDASI KEBIJAKAN ---
    policies = []
    risks = []
    
    # Kebijakan berdasarkan investasi
    if invest_ratio > 40:
        policies.append({
            "priority": "HIGH",
            "category": "Investasi",
            "recommendation": "Optimalisasi Iklim Investasi & Linkage Industry",
            "detail": "Permudah perizinan proyek strategis dan dorong penggunaan material lokal (TKDN) untuk memaksimalkan multiplier effect di daerah."
        })
        risks.append("Risiko Over-Heating: Waspadai inflasi daerah akibat permintaan agregat terlalu tinggi.")
    elif invest_ratio < 20:
        policies.append({
            "priority": "HIGH",
            "category": "Investasi",
            "recommendation": "Percepatan Belanja Modal Infrastruktur",
            "detail": "Tingkatkan alokasi APBD untuk infrastruktur dasar (jalan, irigasi, listrik) guna mendorong pertumbuhan ekonomi jangka panjang."
        })
    
    # Kebijakan berdasarkan konsumsi
    if consume_ratio > 60:
        policies.append({
            "priority": "MEDIUM",
            "category": "Konsumsi",
            "recommendation": "Stimulus UMKM & Digitalisasi Pasar",
            "detail": "Fokus pada penguatan rantai pasok lokal dan perluasan akses pasar digital agar konsumsi menyerap produk dalam negeri, bukan impor."
        })
        risks.append("Ketergantungan Impor: Konsumsi tinggi tanpa produksi lokal akan memperlebar defisit transaksi berjalan.")
    
    # Kebijakan berdasarkan neraca perdagangan
    if net_export_ratio < -20:
        policies.append({
            "priority": "HIGH",
            "category": "Perdagangan",
            "recommendation": "Substitusi Impor & Hilirisasi",
            "detail": "Identifikasi komoditas impor terbesar dan berikan insentif produksi dalam negeri. Wajibkan pengolahan bahan mentah di daerah sebelum diekspor."
        })
        risks.append("Kerentanan Nilai Tukar: Fluktuasi kurs dapat mengguncang biaya produksi dan daya beli masyarakat.")
    elif net_export_ratio > 20:
        policies.append({
            "priority": "MEDIUM",
            "category": "Perdagangan",
            "recommendation": "Diversifikasi Pasar Ekspor",
            "detail": "Kurangi ketergantungan pada satu negara tujuan ekspor dan kembangkan produk bernilai tambah tinggi."
        })
    
    # Kebijakan berdasarkan multiplier
    if multiplier > 2.0:
        policies.append({
            "priority": "MEDIUM",
            "category": "Efisiensi",
            "recommendation": "Pertahankan Momentum Pembangunan",
            "detail": f"Dengan multiplier {multiplier:.2f}x, efektivitas investasi infrastruktur sangat tinggi. Lanjutkan proyek prioritas dengan monitoring ketat."
        })
    else:
        policies.append({
            "priority": "MEDIUM",
            "category": "Efisiensi",
            "recommendation": "Peningkatan Kualitas Belanja Infrastruktur",
            "detail": f"Multiplier {multiplier:.2f}x masih dapat ditingkatkan. Fokus pada infrastruktur produktif yang terhubung dengan pusat ekonomi."
        })
    
    # Jika tidak ada risiko spesifik
    if not risks:
        risks.append("Stabilitas makroekonomi relatif terjaga. Pertahankan kebijakan saat ini dengan monitoring rutin.")
    
    return {
        "year": latest_year,
        "eco_type": eco_type,
        "eco_description": eco_desc,
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
    
    5. **Sumber Data**: 
       - BPS: PDRB Provinsi-Provinsi 2021-2025
       - BPS: Tabel Input-Output 2020
       - BPS: Perdagangan Antar Wilayah 2024
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
        # Diagnosis box
        st.markdown(f"""
        <div class="diagnosis-box">
            <h3 style="margin:0; color:white;">🔍 Diagnosis Struktur Ekonomi</h3>
            <h4 style="margin:5px 0 15px 0; color:#fbbf24;">{policy_rec['eco_type']}</h4>
            <p style="margin:0; line-height:1.6;">{policy_rec['eco_description']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Key metrics summary
        km = policy_rec['key_metrics']
        st.subheader("📈 Indikator Kunci")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Rasio Investasi", f"{km['investment_ratio']:.1f}%")
        col_m2.metric("Rasio Konsumsi", f"{km['consumption_ratio']:.1f}%")
        col_m3.metric("Net Ekspor", f"{km['net_export_ratio']:.1f}%")
        col_m4.metric("Multiplier", f"{km['multiplier']:.2f}x")
        
        st.markdown("---")
        
        # Recommendations
        st.subheader("💡 Rekomendasi Kebijakan")
        
        for policy in policy_rec['policies']:
            priority_class = "priority-high" if policy['priority'] == "HIGH" else "priority-medium"
            st.markdown(f"""
            <div class="policy-box {priority_class}">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-weight:bold; color:#1f2937; font-size:1.1rem;">
                        {policy['category']}: {policy['recommendation']}
                    </span>
                    <span style="background-color:{'#ef4444' if policy['priority']=='HIGH' else '#f59e0b'}; 
                                color:white; padding:4px 12px; border-radius:20px; font-size:0.8rem; font-weight:bold;">
                        {policy['priority']} PRIORITY
                    </span>
                </div>
                <p style="color:#4b5563; margin:0; line-height:1.6;">{policy['detail']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Risks
        st.subheader("⚠️ Analisis Risiko")
        for risk in policy_rec['risks']:
            st.markdown(f"""
            <div class="risk-box">
                <p style="color:#7f1d1d; margin:0; line-height:1.6;">{risk}</p>
            </div>
            """, unsafe_allow_html=True)
        
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
