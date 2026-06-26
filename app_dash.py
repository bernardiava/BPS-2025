import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import os
import sys

# Tambahkan path ke src agar bisa import io_analysis
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from io_analysis import load_io_data, calculate_multipliers, calculate_linkages
except ImportError:
    # Fallback jika struktur folder berbeda
    print("Warning: Could not import io_analysis module. Using mock data for demonstration.")
    
    # Mock data untuk testing di Render
    def load_io_data():
        return None
    
    def calculate_multipliers(io_table):
        sectors = [f"Sektor {i}" for i in range(1, 36)]
        multipliers = np.random.uniform(1.5, 2.5, 35)
        return pd.DataFrame({
            'Sector': sectors,
            'Output Multiplier': multipliers
        })
    
    def calculate_linkages(io_table):
        sectors = [f"Sektor {i}" for i in range(1, 36)]
        backward = np.random.uniform(0.8, 2.2, 35)
        forward = np.random.uniform(0.8, 2.2, 35)
        return pd.DataFrame({
            'Sector': sectors,
            'Backward Linkage': backward,
            'Forward Linkage': forward
        })

# ==========================================
# LOAD DATA
# ==========================================
def get_analysis_data():
    """Load data IO dan hitung multiplier & linkages"""
    try:
        # Coba load dari file Excel jika ada
        io_path = os.path.join(os.path.dirname(__file__), 'indonesia-tables-as-of-june-2023.xlsx')
        if os.path.exists(io_path):
            io_table = pd.read_excel(io_path, sheet_name='2022', skiprows=9)
            multipliers_df = calculate_multipliers(io_table)
            linkages_df = calculate_linkages(io_table)
            return multipliers_df, linkages_df
        else:
            raise FileNotFoundError
    except Exception as e:
        print(f"Using mock data due to: {e}")
        # Return mock data
        sectors = [
            "Agriculture, hunting, forestry, and fishing",
            "Mining and quarrying",
            "Food, beverages, and tobacco",
            "Textiles and textile products",
            "Leather, leather goods, and footwear",
            "Wood and products of wood and cork",
            "Pulp, paper, paper products, printing, and publishing",
            "Coke, refined petroleum, and nuclear fuel",
            "Chemicals and chemical products",
            "Rubber and plastics",
            "Other nonmetallic minerals",
            "Basic metals and fabricated metal",
            "Machinery, nec",
            "Electrical and optical equipment",
            "Transport equipment",
            "Manufacturing, nec; recycling",
            "Electricity, gas, and water supply",
            "Construction",
            "Sale, maintenance, and repair of motor vehicles...",
            "Wholesale trade and commission trade...",
            "Retail trade, except of motor vehicles...",
            "Hotels and restaurants",
            "Inland transport",
            "Water transport",
            "Air transport",
            "Other supporting and auxiliary transport activities...",
            "Post and telecommunications",
            "Financial intermediation, except insurance...",
            "Insurance and pension funding, except compulsory...",
            "Activities auxiliary to financial intermediation",
            "Real estate activities",
            "Renting of machinery and equipment...",
            "Computer and related activities",
            "Research and development",
            "Other business activities"
        ]
        
        # Mock multipliers (mirip hasil analisis sebelumnya)
        mock_mult = [
            1.75, 1.45, 1.94, 1.68, 1.52, 1.71, 1.97, 1.65, 1.90, 1.93,
            1.91, 1.85, 1.94, 1.91, 1.78, 1.62, 2.36, 2.01, 1.67, 1.72,
            1.69, 1.58, 1.82, 1.98, 1.73, 1.64, 1.76, 1.81, 1.55, 1.63,
            1.48, 1.59, 1.71, 1.66, 1.74
        ]
        
        # Mock linkages
        mock_backward = np.random.uniform(0.9, 2.1, 35)
        mock_forward = np.random.uniform(0.9, 2.1, 35)
        
        multipliers_df = pd.DataFrame({
            'Sector': sectors,
            'Output Multiplier': mock_mult
        })
        
        linkages_df = pd.DataFrame({
            'Sector': sectors,
            'Backward Linkage': mock_backward,
            'Forward Linkage': mock_forward
        })
        
        # Add ranking
        multipliers_df['Rank'] = multipliers_df['Output Multiplier'].rank(ascending=False).astype(int)
        multipliers_df = multipliers_df.sort_values('Rank')
        
        # Categorize linkages
        avg_backward = linkages_df['Backward Linkage'].mean()
        avg_forward = linkages_df['Forward Linkage'].mean()
        
        def categorize(row):
            if row['Backward Linkage'] > avg_backward and row['Forward Linkage'] > avg_forward:
                return '🔑 Key Sector'
            elif row['Backward Linkage'] > avg_backward:
                return '🏭 Base Industry'
            elif row['Forward Linkage'] > avg_forward:
                return '📦 Strategic Sector'
            else:
                return '📊 Standard Sector'
        
        linkages_df['Category'] = linkages_df.apply(categorize, axis=1)
        
        return multipliers_df, linkages_df

# Load data saat startup
multipliers_df, linkages_df = get_analysis_data()

# ==========================================
# DASH APP INITIALIZATION
# ==========================================
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server  # Penting untuk Gunicorn/Render

# ==========================================
# LAYOUT
# ==========================================
app.layout = html.Div([
    # Header
    html.Header([
        html.H1("🏛️ Dashboard Analisis Input-Output Indonesia", 
                style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '10px'}),
        html.P("Visualisasi dampak ekonomi infrastruktur dan sektor strategis lainnya",
               style={'textAlign': 'center', 'color': '#7f8c8d', 'fontSize': '18px'})
    ], style={'backgroundColor': '#ecf0f1', 'padding': '30px', 'borderBottom': '4px solid #3498db'}),
    
    # Container utama
    html.Div([
        # Tab 1: Multiplier Dashboard
        html.Div([
            html.H2("📊 Top Sektor dengan Multiplier Tertinggi", 
                    style={'color': '#2c3e50', 'borderBottom': '2px solid #3498db', 'paddingBottom': '10px'}),
            dcc.Graph(
                id='multiplier-chart',
                figure=px.bar(
                    multipliers_df.head(15).sort_values('Output Multiplier', ascending=True),
                    x='Output Multiplier',
                    y='Sector',
                    orientation='h',
                    title='15 Sektor dengan Output Multiplier Tertinggi',
                    labels={'Output Multiplier': 'Multiplier', 'Sector': 'Sektor'},
                    color='Output Multiplier',
                    color_continuous_scale='Viridis'
                ).update_layout(
                    height=600,
                    xaxis_title='Nilai Multiplier',
                    yaxis_title='',
                    showlegend=False
                )
            )
        ], style={'marginBottom': '40px'}),
        
        # Tab 2: Linkages Analysis
        html.Div([
            html.H2("🔗 Analisis Backward & Forward Linkages", 
                    style={'color': '#2c3e50', 'borderBottom': '2px solid #3498db', 'paddingBottom': '10px'}),
            html.P("""
                **Cara Membaca:**
                - 🔑 **Key Sector**: Backward > rata-rata DAN Forward > rata-rata (Prioritas utama!)
                - 🏭 **Base Industry**: Backward > rata-rata (Banyak menyerap supplier lokal)
                - 📦 **Strategic Sector**: Forward > rata-rata (Banyak mensupply sektor lain)
                - 📊 **Standard Sector**: Di bawah rata-rata
            """, style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '5px', 'marginBottom': '20px'}),
            dcc.Graph(
                id='linkages-scatter',
                figure=px.scatter(
                    linkages_df,
                    x='Backward Linkage',
                    y='Forward Linkage',
                    color='Category',
                    text='Sector',
                    title='Peta Sebaran Sektor Berdasarkan Linkages',
                    labels={'Backward Linkage': 'Backward Linkage (Daya Tarik Supplier)', 
                            'Forward Linkage': 'Forward Linkage (Daya Dorong Hilir)'},
                    color_discrete_map={
                        '🔑 Key Sector': '#e74c3c',
                        '🏭 Base Industry': '#3498db',
                        '📦 Strategic Sector': '#2ecc71',
                        '📊 Standard Sector': '#95a5a6'
                    },
                    size_max=15
                ).update_layout(
                    height=700,
                    xaxis=dict(showgrid=True, zeroline=True, zerolinecolor='black'),
                    yaxis=dict(showgrid=True, zeroline=True, zerolinecolor='black'),
                    hovermode='closest'
                ).add_shape(
                    type='line',
                    x0=linkages_df['Backward Linkage'].mean(),
                    y0=0,
                    x1=linkages_df['Backward Linkage'].mean(),
                    y1=linkages_df['Forward Linkage'].max() * 1.1,
                    line=dict(color='black', width=2, dash='dash')
                ).add_shape(
                    type='line',
                    x0=0,
                    y0=linkages_df['Forward Linkage'].mean(),
                    x1=linkages_df['Backward Linkage'].max() * 1.1,
                    y1=linkages_df['Forward Linkage'].mean(),
                    line=dict(color='black', width=2, dash='dash')
                ).add_annotation(
                    x=linkages_df['Backward Linkage'].mean(),
                    y=linkages_df['Forward Linkage'].max() * 1.05,
                    text=f"Rata-rata Backward: {linkages_df['Backward Linkage'].mean():.2f}",
                    showarrow=False,
                    font=dict(size=12, color='black')
                ).add_annotation(
                    x=linkages_df['Backward Linkage'].max() * 1.05,
                    y=linkages_df['Forward Linkage'].mean(),
                    text=f"Rata-rata Forward: {linkages_df['Forward Linkage'].mean():.2f}",
                    showarrow=False,
                    font=dict(size=12, color='black'),
                    textangle=90
                )
            )
        ], style={'marginBottom': '40px'}),
        
        # Tab 3: Policy Simulator
        html.Div([
            html.H2("🧮 Simulator Dampak Investasi", 
                    style={'color': '#2c3e50', 'borderBottom': '2px solid #3498db', 'paddingBottom': '10px'}),
            html.Div([
                html.Div([
                    html.Label("Pilih Sektor:", style={'fontWeight': 'bold', 'fontSize': '16px'}),
                    dcc.Dropdown(
                        id='sector-dropdown',
                        options=[{'label': f"{row['Sector']} ({row['Output Multiplier']:.2f}x)" 
                                 for idx, row in multipliers_df.iterrows()],
                        value=multipliers_df.iloc[0]['Sector'],
                        style={'width': '100%', 'marginBottom': '20px'}
                    ),
                    html.Label("Nilai Investasi (Juta USD):", style={'fontWeight': 'bold', 'fontSize': '16px'}),
                    dcc.Input(
                        id='investment-input',
                        type='number',
                        value=100,
                        min=0,
                        step=10,
                        style={'width': '100%', 'padding': '10px', 'fontSize': '16px', 'marginBottom': '20px'}
                    ),
                    html.Button("Hitung Dampak", id='calculate-btn', 
                                style={'width': '100%', 'padding': '15px', 'fontSize': '18px', 
                                       'backgroundColor': '#3498db', 'color': 'white', 'border': 'none', 
                                       'borderRadius': '5px', 'cursor': 'pointer'})
                ], style={'width': '45%', 'display': 'inline-block', 'verticalAlign': 'top', 'paddingRight': '20px'}),
                
                html.Div([
                    html.Div(id='simulation-output', style={'backgroundColor': '#f8f9fa', 'padding': '20px', 
                                                             'borderRadius': '5px', 'height': '100%'})
                ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'})
            ])
        ], style={'marginBottom': '40px'}),
        
        # Tab 4: Data Table
        html.Div([
            html.H2("📋 Tabel Data Lengkap", 
                    style={'color': '#2c3e50', 'borderBottom': '2px solid #3498db', 'paddingBottom': '10px'}),
            html.Div([
                html.Table([
                    html.Thead([
                        html.Tr([html.Th(col) for col in ['Rank', 'Sektor', 'Multiplier', 'Kategori']])
                    ]),
                    html.Tbody(id='data-table-body')
                ], style={'width': '100%', 'borderCollapse': 'collapse', 'fontSize': '14px'})
            ], style={'overflowX': 'auto'}),
            html.Br(),
            html.A("Download Data sebagai CSV", 
                   href="/data/download-csv/",
                   download="io_analysis_data.csv",
                   style={'padding': '10px 20px', 'backgroundColor': '#27ae60', 'color': 'white', 
                          'textDecoration': 'none', 'borderRadius': '5px', 'fontWeight': 'bold'})
        ])
        
    ], style={'maxWidth': '1200px', 'margin': '0 auto', 'padding': '20px'}),
    
    # Footer
    html.Footer([
        html.Hr(),
        html.P("© 2025 Dashboard Analisis Input-Output Indonesia | Data: BPS & OECD", 
               style={'textAlign': 'center', 'color': '#7f8c8d'})
    ], style={'padding': '20px', 'backgroundColor': '#ecf0f1', 'marginTop': '40px'})
])

# ==========================================
# CALLBACKS
# ==========================================
@callback(
    Output('simulation-output', 'children'),
    Input('calculate-btn', 'n_clicks'),
    [Input('sector-dropdown', 'value'),
     Input('investment-input', 'value')]
)
def simulate_impact(n_clicks, sector, investment):
    if n_clicks is None or sector is None or investment is None:
        return html.P("Silakan pilih sektor dan masukkan nilai investasi, lalu klik 'Hitung Dampak'.")
    
    # Cari multiplier sektor yang dipilih
    sector_data = multipliers_df[multipliers_df['Sector'] == sector]
    if sector_data.empty:
        return html.P("Sektor tidak ditemukan.", style={'color': 'red'})
    
    multiplier = sector_data['Output Multiplier'].values[0]
    
    # Hitung dampak
    direct_impact = investment
    indirect_impact = investment * (multiplier - 1)
    total_impact = investment * multiplier
    
    # Buat visualisasi hasil
    return html.Div([
        html.H3("Hasil Simulasi", style={'color': '#2c3e50', 'marginTop': '0'}),
        html.P(f"**Sektor:** {sector}", style={'fontSize': '16px'}),
        html.P(f"**Multiplier:** {multiplier:.4f}x", style={'fontSize': '18px', 'fontWeight': 'bold', 'color': '#3498db'}),
        html.Hr(),
        html.Div([
            html.Div([
                html.P("Dampak Langsung:", style={'margin': '0', 'fontWeight': 'bold'}),
                html.P(f"${direct_impact:,.0f} Juta", 
                       style={'margin': '5px 0', 'fontSize': '20px', 'color': '#27ae60'})
            ], style={'width': '48%', 'display': 'inline-block'}),
            html.Div([
                html.P("Dampak Tidak Langsung:", style={'margin': '0', 'fontWeight': 'bold'}),
                html.P(f"${indirect_impact:,.0f} Juta", 
                       style={'margin': '5px 0', 'fontSize': '20px', 'color': '#f39c12'})
            ], style={'width': '48%', 'display': 'inline-block', 'textAlign': 'right'})
        ]),
        html.Hr(),
        html.Div([
            html.P("TOTAL DAMPAK EKONOMI:", 
                   style={'margin': '0', 'fontSize': '18px', 'fontWeight': 'bold', 'color': '#2c3e50'}),
            html.P(f"${total_impact:,.0f} Juta", 
                   style={'margin': '10px 0', 'fontSize': '32px', 'fontWeight': 'bold', 'color': '#e74c3c'})
        ], style={'backgroundColor': '#fff', 'padding': '15px', 'borderRadius': '5px', 'border': '2px solid #e74c3c'}),
        html.P(f"*Setiap $1 investasi di sektor ini menghasilkan ${multiplier:.2f} output ekonomi total.*", 
               style={'fontStyle': 'italic', 'color': '#7f8c8d', 'fontSize': '14px'})
    ])

@callback(
    Output('data-table-body', 'children'),
    Input('data-table-body', 'id')  # Dummy trigger untuk load awal
)
def render_table(_):
    rows = []
    for _, row in multipliers_df.iterrows():
        # Cari kategori dari linkages_df jika ada
        linkage_row = linkages_df[linkages_df['Sector'] == row['Sector']]
        category = linkage_row['Category'].values[0] if not linkage_row.empty else '-'
        
        rows.append(html.Tr([
            html.Td(row['Rank'], style={'padding': '8px', 'border': '1px solid #ddd', 'textAlign': 'center'}),
            html.Td(row['Sector'], style={'padding': '8px', 'border': '1px solid #ddd'}),
            html.Td(f"{row['Output Multiplier']:.4f}x", 
                    style={'padding': '8px', 'border': '1px solid #ddd', 'textAlign': 'center', 'fontWeight': 'bold'}),
            html.Td(category, style={'padding': '8px', 'border': '1px solid #ddd'})
        ]))
    return rows

# ==========================================
# RUN SERVER (Konfigurasi untuk Render/Production)
# ==========================================
if __name__ == '__main__':
    # Deteksi port dari environment variable (wajib untuk Render/Heroku)
    port = int(os.environ.get('PORT', 8050))
    
    print(f"Starting Dash app on port {port}...")
    app.run_server(
        host='0.0.0.0',  # Wajib agar bisa diakses dari luar container
        port=port,
        debug=False      # Wajib False untuk produksi
    )
