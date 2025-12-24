import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone

# --- 1. CONFIGURAÇÃO DA UI ---
st.set_page_config(page_title="Alpha Points Intel", page_icon="💎", layout="wide")

# CSS Inteligente: Adapta-se ao tema (Claro ou Escuro)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Estilização dos Cards de Oferta */
    .offer-card {
        background-color: var(--secondary-background-color);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid var(--border-color);
        transition: all 0.3s ease;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        margin-bottom: 20px;
        min-height: 280px;
    }

    .offer-card:hover {
        transform: translateY(-5px);
        border-color: #007bff;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }

    .store-logo {
        height: 50px;
        max-width: 120px;
        object-fit: contain;
        margin-bottom: 15px;
    }

    .points-value {
        color: #10b981; 
        font-size: 2.2rem;
        font-weight: 800;
        margin: 5px 0;
    }

    .points-label {
        color: var(--text-color);
        opacity: 0.7;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Customização das Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: var(--secondary-background-color);
        border-radius: 12px;
        padding: 6px;
        gap: 8px;
    }

    [data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        border: 1px solid var(--border-color);
        padding: 15px;
        border-radius: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÕES DE SUPORTE ---

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

# --- 3. EXECUÇÃO DO APP ---

df = load_market_data()

if df is not None and not df.empty:
    ultima_verificacao = df['Data'].max()
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.image("https://www.livelo.com.br/file/general/livelo-logo.svg", width=120)
        st.title("Configurações")
        ver_apenas_atual = st.toggle("Apenas Última Varredura", value=True)
        min_pts = st.slider("Mínimo de Pontos", 0, int(df['Valor'].max()), 0)
        search_loja = st.text_input("🔍 Buscar Loja")

    if ver_apenas_atual:
        df_display = df[df['Data'] == ultima_verificacao].copy()
    else:
        df_display = df.sort_values('Data').groupby('Loja').last().reset_index()

    df_filtered = df_display[df_display['Valor'] >= min_pts]
    if search_loja:
        df_filtered = df_filtered[df_filtered['Loja'].str.contains(search_loja, case=False)]

    # --- HEADER ---
    st.title("💎 Alpha Points Intelligence")
    st.markdown(f"Status: **Online** | Última sincronização: `{ultima_verificacao.strftime('%d/%m/%Y %H:%M')}`")
    
    # Métricas
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
        st.metric("Base de Dados", "Livelo v2", delta="Sync OK")

    st.divider()

    # --- TABS ---
    tab_now, tab_hist, tab_calc = st.tabs(["🔥 Oportunidades", "📈 Histórico", "🧮 Calculadora"])

    with tab_now:
        if not df_filtered.empty:
            df_filtered = df_filtered.sort_values('Valor', ascending=False)
            cols = st.columns(4)
            for i, (idx, row) in enumerate(df_filtered.iterrows()):
                with cols[i % 4]:
                    # --- LÓGICA DA MOEDA ---
                    # Verifica o valor na coluna 'Moeda'. Se for "Dolar", muda o texto.
                    moeda_val = str(row.get('Moeda', 'Real')).strip().title()
                    label_pts = "Pontos por Dolar" if moeda_val == "Dolar" else "Pontos por Real"
                    
                    logo = row['Logo'] if pd.notnull(row['Logo']) and row['Logo'] != "" else "https://via.placeholder.com/150"
                    st.markdown(f"""
                        <div class="offer-card">
                            <img src="{logo}" class="store-logo">
                            <div style="font-weight: 600; font-size: 1.1rem; margin-bottom: 5px;">{row['Loja']}</div>
                            <div class="points-value">{row['Valor']}</div>
                            <div class="points-label">{label_pts}</div>
                            <div style="margin-top: 15px; font-size: 0.75rem; opacity: 0.6;">
                                Atualizado às {row['Data'].strftime('%H:%M')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("Nenhuma oferta encontrada para os critérios selecionados.")

    with tab_hist:
        st.subheader("Tendência de Acúmulo")
        lojas_hist = st.multiselect("Selecione lojas para comparar", df['Loja'].unique(), default=df['Loja'].unique()[:3] if len(df['Loja'].unique()) > 0 else None)
        if lojas_hist:
            df_plot = df[df['Loja'].isin(lojas_hist)].sort_values('Data')
            fig = px.line(df_plot, x='Data', y='Valor', color='Loja', markers=True, template="plotly_dark")
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

    with tab_calc:
        st.subheader("Simulador de Lucro")
        if not df_filtered.empty:
            c1, c2 = st.columns(2)
            with c1:
                v_compra = st.number_input("Valor do Produto", min_value=1.0, value=1000.0)
                loja_sel = st.selectbox("Parceiro Escolhido", options=df_filtered['Loja'].tolist())
                row_sel = df_filtered[df_filtered['Loja'] == loja_sel].iloc[0]
                pts_v = row_sel['Valor']
                moeda_sel = str(row_sel.get('Moeda', 'Real')).strip().title()
            
            with c2:
                v_milha = st.slider("Preço de Venda do Milheiro (R$)", 15.0, 45.0, 35.0)
                
                # Cálculo básico
                total_pts = v_compra * pts_v
                retorno = (total_pts / 1000) * v_milha
                custo_f = v_compra - retorno

            st.markdown(f"""
                <div style="background-color: var(--secondary-background-color); padding: 25px; border-radius: 12px; border: 1px solid var(--border-color); margin-top: 20px;">
                    <div style="text-align: center; margin-bottom: 15px; opacity: 0.8;">
                        Modo de Cálculo: <b>{moeda_sel}</b>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; text-align: center;">
                        <div><p style="opacity: 0.7; margin:0;">Pontos</p><h3>{int(total_pts):,}</h3></div>
                        <div><p style="opacity: 0.7; margin:0;">Cashback</p><h3 style="color:#10b981;">R$ {retorno:.2f}</h3></div>
                        <div><p style="opacity: 0.7; margin:0;">Custo Final</p><h3 style="color:#3b82f6;">R$ {custo_f:.2f}</h3></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

else:
    st.error("Não foi possível carregar os dados. Verifique a planilha ou as chaves de API.")