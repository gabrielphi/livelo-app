import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone

# --- CONFIGURAÇÃO DA UI ---
st.set_page_config(page_title="Alpha Points Intel", page_icon="💎", layout="wide")

# CSS Avançado para Design Moderno
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Background Geral */
    .stApp {
        background-color: #f8fafc;
    }

    /* Estilização dos Cards de Oferta */
    .offer-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border: 1px solid #f1f5f9;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 20px;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        min-height: 300px;
    }

    .offer-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }

    .store-logo {
        height: 60px;
        object-fit: contain;
        margin-bottom: 15px;
    }

    .points-value {
        color: #059669;
        font-size: 2rem;
        font-weight: 700;
        margin: 10px 0;
    }

    .points-label {
        color: #64748b;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .badge {
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-top: 10px;
    }

    .badge-blue { background-color: #dbeafe; color: #1e40af; }
    
    /* Customização das Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #f1f5f9;
        padding: 8px;
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: transparent;
        border-radius: 8px;
        border: none;
        color: #64748b;
    }

    .stTabs [aria-selected="true"] {
        background-color: white !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        color: #0f172a !important;
    }

    /* Métrica de Topo */
    [data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS ---
def get_now_br():
    now_utc = datetime.now(timezone.utc)
    now_br = now_utc - timedelta(hours=3)
    return now_br.replace(tzinfo=None)

@st.cache_data(ttl=300)
def load_market_data():
    try:
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        if "private_key" in creds_dict:
            key = creds_dict["private_key"].strip().replace("\\n", "\n")
            key = key.replace('"', '').replace("'", "")
            if not key.startswith("-----BEGIN PRIVATE KEY-----"):
                key = "-----BEGIN PRIVATE KEY-----\n" + key
            if not key.endswith("-----END PRIVATE KEY-----"):
                key = key + "\n-----END PRIVATE KEY-----"
            creds_dict["private_key"] = key
        
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        sheet = client.open_by_url(creds_dict["spreadsheet"]).get_worksheet(0)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            df.columns = [col.strip() for col in df.columns]
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Data'])
            df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
            return df
        return None
    except Exception as e:
        st.error(f"❌ Erro na conexão: {str(e)}")
        return None

# --- LÓGICA DE EXECUÇÃO ---
df = load_market_data()

if df is not None and not df.empty:
    ultima_verificacao = df['Data'].max()
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.image("https://www.livelo.com.br/file/general/livelo-logo.svg", width=120)
        st.markdown("---")
        st.title("Filtros Inteligentes")
        ver_apenas_atual = st.toggle("Apenas Ofertas Ativas", value=True)
        min_pts = st.slider("Mínimo de Pontos", 0, int(df['Valor'].max()), 0)
        search_loja = st.text_input("🔍 Buscar Parceiro", "")

    # Filtragem
    if ver_apenas_atual:
        df_display = df[df['Data'] == ultima_verificacao].copy()
    else:
        df_display = df.sort_values('Data').groupby('Loja').last().reset_index()

    df_filtered = df_display[df_display['Valor'] >= min_pts]
    if search_loja:
        df_filtered = df_filtered[df_filtered['Loja'].str.contains(search_loja, case=False)]

    # --- HEADER ---
    st.title("💎 Alpha Points Intel")
    st.markdown(f"Monitoramento em tempo real • Atualizado em: `{ultima_verificacao.strftime('%d/%m %H:%M')}`")
    
    # Métricas de Performance
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Parceiros Ativos", len(df_filtered))
    with m2:
        if not df_filtered.empty:
            top_row = df_filtered.sort_values('Valor', ascending=False).iloc[0]
            st.metric("Melhor Oferta", f"{top_row['Valor']} pts", top_row['Loja'])
    with m3:
        if not df_filtered.empty:
            cashback = (top_row['Valor'] * 35 / 1000) * 100
            st.metric("ROI Máximo Est.", f"{cashback:.1f}%")
    with m4:
        st.metric("Status do Sistema", "Online", delta="Sync OK")

    st.markdown("---")

    # --- CONTEÚDO PRINCIPAL ---
    tab_now, tab_hist, tab_calc = st.tabs(["🔥 Oportunidades", "📈 Análise", "🧮 Calculadora"])

    with tab_now:
        if not df_filtered.empty:
            df_filtered = df_filtered.sort_values('Valor', ascending=False)
            
            # Grid System
            cols = st.columns(4)
            for i, (idx, row) in enumerate(df_filtered.iterrows()):
                col_idx = i % 4
                with cols[col_idx]:
                    # Card em HTML customizado para total controle de design
                    logo_url = row['Logo'] if pd.notnull(row['Logo']) and row['Logo'] != "" else "https://via.placeholder.com/150?text=Sem+Logo"
                    tipo = row.get('Tipo', 'Padrão')
                    
                    st.markdown(f"""
                        <div class="offer-card">
                            <img src="{logo_url}" class="store-logo">
                            <div style="font-weight: 700; color: #1e293b; font-size: 1.1rem;">{row['Loja']}</div>
                            <div class="points-value">{row['Valor']}</div>
                            <div class="points-label">Pontos por Real</div>
                            <span class="badge badge-blue">{tipo}</span>
                            <div style="margin-top: 15px; font-size: 0.75rem; color: #94a3b8;">
                                Atualizado: {row['Data'].strftime('%H:%M')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("Nenhuma oportunidade atende aos filtros selecionados.")

    with tab_hist:
        st.subheader("Tendência de Acúmulo")
        selected = st.multiselect("Comparar Lojas", df['Loja'].unique(), default=df['Loja'].unique()[:3])
        if selected:
            df_plot = df[df['Loja'].isin(selected)].sort_values('Data')
            fig = px.line(df_plot, x='Data', y='Valor', color='Loja', markers=True,
                         color_discrete_sequence=px.colors.qualitative.Prism)
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                             margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with tab_calc:
        st.subheader("Simulador de Lucratividade")
        if not df_filtered.empty:
            c1, c2 = st.columns(2)
            with c1:
                v_prod = st.number_input("Valor da Compra (R$)", min_value=1.0, value=1000.0)
                loja = st.selectbox("Selecione o Parceiro", options=df_filtered['Loja'].tolist())
                pts_real = df_filtered[df_filtered['Loja'] == loja]['Valor'].values[0]
            with c2:
                v_milha = st.slider("Preço de Venda Milheiro (R$)", 15.0, 45.0, 35.0)
                total_pts = v_prod * pts_real
                retorno = (total_pts / 1000) * v_milha
                custo_real = v_prod - retorno
            
            st.markdown(f"""
                <div style="background: white; padding: 30px; border-radius: 12px; border: 1px solid #e2e8f0; margin-top: 20px;">
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; text-align: center;">
                        <div>
                            <p style="color: #64748b; margin-bottom: 5px;">Pontos Totais</p>
                            <h2 style="color: #0f172a; margin: 0;">{int(total_pts):,}</h2>
                        </div>
                        <div>
                            <p style="color: #64748b; margin-bottom: 5px;">Cashback Estimado</p>
                            <h2 style="color: #059669; margin: 0;">R$ {retorno:.2f}</h2>
                        </div>
                        <div>
                            <p style="color: #64748b; margin-bottom: 5px;">Custo Final</p>
                            <h2 style="color: #2563eb; margin: 0;">R$ {custo_real:.2f}</h2>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

else:
    st.error("⚠️ Erro: Não foi possível carregar os dados. Verifique sua conexão com o Google Sheets.")