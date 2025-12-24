import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone

# --- CONFIGURAÇÃO DA UI ---
st.set_page_config(page_title="Alpha Points Intel", page_icon="💎", layout="wide")

# CSS Moderno compatível com Temas Claro/Escuro
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* Variáveis de Cores para Modo Escuro/Claro Automático */
    :root {
        --card-bg: var(--secondary-background-color);
        --card-shadow: rgba(0, 0, 0, 0.3);
        --text-main: var(--text-color);
        --accent-green: #10b981;
    }

    /* Ajuste de visibilidade do Header e Captions */
    .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp span, .stApp label {
        color: var(--text-color) !important;
    }
    
    .stCaption {
        color: var(--text-color) !important;
        opacity: 0.8;
    }

    /* Estilização dos Cards de Oferta */
    .offer-card {
        background: var(--secondary-background-color);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid var(--border-color);
        transition: all 0.3s ease;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        margin-bottom: 20px;
    }

    .offer-card:hover {
        transform: translateY(-5px);
        border-color: #007bff;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }

    .store-logo {
        height: 50px;
        filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.1));
        margin-bottom: 15px;
        border-radius: 8px;
    }

    .points-value {
        color: var(--accent-green);
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
    }

    /* Customização das Tabs para Dark Mode */
    .stTabs [data-baseweb="tab-list"] {
        background-color: var(--secondary-background-color);
        border-radius: 12px;
        padding: 5px;
    }

    .stTabs [data-baseweb="tab"] {
        color: var(--text-color);
        opacity: 0.6;
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--background-color) !important;
        color: var(--text-color) !important;
        opacity: 1;
        border-radius: 8px;
    }

    /* Métrica de Topo Estilizada */
    [data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        border: 1px solid var(--border-color);
        padding: 15px;
        border-radius: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# ... (Funções de dados get_now_br e load_market_data permanecem iguais)

# --- LÓGICA DE EXECUÇÃO ---
df = load_market_data()

if df is not None and not df.empty:
    ultima_verificacao = df['Data'].max()
    
    # --- HEADER ---
    # Usando container para garantir espaçamento
    with st.container():
        st.title("💎 Alpha Points Intelligence")
        st.markdown(f"**Status:** Monitoramento Ativo | **Sincronização:** `{ultima_verificacao.strftime('%d/%m/%Y %H:%M')}`")
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.image("https://www.livelo.com.br/file/general/livelo-logo.svg", width=120)
        st.title("Painel de Controle")
        ver_apenas_atual = st.toggle("Filtrar Última Varredura", value=True)
        min_pts = st.slider("Pontuação Mínima", 0, int(df['Valor'].max()), 0)
        search_loja = st.text_input("🔍 Buscar Loja")

    # Filtros
    if ver_apenas_atual:
        df_display = df[df['Data'] == ultima_verificacao].copy()
    else:
        df_display = df.sort_values('Data').groupby('Loja').last().reset_index()

    df_filtered = df_display[df_display['Valor'] >= min_pts]
    if search_loja:
        df_filtered = df_filtered[df_filtered['Loja'].str.contains(search_loja, case=False)]

    # --- MÉTRICAS ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Parceiros", len(df_filtered))
    with m2:
        if not df_filtered.empty:
            top_row = df_filtered.sort_values('Valor', ascending=False).iloc[0]
            st.metric("Melhor Oferta", f"{top_row['Valor']} pts", top_row['Loja'])
    with m3:
        if not df_filtered.empty:
            cashback = (top_row['Valor'] * 35 / 1000) * 100
            st.metric("ROI Est.", f"{cashback:.1f}%")
    with m4:
        st.metric("Database", "Livelo v2", delta="Online")

    st.divider()

    # --- CONTEÚDO ---
    tab_now, tab_hist, tab_calc = st.tabs(["🔥 Oportunidades", "📈 Análise Histórica", "🧮 Calculadora"])

    with tab_now:
        if not df_filtered.empty:
            df_filtered = df_filtered.sort_values('Valor', ascending=False)
            cols = st.columns(4)
            for i, (idx, row) in enumerate(df_filtered.iterrows()):
                with cols[i % 4]:
                    logo_url = row['Logo'] if pd.notnull(row['Logo']) and row['Logo'] != "" else "https://via.placeholder.com/150"
                    
                    # Layout HTML Moderno com suporte a Dark Mode
                    st.markdown(f"""
                        <div class="offer-card">
                            <img src="{logo_url}" class="store-logo">
                            <div style="font-size: 1.1rem; font-weight: 600; margin-bottom: 5px;">{row['Loja']}</div>
                            <div class="points-value">{row['Valor']}</div>
                            <div class="points-label">Pontos por Real</div>
                            <div style="margin-top: 15px; font-size: 0.7rem; opacity: 0.6;">
                                Verificado às {row['Data'].strftime('%H:%M')}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("Nenhuma oferta encontrada para os filtros atuais.")

    # ... (Restante do código das abas Tab_Hist e Tab_Calc)