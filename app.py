import streamlit as st
import pandas as pd
import json
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta, timezone

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Livelo Alpha Intel", page_icon="💎", layout="wide")

def get_brasilia_time():
    """Garante a exibição da hora correta no Dashboard."""
    fuso_br = timezone(timedelta(hours=-3))
    return datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')

@st.cache_data(ttl=300) # Cache de 5 minutos
def load_data():
    try:
        # Acessa o segredo literal
        if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
            st.error("Configuração de Secrets não encontrada.")
            return None
            
        gs_secrets = st.secrets["connections"]["gsheets"]
        
        # Converte a string JSON para dicionário
        creds_dict = json.loads(gs_secrets["GOOGLE_JSON_CREDENTIALS"])
        
        # CORREÇÃO DEFINITIVA DA CHAVE: Troca o texto '\n' pela quebra de linha real
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        
        # Conecta usando o dicionário tratado
        conn = st.connection("gsheets", type=GSheetsConnection, **creds_dict)
        
        # Lê a planilha
        url_planilha = gs_secrets["spreadsheet"]
        data = conn.read(spreadsheet=url_planilha)
        return data
    except Exception as e:
        st.error(f"❌ Erro de Conexão: {e}")
        return None

# --- CONSTRUÇÃO DO DASHBOARD ---
df = load_data()

if df is not None:
    # Tratamento das colunas
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
    
    # Pega apenas a última oferta de cada loja para o "Agora"
    df_agora = df.sort_values('Data').groupby('Loja').last().reset_index()

    st.title("💎 Livelo Alpha Intel")
    st.markdown(f"**Status do Mercado em:** {get_brasilia_time()}")
    
    # Filtros na Sidebar
    st.sidebar.header("🎯 Filtros de Oportunidade")
    busca = st.sidebar.text_input("Filtrar Loja")
    min_pts = st.sidebar.slider("Pontuação Mínima", 1, 20, 5)
    
    df_filtered = df_agora[df_agora['Valor'] >= min_pts]
    if busca:
        df_filtered = df_filtered[df_filtered['Loja'].str.contains(busca, case=False)]

    # Tabs
    tab1, tab2, tab3 = st.tabs(["🔥 Ofertas do Momento", "📉 Histórico e ATH", "🧮 Calculadora de Lucro"])

    with tab1:
        cols = st.columns(4)
        for i, row in df_filtered.iterrows():
            with cols[i % 4]:
                with st.container(border=True):
                    st.image(row['Logo'], width=80)
                    st.subheader(row['Loja'])
                    st.metric("Acúmulo", f"{row['Pontos']}")
                    st.caption(f"Categoria: {row.get('Tipo', 'Varejo')}")

    with tab2:
        lojas_comparar = st.multiselect("Comparar Histórico", df['Loja'].unique(), default=df['Loja'].unique()[:2])
        if lojas_comparar:
            fig = px.line(df[df['Loja'].isin(lojas_comparar)], x='Data', y='Valor', color='Loja', markers=True)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("Calculadora de Arbitragem")
        val_compra = st.number_input("Valor da Compra (R$)", value=1000.0)
        # Tenta pegar a pontuação da primeira loja filtrada como padrão
        pts_default = float(df_filtered.iloc[0]['Valor']) if not df_filtered.empty else 1.0
        val_pts = st.number_input("Pontos por Real", value=pts_default)
        val_milheiro = st.slider("Valor de Venda do Milheiro (R$)", 20.0, 45.0, 35.0)
        
        ganho_pts = val_compra * val_pts
        retorno_rs = (ganho_pts / 1000) * val_milheiro
        custo_real = val_compra - retorno_rs
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Pontos Ganhos", f"{ganho_pts:,.0f}")
        c2.metric("Retorno em R$", f"R$ {retorno_rs:.2f}")
        c3.metric("Custo Final Efetivo", f"R$ {custo_real:.2f}", delta=f"-{retorno_rs/val_compra*100:.1f}%")

else:
    st.warning("Aguardando configuração das Secrets no painel do Streamlit Cloud...")