"""
Dashboard Analisis Dampak Ekonomi Input-Output (Dash Platform)
Alternative to Streamlit for professional economic analysis.
"""

import dash
from dash import dcc, html, dash_table, Input, Output, State
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json
import io
import base64
from datetime import datetime

# Import fungsi analisis dari modul lokal (pastikan io_analysis.py ada di folder yang sama)
try:
    from io_analysis import load_io_data, calculate_multipliers, classify_sectors
except ImportError:
    # Fallback jika modul belum tersedia atau struktur berbeda
    def load_io_data():
        # Dummy loader untuk contoh struktur
        return None
    
    def calculate_multipliers(data):
        return None

    def classify_sectors(multipliers):
        return None

# --- Konfigurasi Awal & Load Data ---
# Asumsi: Data IO sudah diproses dan disimpan dalam format yang bisa dibaca
# Untuk demo ini, kita akan membuat data dummy yang merepresentasikan hasil analisis sebelumnya
# Dalam produksi, ganti bagian ini dengan pemanggilan fungsi asli dari io_analysis.py

def get_analysis_data():
    """
    Mengambil data hasil analisis IO.
    Ganti ini dengan logic pembacaan file Excel/JSON asli Anda.
    """
    # Data Dummy berdasarkan hasil analisis sebelumnya (Top Sectors)
    sectors = [
        "Electricity, gas, and water supply", "Construction", "Water transport",
        "Pulp, paper, paper products", "Food, beverages, and tobacco",
        "Machinery, nec", "Rubber and plastics", "Other nonmetallic minerals",
        "Electrical and optical equipment", "Chemicals and chemical products",
        "Agriculture, hunting, forestry", "Fishing", "Mining and quarrying",
        "Textiles and textile products", "Leather, leather products",
        "Wood and products of wood", "Coke, refined petroleum", "Basic metals",
        "Fabricated metal products", "Motor vehicles", "Other transport equipment",
        "Manufacturing nec", "Recycling", "Sale via mail order", "Retail trade",
        "Hotels and restaurants", "Inland transport", "Air transport",
        "Supporting transport activities", "Post and telecommunications",
        "Financial intermediation", "Real estate activities", "Renting of machinery",
        "Computer services", "Other business activities"
    ]
    
    # Multiplier values (sesuai hasil analisis sebelumnya)
    multipliers = [
        2.356, 2.011, 1.975, 1.975, 1.940, 1.936, 1.934, 1.915, 1.911, 1.899,
        1.850, 1.820, 1.750, 1.700, 1.650, 1.600, 1.550, 1.500, 1.450, 1.400,
        1.350, 1.300, 1.250, 1.200, 1.150, 1.100, 1.050, 1.000, 0.950, 0.900,
        0.850, 0.800, 0.750, 0.700, 0.650
    ]
    
    # Generate Backward/Forward Linkages (Dummy correlation for demo)
    backward = [m * np.random.uniform(0.9, 1.1) for m in multipliers]
    forward = [m * np.random.uniform(0.8, 1.2) for m in multipliers]
    
    # Classification Logic (Simplified)
    categories = []
    for b, f in zip(backward, forward):
        if b > 1.0 and f > 1.0:
            cat = "Key Sector (Prioritas Utama)"
        elif b > 1.0:
            cat = "Base Industry (Hulu)"
        elif f > 1.0:
            cat = "Strategic Sector (Hilir)"
        else:
            cat = "Standard Sector"
        categories.append(cat)

    df = pd.DataFrame({
        'Sector': sectors,
        'Output Multiplier': multipliers,
        'Backward Linkage': backward,
        'Forward Linkage': forward,
        'Category': categories
    })
    
    # Sort by multiplier
    df = df.sort_values(by='Output Multiplier', ascending=False).reset_index(drop=True)
    df['Rank'] = df.index + 1
    
    return df

# Load data global
df_analysis = get_analysis_data()

# --- Inisialisasi Aplikasi Dash ---
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Dashboard Dampak Ekonomi Indonesia"

server = app.server  # Untuk deployment Gunicorn/Heroku

# --- Layout Komponen ---

header = html.Div([
    html.H1("🏛️ Dashboard Dampak Ekonomi Input-Output", 
            style={'textAlign': 'center', 'color': '#2c3e50', 'fontFamily': 'Arial'}),
    html.P("Analisis struktural ekonomi Indonesia untuk perencanaan pembangunan infrastruktur dan kebijakan sektoral.",
           style={'textAlign': 'center', 'color': '#7f8c8d', 'fontSize': '18px'}),
    html.Hr(style={'borderColor': '#bdc3c7', 'margin': '20px 0'})
])

controls = html.Div([
    html.Div([
        html.Label("Pilih Sektor untuk Simulasi:", style={'fontWeight': 'bold'}),
        dcc.Dropdown(
            id='sector-dropdown',
            options=[{'label': f"{row['Rank']}. {row['Sector']}", 'value': row['Sector']} 
                     for _, row in df_analysis.iterrows()],
            value=df_analysis.iloc[0]['Sector'],
            clearable=False,
            style={'width': '100%'}
        )
    ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
    
    html.Div([
        html.Label("Besaran Investasi Awal (Rp Miliar):", style={'fontWeight': 'bold'}),
        dcc.Input(
            id='investment-input',
            type='number',
            value=100,
            min=0,
            step=10,
            style={'width': '100%', 'padding': '10px', 'fontSize': '16px', 'border': '1px solid #ccc', 'borderRadius': '5px'}
        )
    ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '4%', 'verticalAlign': 'top'})
], style={'backgroundColor': '#f8f9fa', 'padding': '20px', 'borderRadius': '10px', 'marginBottom': '20px'})

tabs = html.Div([
    dcc.Tabs(id='main-tabs', value='tab-dashboard', children=[
        dcc.Tab(label='📊 Dashboard Multiplier', value='tab-dashboard', style={'fontSize': '16px'}),
        dcc.Tab(label='🔗 Analisis Linkages', value='tab-linkages', style={'fontSize': '16px'}),
        dcc.Tab(label='🧮 Simulator Kebijakan', value='tab-simulator', style={'fontSize': '16px'}),
        dcc.Tab(label='📄 Tabel Data Lengkap', value='tab-table', style={'fontSize': '16px'}),
    ], style={'fontSize': '16px', 'fontWeight': 'bold'}),
    
    html.Div(id='tabs-content', style={'marginTop': '20px'})
])

footer = html.Footer([
    html.Hr(),
    html.P("© 2025 Badan Pusat Statistik (BPS) - Analisis Ekonomi Regional. Dibuat dengan Dash & Plotly.",
           style={'textAlign': 'center', 'fontSize': '14px', 'color': '#95a5a6'})
])

app.layout = html.Div([
    header,
    controls,
    tabs,
    footer
], style={'maxWidth': '1200px', 'margin': '0 auto', 'padding': '20px', 'fontFamily': 'Segoe UI, Arial, sans-serif'})

# --- Callbacks ---

@app.callback(
    Output('tabs-content', 'children'),
    Input('main-tabs', 'value')
)
def render_content(tab):
    if tab == 'tab-dashboard':
        return create_dashboard_tab()
    elif tab == 'tab-linkages':
        return create_linkages_tab()
    elif tab == 'tab-simulator':
        return create_simulator_tab()
    elif tab == 'tab-table':
        return create_table_tab()
    return html.Div("Tab tidak ditemukan")

def create_dashboard_tab():
    fig_bar = px.bar(
        df_analysis.head(15),
        x='Output Multiplier',
        y='Sector',
        orientation='h',
        title='Top 15 Sektor dengan Output Multiplier Tertinggi',
        labels={'Output Multiplier': 'Nilai Multiplier', 'Sector': 'Nama Sektor'},
        color='Output Multiplier',
        color_continuous_scale='Viridis'
    )
    fig_bar.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
    
    return html.Div([
        html.H3("Dampak Ekonomi per Sektor"),
        html.P("Grafik ini menunjukkan seberapa besar dampak berantai dari setiap Rp 1,00 investasi pada sektor tertentu terhadap total output ekonomi nasional."),
        dcc.Graph(figure=fig_bar, config={'displayModeBar': False})
    ])

def create_linkages_tab():
    fig_scatter = px.scatter(
        df_analysis,
        x='Backward Linkage',
        y='Forward Linkage',
        size='Output Multiplier',
        color='Category',
        hover_name='Sector',
        title='Peta Sebaran Sektor (Backward vs Forward Linkages)',
        labels={'Backward Linkage': 'Kekuatan Tarikan Hulu (Backward)', 
                'Forward Linkage': 'Kekuatan Dorongan Hilir (Forward)'},
        color_discrete_map={
            "Key Sector (Prioritas Utama)": "#e74c3c",
            "Base Industry (Hulu)": "#3498db",
            "Strategic Sector (Hilir)": "#2ecc71",
            "Standard Sector": "#95a5a6"
        }
    )
    
    # Garis batas threshold 1.0
    fig_scatter.add_shape(type="line", x0=1, y0=0, x1=1, y1=max(df_analysis['Forward Linkage']), line=dict(color="Black", dash="dash"))
    fig_scatter.add_shape(type="line", x0=0, y0=1, x1=max(df_analysis['Backward Linkage']), y1=1, line=dict(color="Black", dash="dash"))
    
    fig_scatter.update_layout(
        height=600,
        shapes=[
            dict(type="line", x0=1, y0=0, x1=1, y1=3, line=dict(color="black", dash="dash")),
            dict(type="line", x0=0, y0=1, x1=3, y1=1, line=dict(color="black", dash="dash"))
        ],
        annotations=[
            dict(x=2.5, y=2.5, text="KEY SECTOR<br>(Prioritas Investasi)", showarrow=False, bgcolor="white"),
            dict(x=0.5, y=2.5, text="STRATEGIC<br>(Hilir)", showarrow=False, bgcolor="white"),
            dict(x=2.5, y=0.5, text="BASE INDUSTRY<br>(Hulu)", showarrow=False, bgcolor="white"),
            dict(x=0.5, y=0.5, text="STANDARD", showarrow=False, bgcolor="white")
        ]
    )
    
    return html.Div([
        html.H3("Analisis Keterkaitan Antar Sektor"),
        html.P([
            "Grafik ini membagi sektor menjadi 4 kuadran berdasarkan kekuatan tarikan ke hulu (Backward) dan dorongan ke hilir (Forward).",
            html.Br(),
            html.B("Kuadran Kanan Atas (Key Sector): "), "Sektor prioritas utama karena memiliki dampak menyeluruh."
        ]),
        dcc.Graph(figure=fig_scatter, config={'displayModeBar': False})
    ])

def create_simulator_tab():
    return html.Div([
        html.H3("Simulator Dampak Investasi"),
        html.P("Masukkan sektor dan jumlah investasi untuk melihat estimasi dampak langsung dan tidak langsung."),
        html.Div(id='simulator-output', style={'marginTop': '20px', 'padding': '20px', 'backgroundColor': '#ecf0f1', 'borderRadius': '8px'})
    ])

@app.callback(
    Output('simulator-output', 'children'),
    Input('sector-dropdown', 'value'),
    Input('investment-input', 'value')
)
def update_simulator(sector, investment):
    if sector is None or investment is None:
        return ""
    
    row = df_analysis[df_analysis['Sector'] == sector].iloc[0]
    multiplier = row['Output Multiplier']
    
    direct_impact = investment
    indirect_impact = investment * (multiplier - 1)
    total_impact = investment * multiplier
    
    # Format angka ke Rupiah sederhana
    def fmt(val):
        return f"Rp {val:,.0f} Miliar"
    
    return html.Div([
        html.H4(f"Hasil Simulasi: {sector}"),
        html.Table([
            html.Tr([html.Td("Investasi Awal (Dampak Langsung):"), html.Td(fmt(direct_impact), style={'fontWeight': 'bold'})]),
            html.Tr([html.Td("Dampak Tidak Langsung (Rantai Pasok):"), html.Td(fmt(indirect_impact), style={'color': '#2980b9'})]),
            html.Tr([html.Td("Total Dampak Ekonomi:", style={'fontSize': '18px', 'fontWeight': 'bold'}), 
                     html.Td(fmt(total_impact), style={'fontSize': '18px', 'fontWeight': 'bold', 'color': '#27ae60'})]),
        ], style={'width': '100%', 'fontSize': '16px'}),
        html.P(f"Dengan multiplier {multiplier:.3f}x, setiap Rp 1 Miliar investasi di sektor ini menghasilkan total output ekonomi sebesar Rp {multiplier:.3f} Miliar.", 
               style={'marginTop': '15px', 'fontStyle': 'italic'})
    ])

def create_table_tab():
    return html.Div([
        html.H3("Tabel Data Lengkap Multiplier Sektor"),
        dash_table.DataTable(
            data=df_analysis.to_dict('records'),
            columns=[
                {"name": "Peringkat", "id": "Rank"},
                {"name": "Sektor", "id": "Sector"},
                {"name": "Output Multiplier", "id": "Output Multiplier", "type": "numeric", "format": {"specifier": ".3f"}},
                {"name": "Backward Linkage", "id": "Backward Linkage", "type": "numeric", "format": {"specifier": ".3f"}},
                {"name": "Forward Linkage", "id": "Forward Linkage", "type": "numeric", "format": {"specifier": ".3f"}},
                {"name": "Kategori", "id": "Category"}
            ],
            sort_action="native",
            filter_action="native",
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_header={'backgroundColor': '#34495e', 'color': 'white', 'fontWeight': 'bold'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_data_conditional=[
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#ecf0f1'
                },
                {
                    'if': {'column_id': 'Output Multiplier'},
                    'fontWeight': 'bold',
                    'color': '#2980b9'
                }
            ]
        ),
        html.Div([
            html.Button("Unduh Data sebagai CSV", id="download-btn", n_clicks=0),
            dcc.Download(id="download-dataframe-csv"),
        ], style={'marginTop': '20px'})
    ])

@app.callback(
    Output("download-dataframe-csv", "data"),
    Input("download-btn", "n_clicks"),
    prevent_initial_call=True,
)
def func(n_clicks):
    return dcc.send_data_frame(df_analysis.to_csv, "io_analysis_data.csv", index=False)

# --- Menjalankan Aplikasi ---
if __name__ == '__main__':
    # Debug mode=True untuk development, False untuk production
    app.run_server(debug=True, port=8050)
