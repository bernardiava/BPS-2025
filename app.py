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

@st.cache_data
def load_grdp_data():
    """Load GRDP data dari file JSON dengan multiple fallback options"""
    github_url = 'https://raw.githubusercontent.com/bernardiava/BPS-2025/main/grdp_full.json'
    local_file = 'grdp_full.json'
    local_file_data = 'data/grdp_full.json'

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

    # Try local file paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for path in [os.path.join(script_dir, local_file), local_file, local_file_data]:
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                st.success(f"✅ Data berhasil dimuat dari: {path}")
                return data
        except FileNotFoundError:
            continue
        except Exception as e:
            st.warning(f"⚠️ Error membaca {path}: {e}")

    st.error("❌ File tidak ditemukan di semua lokasi yang dicoba.")
    st.info("""
    **📌 Panduan Upload File:**
    1. Upload file `grdp_full.json` ke repository GitHub Anda
    2. Atau letakkan file di folder yang sama dengan script ini
    """)

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

def calculate_infrastructure_multiplier(pmtb, grdp_total, sector="Infrastruktur"):
    if grdp_total == 0:
        return 0
    infrastructure_share = 0.40
    infrastructure_investment = pmtb * infrastructure_share
    base_multiplier = 1.8
    investment_ratio = pmtb / grdp_total
    if investment_ratio > 0.3:
        multiplier = base_multiplier + 0.3
    elif investment_ratio > 0.2:
        multiplier = base_multiplier + 0.15
    elif investment_ratio > 0.15:
        multiplier = base_multiplier
    else:
        multiplier = base_multiplier - 0.2
    return multiplier, infrastructure_investment

def calculate_economic_impact(province_data, province_name):
    results = {}
    for year, data in province_data.items():
        if province_name not in data:
            continue
        values = data[province_name]
        if len(values) < 9:
            continue
        pkrt = values[0]
        pk_lnpert = values[1]
        pk_p = values[2]
        pmtb = values[3]
        inventori = values[4]
        ekspor = values[5]
        impor = values[6]
        net_ekspor = values[7]
        grdp_total = values[8]
        multiplier, infra_investment = calculate_infrastructure_multiplier(pmtb, grdp_total)
        direct_impact = infra_investment
        indirect_impact = infra_investment * (multiplier - 1)
        total_impact = infra_investment * multiplier
        contribution_ratio = (infra_investment / grdp_total) * 100 if grdp_total > 0 else 0
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
            'contribution_pct': contribution_ratio,
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
    if not impact_data:
        return None
    years = sorted(impact_data.keys())
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
    fig.add_trace(go.Bar(x=df_impact['Year'], y=df_impact['Direct Impact'],
                         name='Dampak Langsung', marker_color='#1f77b4'), row=1, col=1)
    fig.add_trace(go.Bar(x=df_impact['Year'], y=df_impact['Indirect Impact'],
                         name='Dampak Tidak Langsung', marker_color='#ff7f0e'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_impact['Year'], y=df_impact['Multiplier'],
                              mode='lines+markers', name='Multiplier',
                              line=dict(color='#2ca02c', width=3), marker=dict(size=10)), row=1, col=2)
    fig.add_trace(go.Bar(x=df_impact['Year'], y=df_impact['Contribution %'],
                         name='Kontribusi %', marker_color='#d62728'), row=2, col=1)
    latest_year = max(years)
    latest_data = impact_data[latest_year]
    fig.add_trace(go.Pie(
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
    ), row=2, col=2)
    fig.update_layout(height=800, showlegend=True, legend=dict(x=0, y=1.1, orientation='h'),
                      title_text=f"<b>Analisis Dampak Infrastruktur: {province_name}</b>", title_font_size=20)
    fig.update_xaxes(title_text="Tahun", row=1, col=1)
    fig.update_xaxes(title_text="Tahun", row=1, col=2)
    fig.update_xaxes(title_text="Tahun", row=2, col=1)
    fig.update_yaxes(title_text="Triliun Rupiah", row=1, col=1)
    fig.update_yaxes(title_text="Multiplier Value", row=1, col=2)
    fig.update_yaxes(title_text="Persen (%)", row=2, col=1)
    return fig

def create_comparison_chart(all_impact_data, metric='total_impact'):
    years = set()
    for prov_data in all_impact_data.values():
        years.update(prov_data.keys())
    latest_year = max(years)
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
        x=df_compare['Total Impact'], y=df_compare['Province'], orientation='h',
        marker=dict(color=df_compare['Total Impact'], colorscale='Viridis',
                    showscale=True, colorbar=dict(title="Triliun Rp")),
        hovertemplate='<b>%{y}</b><br>Dampak: Rp %{x:.2f} T<br><extra></extra>'
    ))
    fig.update_layout(
        title=f"<b>Perbandingan Dampak Infrastruktur Antar Provinsi ({latest_year})</b>",
        xaxis_title="Total Dampak Ekonomi (Triliun Rupiah)", yaxis_title="Provinsi",
        height=600, showlegend=False
    )
    return fig


def generate_policy_recommendations(impact_data, province_name):
    if not impact_data:
        return None
    latest_year = max(impact_data.keys())
    data = impact_data[latest_year]
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

    eco_type = ""
    structure_narrative = []
    if invest_ratio > 35:
        eco_type = "Investment-Led Growth"
        structure_narrative.append(f"**PMTB sangat tinggi ({invest_ratio:.1f}%)** → Ekonomi didorong oleh investasi besar-besaran.")
        structure_narrative.append(f"**Konsumsi RT hanya {consume_rt_ratio:.1f}%** → Ekonomi TIDAK konsumtif.")
        structure_narrative.append(f"**Insight:** {province_name} sedang dalam fase akselerasi pembentukan modal terkait {dominant_sector}.")
    elif consume_ratio > 55:
        eco_type = "Consumption-Driven"
        structure_narrative.append(f"**Dominasi Konsumsi ({consume_ratio:.1f}%)** → Ekonomi sangat bergantung pada daya beli masyarakat.")
        structure_narrative.append(f"**PMTB rendah ({invest_ratio:.1f}%)** → Kapasitas produksi masa depan belum terbangun optimal.")
        structure_narrative.append(f"**Insight:** Perlu stimulus investasi untuk mengubah pola konsumsi menjadi produktif.")
    elif export_ratio > 30 and net_export_ratio > 0:
        eco_type = "Export-Oriented"
        structure_narrative.append(f"**Ekspor Besar ({export_ratio:.1f}%)** → Sektor eksternal adalah motor utama pertumbuhan.")
        structure_narrative.append(f"**Surplus Neraca ({net_export_ratio:.1f}%)** → Daya saing produk daerah kuat di pasar global.")
        structure_narrative.append(f"**Insight:** Daerah ini adalah basis produksi {dominant_sector} untuk pasar global.")
    else:
        eco_type = "Transitional / Mixed Economy"
        structure_narrative.append(f"**Struktur Seimbang:** Ekonomi dalam fase transisi.")
        if net_export_ratio < 0:
            structure_narrative.append(f"**Defisit Neto ({net_export_ratio:.1f}%)** → Ketergantungan input luar masih tinggi.")

    trade_narrative = []
    if export_ratio > 50 or import_ratio > 30:
        trade_narrative.append(f"**Ekspor sangat besar ({export_ratio:.1f}% dari PDRB!)** → Sektor eksternal adalah motor utama.")
        trade_narrative.append(f"**Impor juga besar ({import_ratio:.1f}%)** → Ketergantungan pada barang modal dari luar.")
        if net_export_ratio < -20:
            trade_narrative.append(f"**Net Ekspor NEGATIF ({net_export_ratio:.1f}%)** → Karakteristik daerah resource-based economy.")
        elif net_export_ratio > 10:
            trade_narrative.append(f"**Surplus Kuat:** Nilai tambah {dominant_sector} berhasil ditahan di daerah.")
    else:
        trade_narrative.append(f"**Keterbukaan Moderat:** Ekspor ({export_ratio:.1f}%) dan Impor ({import_ratio:.1f}%) dalam batas wajar.")

    impact_narrative = []
    impact_narrative.append(f"**Estimasi Investasi Infrastruktur:** Rp {infra_invest:,.2f} Juta (40% dari PMTB)")
    impact_narrative.append(f"**Total Dampak Ekonomi (Multiplier {multiplier:.1f}x):** Rp {total_impact:,.2f} Juta")
    impact_narrative.append(f"**Kontribusi terhadap PDRB:** {contribution_pct:.2f}%")
    impact_narrative.append(f"**Artinya:** Setiap Rp 1 triliun investasi menghasilkan Rp {multiplier:.2f} triliun dampak ekonomi total.")

    full_interpretation = {
        "structure": "\n".join([f"1. STRUKTUR EKONOMI: {eco_type}"] + structure_narrative),
        "trade": "\n".join(["2. KETERBUKAAN EKONOMI"] + trade_narrative),
        "impact": "\n".join(["3. DAMPAK INFRASTRUKTUR"] + impact_narrative)
    }

    policies = []
    policies.append({
        "priority": "PRIORITAS 1: INFRASTRUKTUR LOGISTIK INDUSTRI",
        "desc": f"Fokus pada rantai pasok {dominant_sector}:",
        "actions": [
            f"• **Pelabuhan Khusus {dominant_sector}:** Bangun/upgrade dermaga laut dalam untuk efisiensi bongkar muat komoditas.",
            "• **Jalan Poros Industri:** Aspal jalan penghubung dari pusat produksi ke pelabuhan dengan spesifikasi kelas I.",
            "• **Cold Storage & Gudang:** Untuk komoditas perikanan/pertanian agar tidak rusak saat distribusi."
        ]
    })
    policies.append({
        "priority": "PRIORITAS 2: KEAMANAN ENERGI INDUSTRI",
        "desc": "Support operasional industri skala besar:",
        "actions": [
            "• **Pembangkit Listrik Dedicated:** Konstruksi PLTU/PLTG/PLTS khusus kawasan industri dengan tarif kompetitif.",
            "• **Jaringan Gas Bumi:** Pipanisasi gas untuk industri yang membutuhkan panas tinggi.",
            "• **Energi Terbarukan:** Manfaatkan potensi lokal (bayu, air, surya) untuk mengurangi biaya energi jangka panjang."
        ]
    })
    if export_ratio > 25 and net_export_ratio < 0:
        policies.append({
            "priority": "PRIORITAS 3: WAJIB HILIRISASI KOMODITAS",
            "desc": f"Tahan nilai tambah {dominant_sector} di daerah:",
            "actions": [
                f"• **Smelter/Refinery {dominant_sector}:** Wajibkan pengolahan minimal 50% sebelum ekspor.",
                "• **Kawasan Industri Hilir:** Sediakan lahan terintegrasi dengan fasilitas bersama.",
                "• **Larangan Ekspor Mentah:** Terapkan regulasi daerah progresif dalam 3-5 tahun."
            ]
        })
    if import_ratio > 25 or net_export_ratio < -20:
        policies.append({
            "priority": "PRIORITAS 4: SUBSTITUSI IMPOR BERBASIS KLASTER",
            "desc": "Kurangi kebocoran ekonomi:",
            "actions": [
                "• **Industri Penunjang Lokal:** Identifikasi 5 komponen impor terbesar dan berikan hibah lahan.",
                "• **Program Kemitraan Wajib:** Investor besar wajib menyerap 30% suplai dari UMKM lokal.",
                "• **Zona Ekonomi Khusus (KEK):** Dorong status KEK untuk menarik industri substitusi impor."
            ]
        })
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
    policies.append({
        "priority": "PRIORITAS 6: VOKASI SPESIFIK INDUSTRI",
        "desc": f"Siapkan SDM untuk industri {dominant_sector}:",
        "actions": [
            f"• **Kurikulum SMK Politeknik:** Fokus pada teknologi {dominant_sector}, operator alat berat, teknisi smelter.",
            "• **Magang Berbayar Wajib:** Perusahaan besar wajib menerima 10% tenaga kerja lokal sebagai magang berbayar.",
            "• **Beasiswa Ikatan Dinas:** Pemda biayai kuliah warga lokal dengan ikatan kerja di perusahaan daerah."
        ]
    })
    policies.append({
        "priority": "PRIORITAS 7: SERTIFIKASI INTERNASIONAL UMKM",
        "desc": "Akses pasar global untuk UMKM:",
        "actions": [
            "• **Subsidi Sertifikasi:** ISO, HACCP, Organic untuk UMKM potensial ekspor.",
            "• **Trade Matching:** Fasilitasi pertemuan bisnis dengan buyer internasional melalui Kedutaan.",
            "• **Logistik Ekspor Bersama:** Konsolidasi pengiriman UMKM untuk tekan biaya freight."
        ]
    })
    policies.append({
        "priority": "PRIORITAS 8: REVISI RDTR BERBASIS KORIDOR",
        "desc": "Optimalkan tata ruang:",
        "actions": [
            "• **Zona Industri Terintegrasi:** Tetapkan koridor dari tambang/pelabuhan ke kawasan pengolahan.",
            "• **Buffer Zone Lingkungan:** Zona penyangga antara industri dan pemukiman.",
            "• **Infrastruktur Multimoda:** Integrasi jalan-rel-pelabuhan dalam satu masterplan."
        ]
    })
    policies.append({
        "priority": "PRIORITAS 9: REKLAMASI & LINGKUNGAN WAJIB",
        "desc": "Pembangunan berkelanjutan:",
        "actions": [
            "• **Dana Reklamasi Di Muka:** Wajib setor dana reklamasi sebelum operasi dimulai.",
            "• **AMDAL Ketat & Monitoring Real-time:** Sensor kualitas udara/air online di kawasan industri.",
            "• **Green Infrastructure:** Wajib 20% area hijau di setiap kawasan industri baru."
        ]
    })
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

    risks = []
    if net_export_ratio < -50:
        risks.append({"level": "CRITICAL", "msg": f"**Kerentanan Nilai Tukar & Global:** Defisit neraca yang sangat dalam ({net_export_ratio:.1f}%) membuat ekonomi daerah sangat sensitif terhadap fluktuasi kurs dan harga komoditas global."})
    if invest_ratio > 45:
        risks.append({"level": "HIGH", "msg": f"**Risiko Over-Heating:** Investasi terlalu dominan ({invest_ratio:.1f}%) dapat memicu inflasi daerah jika tidak diimbangi peningkatan suplai barang/jasa."})
    if consume_ratio > 60:
        risks.append({"level": "MEDIUM", "msg": f"**Stagnasi Produktivitas:** Ketergantungan pada konsumsi ({consume_ratio:.1f}%) berisiko membuat ekonomi stagnan."})
    if export_ratio > 50 and ("Maluku" in province_name or "Sulawesi" in province_name):
        risks.append({"level": "HIGH", "msg": f"**Monokultur Ekonomi ({dominant_sector}):** Ketergantungan ekstrem pada satu komoditas membuat daerah sangat rentan terhadap fluktuasi harga global."})
    if not risks:
        risks.append({"level": "LOW", "msg": "Struktur ekonomi relatif seimbang. Fokus utama adalah menjaga stabilitas makro dan meningkatkan kualitas SDM serta infrastruktur dasar."})

    return {
        "year": latest_year, "eco_type": eco_type, "dominant_sector": dominant_sector,
        "interpretation": full_interpretation, "policies": policies, "risks": risks,
        "key_metrics": {"investment_ratio": invest_ratio, "consumption_ratio": consume_ratio,
                        "net_export_ratio": net_export_ratio, "multiplier": multiplier}
    }


# ============================================================
# FIXED: load_io_analyzer - no debug output, reliable path resolution
# ============================================================
@st.cache_resource
def load_io_analyzer():
    """Load IO analyzer - resolves path relative to this script file."""
    filename = 'indonesia-tables-as-of-june-2023.xlsx'
    script_dir = os.path.dirname(os.path.abspath(__file__))

    possible_paths = [
        os.path.join(script_dir, filename),   # same folder as app.py  ← fixes the CWD issue
        '/workspace/' + filename,             # explicit absolute path
        filename,                             # relative CWD (last resort)
    ]

    found_path = None
    for path in possible_paths:
        if os.path.exists(path):
            found_path = path
            break

    if not found_path:
        return None, False   # silent – error shown in the tab via io_loaded check

    try:
        analyzer = InputOutputAnalyzer(excel_path=found_path)
        if analyzer.load_table(2020):
            return analyzer, True
        return None, False
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None, False


# Custom CSS
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1f77b4; text-align: center; margin-bottom: 1rem; }
    .policy-box { background-color: #f0fdf4; border-radius: 8px; padding: 15px; margin-bottom: 12px; border-left: 4px solid #22c55e; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .risk-box { background-color: #fef2f2; border-radius: 8px; padding: 15px; margin-bottom: 12px; border-left: 4px solid #ef4444; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .diagnosis-box { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 20px; color: white; margin-bottom: 20px; }
    .metric-premium { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); padding: 1.5rem; border-radius: 15px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
    .sector-card { background: white; padding: 1.2rem; border-radius: 12px; margin-bottom: 1rem; box-shadow: 0 2px 10px rgba(0,0,0,0.08); border-left: 4px solid #667eea; }
    .highlight-box { background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); padding: 1.5rem; border-radius: 15px; margin: 1rem 0; }
    .info-box { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); padding: 1.5rem; border-radius: 15px; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🏛️ Regional Infrastructure Impact & Policy Advisor</p>', unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: #666; margin-bottom: 2rem;'>
Platform analitik berbasis data BPS untuk mengukur multiplier effect investasi infrastruktur
dan memberikan rekomendasi kebijakan berbasis evidence untuk pemerintah provinsi di Indonesia
</div>
""", unsafe_allow_html=True)

st.sidebar.header("⚙️ Parameter Analisis")

grdp_data = load_grdp_data()
province_mapping = load_province_mapping()
io_analyzer, io_loaded = load_io_analyzer()

if not grdp_data:
    st.error("Data tidak tersedia. Pastikan file grdp_full.json ada di workspace.")
    st.stop()

selected_province = st.sidebar.selectbox(
    "Pilih Provinsi:",
    options=list(grdp_data['2024'].keys()),
    index=list(grdp_data['2024'].keys()).index("DKI Jakarta") if "DKI Jakarta" in grdp_data['2024'] else 0
)
available_years = sorted(grdp_data.keys())
selected_year = st.sidebar.selectbox("Tahun Referensi:", options=available_years, index=len(available_years) - 1)
show_methodology = st.sidebar.checkbox("Tampilkan Metodologi", value=False)

if show_methodology:
    st.sidebar.info("""
    **Metodologi Analisis:**
    1. **Infrastructure Multiplier**: Berdasarkan rasio PMTB terhadap GRDP (baseline 1.8x)
    2. **Dampak Langsung**: 40% dari PMTB sebagai investasi infrastruktur
    3. **Dampak Tidak Langsung**: Efek multiplier melalui rantai pasok
    4. **Input-Output Analysis**: Leontief Inverse Matrix, 42 sektor, BPS 2020
    """)

show_io_analysis = st.sidebar.checkbox("Tampilkan Analisis Input-Output", value=False)

if show_io_analysis and io_loaded:
    st.sidebar.success("✅ Tabel Input-Output 2020 berhasil dimuat")
    io_summary_col1, io_summary_col2 = st.columns(2)
    with io_summary_col1:
        st.subheader("🏭 Top 5 Sektor dengan Multiplier Tertinggi")
        top_sectors = io_analyzer.get_top_sectors_by_multiplier(5)
        for rank, (sector, mult) in enumerate(top_sectors, 1):
            st.metric(f"#{rank}", f"{mult:.3f}", sector)
    with io_summary_col2:
        st.subheader("📊 Statistik IO Table")
        st.metric("Total Output Nasional", f"${io_analyzer.data['total_output_sum']:,.2f} Juta USD")
        st.metric("Jumlah Sektor", len(io_analyzer.industry_names))
        construction_linkages = io_analyzer.get_sector_linkages('Construction')
        if construction_linkages:
            st.info(f"""
            **Konstruksi:**
            - Backward Linkage: {construction_linkages['backward_linkage']:.3f}
            - Forward Linkage: {construction_linkages['forward_linkage']:.3f}
            - {construction_linkages['interpretation']}
            """)

impact_results = calculate_economic_impact(grdp_data, selected_province)
if not impact_results:
    st.error(f"Tidak ada data untuk provinsi {selected_province}")
    st.stop()

policy_rec = generate_policy_recommendations(impact_results, selected_province)
latest_data = impact_results.get(selected_year, impact_results[max(impact_results.keys())])

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard Dampak", "🧠 Interpretasi & Kebijakan",
    "📋 Breakdown Data", "🗺️ Komparasi Nasional", "🏛️ Input-Output Analysis"
])

with tab1:
    st.header(f"📍 {selected_province} ({selected_year})")
    if selected_year in impact_results:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Investasi Infrastruktur", f"Rp {latest_data['infrastructure_investment']:,.2f} M",
                      delta=f"{latest_data['investment_ratio']:.2f}% dari PDRB")
        with col2:
            st.metric("Total Dampak Ekonomi", f"Rp {latest_data['total_impact']:,.2f} M",
                      delta=f"Multiplier: {latest_data['multiplier']:.2f}x")
        with col3:
            st.metric("Dampak Tidak Langsung", f"Rp {latest_data['indirect_impact']:,.2f} M",
                      delta=f"+{latest_data['indirect_impact']/latest_data['direct_impact']*100:.2f}% dari dampak langsung")
        with col4:
            st.metric("Kontribusi ke PDRB", f"{latest_data['contribution_ratio']:.2f}%",
                      delta=f"Total PDRB: Rp {latest_data['grdp_total']:,.2f} M")
    st.subheader("📊 Visualisasi Dampak Infrastruktur")
    fig_impact = create_impact_visualization(impact_results, selected_province)
    if fig_impact:
        st.plotly_chart(fig_impact, use_container_width=True)

with tab2:
    st.header(f"🧠 Analisis Kebijakan: {selected_province}")
    if policy_rec:
        if 'interpretation' in policy_rec:
            interp = policy_rec['interpretation']
            st.subheader("🔍 Interpretasi Regional Economist")
            st.markdown(interp.get('structure', ''))
            st.markdown("---")
            st.markdown(interp.get('trade', ''))
            st.markdown("---")
            st.markdown(interp.get('impact', ''))
            st.markdown("---")
        km = policy_rec['key_metrics']
        st.subheader("📈 Indikator Kunci")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Rasio Investasi", f"{km['investment_ratio']:.1f}%")
        col_m2.metric("Rasio Konsumsi", f"{km['consumption_ratio']:.1f}%")
        col_m3.metric("Net Ekspor", f"{km['net_export_ratio']:.1f}%")
        col_m4.metric("Multiplier", f"{km['multiplier']:.2f}x")
        st.markdown("---")
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
        if policy_rec['risks']:
            st.subheader("⚠️ Analisis Risiko")
            for risk in policy_rec['risks']:
                level = risk.get('level', 'MEDIUM') if isinstance(risk, dict) else 'MEDIUM'
                msg = risk['msg'] if isinstance(risk, dict) else str(risk)
                color_map = {
                    'CRITICAL': ("#fef2f2", "#dc2626", "#991b1b"),
                    'HIGH':     ("#fff7ed", "#ea580c", "#9a3412"),
                    'MEDIUM':   ("#fefce8", "#ca8a04", "#854d0e"),
                    'LOW':      ("#f0fdf4", "#16a34a", "#166534"),
                }
                bg, border, text = color_map.get(level, color_map['MEDIUM'])
                st.markdown(f"""
                <div style="background-color:{bg};border-radius:8px;padding:15px;margin-bottom:12px;border-left:4px solid {border};box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                    <p style="color:{text};margin:0;font-weight:500;">{msg}</p>
                </div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.subheader("📊 Decomposition Dampak Ekonomi")
        fig_wf = go.Figure()
        fig_wf.add_trace(go.Bar(x=["Investasi Langsung"], y=[latest_data['infrastructure_investment']],
                                 marker_color="#3b82f6", text=[f"Rp {latest_data['infrastructure_investment']:,.2f} M"],
                                 textposition='outside', name='Investasi Langsung'))
        fig_wf.add_trace(go.Bar(x=["Efek Pengganda"], y=[latest_data['indirect_impact']],
                                 marker_color="#22c55e", text=[f"+ Rp {latest_data['indirect_impact']:,.2f} M"],
                                 textposition='outside', name='Efek Pengganda'))
        fig_wf.add_trace(go.Scatter(x=["Total Dampak"], y=[latest_data['total_impact']],
                                     mode='markers+text', marker=dict(size=20, color="#1f2937"),
                                     text=[f"= Rp {latest_data['total_impact']:,.2f} M"],
                                     textposition='top center', name='Total Dampak', showlegend=False))
        fig_wf.update_layout(title=f"Dekomposisi Dampak ({selected_year})", height=400, barmode='group',
                              xaxis_title="Komponen", yaxis_title="Nilai (Juta Rupiah)", template="plotly_white")
        st.plotly_chart(fig_wf, use_container_width=True)

with tab3:
    st.header("📋 Breakdown Komponen PDRB")
    if selected_year in grdp_data and selected_province in grdp_data[selected_year]:
        values = grdp_data[selected_year][selected_province]
        component_names = ["Konsumsi Rumah Tangga", "Konsumsi LNPRT", "Konsumsi Pemerintah",
                           "PMTB (Investasi)", "Perubahan Inventori", "Ekspor", "Impor", "Ekspor Neto", "Total PDRB"]
        df_components = pd.DataFrame({
            'Komponen': component_names, 'Nilai (Miliar Rupiah)': values,
            'Persentase': [(v / values[8] * 100) if values[8] > 0 else 0 for v in values]
        })
        st.dataframe(df_components.style.format({'Nilai (Miliar Rupiah)': '{:,.2f}', 'Persentase': '{:.2f}%'}),
                     use_container_width=True, hide_index=True)
        col_pie1, col_pie2 = st.columns(2)
        with col_pie1:
            fig_pie = px.pie(df_components.head(6), values='Nilai (Miliar Rupiah)', names='Komponen',
                             title=f"Komposisi PDRB {selected_province} ({selected_year})", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_pie2:
            fig_bar = px.bar(df_components.head(6), x='Persentase', y='Komponen', orientation='h',
                             title='Persentase Kontribusi terhadap PDRB', color='Persentase',
                             color_continuous_scale='Blues')
            fig_bar.update_layout(height=400)
            st.plotly_chart(fig_bar, use_container_width=True)

with tab5:
    st.markdown("""
    <style>
        .io-hero { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 3rem; border-radius: 20px; color: white; margin-bottom: 2rem; box-shadow: 0 10px 40px rgba(102,126,234,0.3); }
        .io-hero h1 { font-size: 2.8rem; font-weight: 800; margin-bottom: 0.5rem; }
        .io-hero p { font-size: 1.1rem; opacity: 0.95; max-width: 800px; }
    </style>
    """, unsafe_allow_html=True)

    if io_loaded:
        st.markdown(f"""
        <div class="io-hero">
            <h1>🏛️ Input-Output Analysis Indonesia 2020</h1>
            <p>Analisis komprehensif menggunakan <strong>Leontief Inverse Matrix</strong> untuk mengukur multiplier effect,
            backward-forward linkages, dan dampak ekonomi dari {len(io_analyzer.industry_names)} sektor industri terhadap perekonomian nasional.</p>
            <p style="margin-top:1rem;font-size:0.95rem;opacity:0.9;">📊 Data: Badan Pusat Statistik (BPS) | Metodologi: Wassily Leontief Input-Output Model</p>
        </div>
        """, unsafe_allow_html=True)

        multipliers = io_analyzer.get_output_multipliers()
        avg_multiplier = np.mean(list(multipliers.values()))
        max_mult_sector = max(multipliers.items(), key=lambda x: x[1])
        construction_mult = multipliers.get('Construction', 0)

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.markdown(f'<div class="metric-premium"><div style="font-size:0.9rem;color:#666;margin-bottom:0.5rem;">📈 Rata-rata Multiplier</div><div style="font-size:2.2rem;font-weight:800;color:#667eea;">{avg_multiplier:.3f}x</div><div style="font-size:0.8rem;color:#888;">Seluruh sektor</div></div>', unsafe_allow_html=True)
        with col_m2:
            st.markdown(f'<div class="metric-premium"><div style="font-size:0.9rem;color:#666;margin-bottom:0.5rem;">🚀 Multiplier Tertinggi</div><div style="font-size:2.2rem;font-weight:800;color:#764ba2;">{max_mult_sector[1]:.3f}x</div><div style="font-size:0.75rem;color:#888;">{max_mult_sector[0][:30]}</div></div>', unsafe_allow_html=True)
        with col_m3:
            st.markdown(f'<div class="metric-premium"><div style="font-size:0.9rem;color:#666;margin-bottom:0.5rem;">🏗️ Konstruksi</div><div style="font-size:2.2rem;font-weight:800;color:#f093fb;">{construction_mult:.3f}x</div><div style="font-size:0.8rem;color:#888;">Sektor infrastruktur</div></div>', unsafe_allow_html=True)
        with col_m4:
            st.markdown(f'<div class="metric-premium"><div style="font-size:0.9rem;color:#666;margin-bottom:0.5rem;">🏭 Total Sektor</div><div style="font-size:2.2rem;font-weight:800;color:#4facfe;">{len(multipliers)}</div><div style="font-size:0.8rem;color:#888;">Industri dianalisis</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='height:2rem;'></div>", unsafe_allow_html=True)

        io_tab1, io_tab2, io_tab3 = st.tabs(["📊 Sector Multipliers", "💰 Investment Impact Simulator", "🔗 Linkages Analysis"])

        with io_tab1:
            st.markdown("### 📈 Output Multipliers: Mengukur Dampak Ekonomi per Sektor")
            multipliers_df = pd.DataFrame([{'Sector': s, 'Output Multiplier': m} for s, m in multipliers.items()]).sort_values('Output Multiplier', ascending=False)
            multipliers_df['Rank'] = range(1, len(multipliers_df)+1)

            def categorize_multiplier(x):
                if x > 2.0: return 'Very High (>2.0)'
                elif x >= 1.5: return 'High (1.5-2.0)'
                elif x >= 1.0: return 'Moderate (1.0-1.5)'
                else: return 'Low (<1.0)'

            multipliers_df['Category'] = multipliers_df['Output Multiplier'].apply(categorize_multiplier)
            col_chart, col_info = st.columns([2, 1])
            with col_chart:
                st.markdown("**🏆 Top 10 Sektor dengan Multiplier Tertinggi**")
                colors = ['#FF6B6B' if x > 2.0 else '#FFD93D' if x > 1.5 else '#6BCB77' if x > 1.0 else '#4D96FF' for x in multipliers_df.head(10)['Output Multiplier']]
                fig_top10 = go.Figure(data=[go.Bar(x=multipliers_df.head(10)['Output Multiplier'], y=multipliers_df.head(10)['Sector'],
                                                    orientation='h', marker_color=colors, marker_line_color='rgba(0,0,0,0.3)', marker_line_width=1,
                                                    hovertemplate='<b>%{y}</b><br>Multiplier: %{x:.4f}x<extra></extra>')])
                fig_top10.update_layout(height=550, xaxis_title="Output Multiplier (x)", showlegend=False,
                                        plot_bgcolor='rgba(240,240,240,0.5)', paper_bgcolor='white',
                                        font=dict(family="Segoe UI", size=12),
                                        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(0,0,0,0.1)'),
                                        yaxis=dict(showgrid=False), margin=dict(l=50,r=50,t=50,b=50))
                st.plotly_chart(fig_top10, use_container_width=True)
            with col_info:
                st.markdown("**📊 Kategori Multiplier**")
                category_counts = multipliers_df['Category'].value_counts()
                for cat in ['Very High (>2.0)', 'High (1.5-2.0)', 'Moderate (1.0-1.5)', 'Low (<1.0)']:
                    count = category_counts.get(cat, 0)
                    st.markdown(f'<div class="sector-card" style="padding:0.8rem;margin-bottom:0.5rem;"><div style="display:flex;justify-content:space-between;align-items:center;"><span>{cat}</span><span style="font-weight:700;font-size:1.2rem;">{count}</span></div></div>', unsafe_allow_html=True)
                st.markdown('<div class="highlight-box"><strong>💡 Insight:</strong><br>Sektor dengan multiplier > 2.0 memiliki dampak ekonomi terbesar. Setiap $1 investasi menghasilkan >$2 output total melalui efek langsung dan tidak langsung.</div>', unsafe_allow_html=True)

            st.markdown("### 📋 Complete Ranking Semua Sektor")

            def color_multiplier(val):
                if val > 2.0: return 'background-color: #FFEBEE; color: #C62828; font-weight: bold'
                elif val >= 1.5: return 'background-color: #FFF3E0; color: #E65100'
                elif val >= 1.0: return 'background-color: #E8F5E9; color: #2E7D32'
                else: return 'background-color: #E3F2FD; color: #1565C0'

            styled_df = multipliers_df[['Rank', 'Sector', 'Output Multiplier', 'Category']].style\
                .format({'Output Multiplier': '{:.4f}x'})\
                .apply(lambda x: [color_multiplier(val) if name == 'Output Multiplier' else '' for name, val in zip(x.index, x)], axis=0)\
                .hide(axis='index')
            st.dataframe(styled_df, use_container_width=True, height=600)

        with io_tab2:
            st.markdown("### 💰 Investment Impact Simulator")
            col_ctrl1, col_ctrl2 = st.columns([1, 1])
            with col_ctrl1:
                st.markdown("**🏭 Pilih Sektor Target**")
                selected_io_sector = st.selectbox("", options=io_analyzer.industry_names,
                                                   index=io_analyzer.industry_names.index('Construction') if 'Construction' in io_analyzer.industry_names else 0,
                                                   label_visibility="collapsed")
                sector_mult = multipliers.get(selected_io_sector, 0)
                st.markdown(f'<div class="sector-card"><div style="font-size:0.9rem;color:#666;">Output Multiplier Sektor Ini</div><div style="font-size:1.8rem;font-weight:800;color:#667eea;">{sector_mult:.4f}x</div></div>', unsafe_allow_html=True)
            with col_ctrl2:
                st.markdown("**💵 Besaran Investasi (Juta USD)**")
                investment_amount = st.slider("", min_value=100, max_value=50000, value=5000, step=500, label_visibility="collapsed")
                st.markdown(f'<div class="sector-card" style="text-align:center;"><div style="font-size:0.9rem;color:#666;">Investasi yang Disimulasikan</div><div style="font-size:1.8rem;font-weight:800;color:#764ba2;">${investment_amount:,.0f} Juta USD</div></div>', unsafe_allow_html=True)

            calc_col1, calc_col2, calc_col3 = st.columns([1, 2, 1])
            with calc_col2:
                calculate_btn = st.button("🚀 Hitung Dampak Ekonomi", type="primary", use_container_width=True)

            if calculate_btn or 'impact_calculated' in st.session_state:
                st.session_state.impact_calculated = True
                impact = io_analyzer.calculate_infrastructure_impact(investment_amount, selected_io_sector)
                if 'error' not in impact:
                    st.markdown(f'<div style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);padding:2rem;border-radius:15px;color:white;margin:2rem 0;"><h3 style="margin:0;font-size:1.5rem;">📊 Hasil Simulasi: {selected_io_sector}</h3><p style="margin:0.5rem 0 0 0;opacity:0.9;">Investasi: ${investment_amount:,.0f} Juta USD</p></div>', unsafe_allow_html=True)
                    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
                    with res_col1: st.markdown(f'<div class="metric-premium" style="background:linear-gradient(135deg,#a8edea 0%,#fed6e3 100%);"><div style="font-size:0.85rem;color:#555;">📥 Dampak Langsung</div><div style="font-size:1.8rem;font-weight:800;color:#2c3e50;">${impact["direct_impact"]:,.2f}M</div></div>', unsafe_allow_html=True)
                    with res_col2: st.markdown(f'<div class="metric-premium" style="background:linear-gradient(135deg,#ffecd2 0%,#fcb69f 100%);"><div style="font-size:0.85rem;color:#555;">🔄 Dampak Tidak Langsung</div><div style="font-size:1.8rem;font-weight:800;color:#2c3e50;">${impact["indirect_impact"]:,.2f}M</div></div>', unsafe_allow_html=True)
                    with res_col3: st.markdown(f'<div class="metric-premium" style="background:linear-gradient(135deg,#a1c4fd 0%,#c2e9fb 100%);"><div style="font-size:0.85rem;color:#555;">📤 Total Dampak</div><div style="font-size:1.8rem;font-weight:800;color:#2c3e50;">${impact["total_impact"]:,.2f}M</div></div>', unsafe_allow_html=True)
                    with res_col4:
                        mv = impact['multiplier']; mc = '#FF6B6B' if mv>2 else '#FFD93D' if mv>1.5 else '#6BCB77'
                        st.markdown(f'<div class="metric-premium" style="background:linear-gradient(135deg,#d299c2 0%,#fef9d7 100%);"><div style="font-size:0.85rem;color:#555;">✖️ Multiplier</div><div style="font-size:1.8rem;font-weight:800;color:{mc};">{mv:.4f}x</div></div>', unsafe_allow_html=True)

                    chart_r1, chart_r2 = st.columns(2)
                    with chart_r1:
                        fig_pie2 = go.Figure(data=[go.Pie(labels=['Dampak Langsung','Dampak Tidak Langsung'],
                                                           values=[impact['direct_impact'],impact['indirect_impact']],
                                                           hole=0.4, marker_colors=['#667eea','#764ba2'],
                                                           textinfo='label+percent')])
                        fig_pie2.update_layout(height=400, title_text="📊 Distribusi Dampak Investasi", paper_bgcolor='white')
                        st.plotly_chart(fig_pie2, use_container_width=True)
                    with chart_r2:
                        top5_df = pd.DataFrame(impact['top_5_beneficiaries'], columns=['Sector','Impact']).sort_values('Impact', ascending=True)
                        fig_ben = go.Figure(data=[go.Bar(x=top5_df['Impact'], y=top5_df['Sector'], orientation='h',
                                                          marker_color=['#667eea','#764ba2','#f093fb','#4facfe','#43e97b'],
                                                          hovertemplate='%{y}: $%{x:,.2f} Juta<extra></extra>')])
                        fig_ben.update_layout(height=400, title_text="🏆 5 Sektor Penerima Manfaat Terbesar",
                                              xaxis_title="Dampak (Juta USD)", showlegend=False,
                                              paper_bgcolor='white', plot_bgcolor='rgba(240,240,240,0.5)')
                        st.plotly_chart(fig_ben, use_container_width=True)

                    st.markdown("### 📋 Breakdown Lengkap per Sektor")
                    breakdown_df = pd.DataFrame([{'Sektor': k, 'Dampak (Juta USD)': v, '% dari Total': (v/impact['total_impact'])*100}
                                                  for k,v in sorted(impact['sector_breakdown'].items(), key=lambda x:x[1], reverse=True)])
                    st.dataframe(breakdown_df.style.format({'Dampak (Juta USD)': '${:,.2f}', '% dari Total': '{:.2f}%'}),
                                 use_container_width=True, height=400)

        with io_tab3:
            st.markdown("### 🔗 Backward & Forward Linkages Analysis")
            col_sel1, col_sel2 = st.columns([2, 1])
            with col_sel1:
                linkage_sector = st.selectbox("**🏭 Pilih Sektor untuk Analisis Linkages:**",
                                               options=io_analyzer.industry_names,
                                               index=io_analyzer.industry_names.index('Construction') if 'Construction' in io_analyzer.industry_names else 0)
            linkages = io_analyzer.get_sector_linkages(linkage_sector)
            with col_sel2:
                if linkages:
                    interp_short = linkages['interpretation'].split(' - ')[0] if ' - ' in linkages['interpretation'] else linkages['interpretation']
                    st.markdown(f'<div class="sector-card" style="text-align:center;"><div style="font-size:0.85rem;color:#666;">Klasifikasi Sektor</div><div style="font-size:1.1rem;font-weight:700;color:#667eea;">{interp_short}</div></div>', unsafe_allow_html=True)

            if linkages:
                lc1, lc2, lc3, lc4 = st.columns(4)
                with lc1: st.markdown(f'<div class="metric-premium"><div style="font-size:0.8rem;color:#555;">⬅️ Backward Linkage</div><div style="font-size:2rem;font-weight:800;color:#C62828;">{linkages["backward_linkage"]:.4f}</div><div style="font-size:0.75rem;color:#888;">Keterkaitan Hulu</div></div>', unsafe_allow_html=True)
                with lc2: st.markdown(f'<div class="metric-premium"><div style="font-size:0.8rem;color:#555;">➡️ Forward Linkage</div><div style="font-size:2rem;font-weight:800;color:#F57C00;">{linkages["forward_linkage"]:.4f}</div><div style="font-size:0.75rem;color:#888;">Keterkaitan Hilir</div></div>', unsafe_allow_html=True)
                with lc3: st.markdown(f'<div class="metric-premium"><div style="font-size:0.8rem;color:#555;">📥 Direct Input Coef.</div><div style="font-size:1.8rem;font-weight:800;color:#764ba2;">{linkages["direct_input_coefficient"]:.4f}</div></div>', unsafe_allow_html=True)
                with lc4: st.markdown(f'<div class="metric-premium"><div style="font-size:0.8rem;color:#555;">📤 Direct Sales Coef.</div><div style="font-size:1.8rem;font-weight:800;color:#667eea;">{linkages["direct_sales_coefficient"]:.4f}</div></div>', unsafe_allow_html=True)

                box_class = 'highlight-box' if 'Key' in linkages['interpretation'] else 'info-box'
                st.markdown(f'<div class="{box_class}"><h4>💡 Interpretasi Ekonomis:</h4><p style="font-size:1.1rem;"><strong>{linkages["interpretation"]}</strong></p></div>', unsafe_allow_html=True)

                viz1, viz2 = st.columns(2)
                with viz1:
                    fig_radar = go.Figure(data=go.Scatterpolar(
                        r=[linkages['backward_linkage'], linkages['forward_linkage'],
                           linkages['direct_input_coefficient']*10, linkages['direct_sales_coefficient']*10],
                        theta=['Backward Linkage<br>(Hulu)', 'Forward Linkage<br>(Hilir)', 'Direct Input<br>(×10)', 'Direct Sales<br>(×10)'],
                        fill='toself', line_color='#667eea', fillcolor='rgba(102,126,234,0.3)', name=linkage_sector
                    ))
                    fig_radar.update_layout(height=500, title=f"🕸️ Radar Profile: {linkage_sector}", title_font_size=16,
                                            polar=dict(radialaxis=dict(visible=True, gridcolor='rgba(0,0,0,0.2)'),
                                                       angularaxis=dict(gridcolor='rgba(0,0,0,0.2)')),
                                            paper_bgcolor='white', showlegend=False, margin=dict(l=50,r=50,t=80,b=50))
                    st.plotly_chart(fig_radar, use_container_width=True)
                with viz2:
                    avg_backward = np.mean([io_analyzer.get_sector_linkages(s)['backward_linkage'] for s in io_analyzer.industry_names[:10]])
                    avg_forward  = np.mean([io_analyzer.get_sector_linkages(s)['forward_linkage']  for s in io_analyzer.industry_names[:10]])
                    fig_cmp = go.Figure(data=[
                        go.Bar(name='Sektor Terpilih', x=['Backward Linkage','Forward Linkage'],
                               y=[linkages['backward_linkage'],linkages['forward_linkage']],
                               marker_color=['#667eea','#764ba2'], text=[f'{linkages["backward_linkage"]:.2f}',f'{linkages["forward_linkage"]:.2f}'], textposition='outside'),
                        go.Bar(name='Rata-rata Ekonomi*', x=['Backward Linkage','Forward Linkage'],
                               y=[avg_backward,avg_forward], marker_color=['#ffd700','#c0c0c0'],
                               text=[f'{avg_backward:.2f}',f'{avg_forward:.2f}'], textposition='outside')
                    ])
                    fig_cmp.update_layout(height=500, title="📊 Perbandingan dengan Rata-rata Ekonomi", barmode='group',
                                          yaxis_title="Nilai Linkage", paper_bgcolor='white', plot_bgcolor='rgba(240,240,240,0.5)')
                    st.plotly_chart(fig_cmp, use_container_width=True)
                    st.caption("*Rata-rata dihitung dari 10 sektor pertama sebagai sampel")
    else:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#ff6b6b 0%,#ee5a24 100%);padding:3rem;border-radius:20px;color:white;text-align:center;">
            <h2 style="font-size:2rem;margin-bottom:1rem;">❌ Gagal Memuat Tabel Input-Output</h2>
            <p style="font-size:1.1rem;margin-bottom:2rem;">File 'indonesia-tables-as-of-june-2023.xlsx' tidak ditemukan.</p>
            <div style="background:rgba(255,255,255,0.2);padding:1.5rem;border-radius:10px;">
                <strong>Solusi:</strong><br>
                Pastikan file Excel berada di folder yang sama dengan app.py
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab4:
    st.header("🗺️ Perbandingan Antar Provinsi")
    all_provinces_impact = {}
    for province in grdp_data['2024'].keys():
        impact = calculate_economic_impact(grdp_data, province)
        if impact:
            all_provinces_impact[province] = impact
    fig_compare_all = create_comparison_chart(all_provinces_impact)
    st.plotly_chart(fig_compare_all, use_container_width=True)

    st.subheader("📈 Tren Pertumbuhan Dampak Infrastruktur")
    comparison_provinces = st.multiselect(
        "Pilih provinsi untuk dibandingkan:",
        options=list(all_provinces_impact.keys()),
        default=["DKI Jakarta", "Jawa Barat", "Jawa Timur"] if "DKI Jakarta" in all_provinces_impact else list(all_provinces_impact.keys())[:3],
        max_selections=5
    )
    if comparison_provinces:
        trend_data = []
        for province in comparison_provinces:
            if province in all_provinces_impact:
                for year, data in all_provinces_impact[province].items():
                    trend_data.append({'Year': int(year), 'Province': province,
                                       'Total Impact': data['total_impact'], 'Multiplier': data['multiplier']})
        df_trend = pd.DataFrame(trend_data)
        fig_trend = px.line(df_trend, x='Year', y='Total Impact', color='Province', markers=True,
                            title='Tren Dampak Ekonomi Infrastruktur Antar Provinsi',
                            labels={'Year': 'Tahun', 'Total Impact': 'Total Dampak (Triliun Rupiah)'})
        fig_trend.update_traces(line=dict(width=3))
        st.plotly_chart(fig_trend, use_container_width=True)
        fig_mult2 = px.line(df_trend, x='Year', y='Multiplier', color='Province', markers=True,
                            title='Tren Infrastructure Multiplier Antar Provinsi',
                            labels={'Year': 'Tahun', 'Multiplier': 'Nilai Multiplier'})
        fig_mult2.add_hline(y=1.8, line_dash="dash", line_color="gray", annotation_text="Baseline Multiplier (1.8x)")
        st.plotly_chart(fig_mult2, use_container_width=True)

st.markdown("---")
st.markdown("""
<div style='text-align:center;color:#666;font-size:0.9rem;'>
    <b>Sumber Data:</b> Badan Pusat Statistik (BPS) Indonesia<br>
    Publikasi: Produk Domestik Regional Bruto Provinsi-Provinsi di Indonesia Menurut Pengeluaran 2021-2025<br>
    <i>Dikembangkan dengan metodologi Regional Economic Impact Analysis & Policy Advisory System</i>
</div>
""", unsafe_allow_html=True)
