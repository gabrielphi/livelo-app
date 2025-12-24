import streamlit as st
import pandas as pd
import json
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Livelo Market Intel", page_icon="📈", layout="wide")

# --- CONEXÃO COM DADOS (PLANO B) ---
@st.cache_data(ttl=600) # Cache de 10 minutos
def load_data():
    try:
        # 1. Carrega o JSON puro da Secret
        creds_info = json.loads(st.secrets["GOOGLE_JSON_CREDENTIALS"])
        
        # 2. Conecta usando o dicionário de credenciais
        conn = st.connection("gsheets", type=GSheetsConnection, **creds_info)
        
        # 3. Lê os dados
        url_planilha = "https://docs.google.com/spreadsheets/d/1M0nFxK-O10wTxdljuBGDsAnd86234QNiQqme9kqlOiE/edit"
        data = conn.read(spreadsheet=url_planilha)
        return data
    except Exception as e:
        st.error(f"❌ Falha crítica na conexão: {e}")
        return None

df = load_data()

if df is not None:
    # Tratamento de Dados
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')

    # --- INTERFACE ---
    st.title("📈 Livelo Market Intelligence")
    st.markdown("Dashboard profissional para monitoramento de acúmulo de pontos.")

    # Sidebar
    st.sidebar.header("Filtros")
    filtro_loja = st.sidebar.text_input("🔍 Buscar Parceiro")
    min_pontos = st.sidebar.number_input("Mínimo de Pontos", value=5)

    # Lógica de Filtro
    mask = (df['Valor'] >= min_pontos)
    if filtro_loja:
        mask &= df['Loja'].str.contains(filtro_loja, case=False)
    
    df_filtered = df[mask]

    # --- MÉTRICAS ---
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Parceiros Ativos", len(df_filtered['Loja'].unique()))
    with m2:
        top_loja = df_filtered.sort_values(by='Valor', ascending=False).iloc[0]
        st.metric("Maior Pontuação", f"{top_loja['Valor']} pts", top_loja['Loja'])
    with m3:
        # Cálculo de Cashback Equivalente (Milheiro a R$ 35,00)
        cashback = (top_loja['Valor'] * 35 / 1000) * 100
        st.metric("Cashback Máximo Est.", f"{cashback:.1f}%")

    # --- VISUALIZAÇÃO ---
    tab1, tab2 = st.tabs(["💎 Ofertas Atuais", "📊 Histórico de Ofertas"])

    with tab1:
        # Mostra os cards das lojas
        df_now = df_filtered.sort_values('Data').groupby('Loja').last().reset_index()
        
        cols = st.columns(4)
        for idx, row in df_now.iterrows():
            with cols[idx % 4]:
                st.image(row['Logo'], width=100)
                st.subheader(row['Loja'])
                st.info(f"**{row['Pontos']}**")
                st.caption(f"Tipo: {row['Tipo']}")
                st.divider()

    with tab2:
        st.subheader("Evolução Temporal da Pontuação")
        lojas_grafico = st.multiselect("Selecione lojas para comparar", 
                                       options=df['Loja'].unique(), 
                                       default=df['Loja'].unique()[:2])
        
        if lojas_grafico:
            df_hist = df[df['Loja'].isin(lojas_grafico)]
            fig = px.line(df_hist, x='Data', y='Valor', color='Loja', markers=True)
            st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Aguardando carregamento dos dados...")

# Rodapé
st.markdown("---")
st.caption(f"Última sincronização: {get_brasilia_time() if 'df' in locals() else 'N/A'}")