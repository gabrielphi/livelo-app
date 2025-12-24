import streamlit as st
import pandas as pd
import json
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta, timezone

# --- FUNÇÕES UTILITÁRIAS (Necessárias no app.py) ---
def get_brasilia_time():
    """Garante o fuso horário UTC-3 para exibição no Dashboard."""
    fuso_br = timezone(timedelta(hours=-3))
    return datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Livelo Market Intel", page_icon="📈", layout="wide")

# --- CONEXÃO COM DADOS (PLANO B) ---
@st.cache_data(ttl=600)
def load_data():
    try:
        # Verifica se a chave existe antes de tentar carregar
        if "GOOGLE_JSON_CREDENTIALS" not in st.secrets:
            st.error("⚠️ A Secret 'GOOGLE_JSON_CREDENTIALS' não foi encontrada nas configurações do Streamlit.")
            st.info("Acesse 'Settings' -> 'Secrets' no painel do Streamlit Cloud e cole suas credenciais.")
            return None
            
        # Carrega o JSON da Secret
        creds_info = json.loads(st.secrets["GOOGLE_JSON_CREDENTIALS"])
        
        # Conecta usando o dicionário de credenciais
        conn = st.connection("gsheets", type=GSheetsConnection, **creds_info)
        
        # URL da sua planilha
        url_planilha = "https://docs.google.com/spreadsheets/d/1M0nFxK-O10wTxdljuBGDsAnd86234QNiQqme9kqlOiE/edit"
        data = conn.read(spreadsheet=url_planilha)
        return data
    except Exception as e:
        st.error(f"❌ Falha na conexão ou permissão: {e}")
        return None

# --- EXECUÇÃO DO DASHBOARD ---
df = load_data()

if df is not None:
    # Tratamento de Dados
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')

    st.title("📈 Livelo Market Intelligence")
    
    # Métricas
    m1, m2, m3 = st.columns(3)
    df_now = df.sort_values('Data').groupby('Loja').last().reset_index()
    
    with m1:
        st.metric("Parceiros Ativos (5+)", len(df_now))
    with m2:
        top_loja = df_now.sort_values(by='Valor', ascending=False).iloc[0]
        st.metric("Maior Pontuação", f"{top_loja['Valor']} pts", top_loja['Loja'])
    with m3:
        cashback = (top_loja['Valor'] * 35 / 1000) * 100
        st.metric("Cashback Máximo Est.", f"{cashback:.1f}%")

    # Tabs
    tab1, tab2 = st.tabs(["💎 Ofertas Atuais", "📊 Histórico"])
    
    with tab1:
        cols = st.columns(4)
        for idx, row in df_now.iterrows():
            with cols[idx % 4]:
                with st.container(border=True):
                    st.image(row['Logo'], width=80)
                    st.markdown(f"**{row['Loja']}**")
                    st.subheader(f"{row['Pontos']}")
                    st.caption(f"Tipo: {row['Tipo']}")

    with tab2:
        lojas = st.multiselect("Comparar lojas:", df['Loja'].unique(), default=df['Loja'].unique()[:2])
        if lojas:
            fig = px.line(df[df['Loja'].isin(lojas)], x='Data', y='Valor', color='Loja')
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.caption(f"🕒 Última atualização do banco: {get_brasilia_time()}")

else:
    st.stop() # Interrompe se não houver dados