import streamlit as st
import pandas as pd
import json
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta, timezone

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Livelo Alpha Intel", page_icon="💎", layout="wide")

def get_brasilia_time():
    fuso_br = timezone(timedelta(hours=-3))
    return datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')

@st.cache_data(ttl=300)
def load_data():
    try:
        # Acesso ao TOML estruturado
        if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
            st.error("❌ Configuração [connections.gsheets] não encontrada nos Secrets.")
            return None
            
        secrets_gsheets = st.secrets["connections"]["gsheets"]
        
        # Carrega o JSON
        raw_json = secrets_gsheets["GOOGLE_JSON_CREDENTIALS"]
        creds_info = json.loads(raw_json)
        
        # CORREÇÃO CRÍTICA: Tratar as quebras de linha na Private Key
        # Às vezes o parser do TOML mantém o literal '\n' como texto, o Google exige o caractere real.
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
        
        # Conecta
        conn = st.connection("gsheets", type=GSheetsConnection, **creds_info)
        
        url_planilha = secrets_gsheets["spreadsheet"]
        data = conn.read(spreadsheet=url_planilha)
        return data
    except Exception as e:
        st.error(f"❌ Erro de Conexão: {e}")
        return None

# --- EXECUÇÃO ---
df = load_data()

if df is not None:
    # Converter colunas e tratar dados
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
    df_now = df.sort_values('Data').groupby('Loja').last().reset_index()

    st.title("💎 Livelo Alpha Intel")
    st.caption(f"Última sincronização: {get_brasilia_time()}")

    # Layout de Mercado: Cards de Oferta
    st.subheader("🔥 Melhores Ofertas Atuais")
    cols = st.columns(4)
    for idx, row in df_now.iterrows():
        with cols[idx % 4]:
            with st.container(border=True):
                st.image(row['Logo'], width=60)
                st.markdown(f"**{row['Loja']}**")
                st.markdown(f"## {row['Pontos']}")
                st.progress(min(int(row['Valor'])/15, 1.0)) # Barra de 'calor' da oferta

    # Seção de Gráfico
    st.divider()
    st.subheader("📈 Análise de Tendência")
    lojas = st.multiselect("Selecione lojas:", df['Loja'].unique(), default=df['Loja'].unique()[:2])
    if lojas:
        fig = px.line(df[df['Loja'].isin(lojas)], x='Data', y='Valor', color='Loja', markers=True)
        st.plotly_chart(fig, use_container_width=True)
else:
    st.stop()