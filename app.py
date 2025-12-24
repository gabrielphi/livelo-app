import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Livelo Alpha Insights", page_icon="🚀", layout="wide")

st.title("🚀 Livelo Alpha Insights")
st.markdown("---")

# --- CONEXÃO COM DADOS ---
# O Streamlit possui uma conexão nativa otimizada para Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=st.secrets["GOOGLE_SHEET_URL"], ttl="10m")
    
    # Tratamento inicial dos dados
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
except Exception as e:
    st.error(f"Erro ao conectar com a planilha: {e}")
    st.stop()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("Filtros de Busca")
busca_loja = st.sidebar.text_input("🔍 Buscar Loja", "")
min_pontos = st.sidebar.slider("Pontuação Mínima", 5, 20, 5)

# Filtragem de Dados
df_filtrado = df[df['Valor'] >= min_pontos]
if busca_loja:
    df_filtrado = df_filtrado[df_filtrado['Loja'].str.contains(busca_loja, case=False)]

# --- MÉTRICAS EM DESTAQUE ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Lojas Ativas (5+)", len(df_filtrado['Loja'].unique()))

with col2:
    melhor_hoje = df_filtrado.sort_values(by='Data', ascending=False).iloc[0]
    st.metric("Melhor Oferta Atual", f"{melhor_hoje['Valor']} pts", melhor_hoje['Loja'])

with col3:
    # Cálculo de "Cashback" (Assumindo milheiro a R$ 35,00)
    valor_cashback = (melhor_hoje['Valor'] * 35) / 1000 * 100
    st.metric("Cashback Equiv. (Máx)", f"{valor_cashback:.1f}%")

with col4:
    total_historico = len(df)
    st.metric("Registros no Banco", total_historico)

# --- VISUALIZAÇÃO PRINCIPAL ---
tab1, tab2, tab3 = st.tabs(["🔥 Ofertas Atuais", "📈 Histórico ATH", "📊 Análise de Mercado"])

with tab1:
    st.subheader("Oportunidades Disponíveis")
    # Mostra apenas a última execução de cada loja
    df_latest = df_filtrado.sort_values('Data').groupby('Loja').last().reset_index()
    
    # Formatação de "Cards" visuais
    cols = st.columns(3)
    for i, row in df_latest.iterrows():
        with cols[i % 3]:
            with st.container(border=True):
                st.image(row['Logo'], width=80)
                st.subheader(row['Loja'])
                st.write(f"**Pontuação:** {row['Pontos']}")
                st.caption(f"Atualizado em: {row['Data'].strftime('%d/%m %H:%M')}")
                st.link_button("Ir para Livelo", f"https://www.livelo.com.br/juntar-pontos/todos-os-parceiros")

with tab2:
    st.subheader("Gráfico de Evolução (All-Time High)")
    # Gráfico interativo com Plotly
    lojas_selecionadas = st.multiselect("Selecione lojas para comparar", df['Loja'].unique(), default=df['Loja'].unique()[:3])
    df_hist = df[df['Loja'].isin(lojas_selecionadas)]
    
    fig = px.line(df_hist, x='Data', y='Valor', color='Loja', markers=True, 
                  title="Histórico de Pontuação por Loja")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Distribuição de Mercado")
    fig_pie = px.pie(df_latest, names='Tipo', title="Proporção Clube vs Normal")
    st.plotly_chart(fig_pie)