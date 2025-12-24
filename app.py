import streamlit as st
import pandas as pd
import json
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta, timezone

# --- 1. FUNÇÕES UTILITÁRIAS ---
def get_brasilia_time():
    """Retorna a hora atual de Brasília."""
    fuso_br = timezone(timedelta(hours=-3))
    return datetime.now(fuso_br).strftime('%d/%m/%Y %H:%M')

# --- 2. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Livelo Alpha Intel", page_icon="💎", layout="wide")

# Estilização básica para remover o menu padrão e rodapé do Streamlit (Aspecto de App Profissional)
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 3. CONEXÃO E CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=300) # Atualiza a cada 5 minutos
def load_data():
    try:
        # Pega a string JSON de dentro do bloco [connections.gsheets] do seu TOML
        # Se você colocou como [connections.gsheets], o acesso é aninhado:
        secrets_dict = st.secrets["connections"]["gsheets"]
        
        if "GOOGLE_JSON_CREDENTIALS" not in secrets_dict:
            st.error("ERRO: 'GOOGLE_JSON_CREDENTIALS' não encontrada dentro de [connections.gsheets]")
            return None

        # Converte a string JSON para dicionário Python
        creds_info = json.loads(secrets_dict["GOOGLE_JSON_CREDENTIALS"])
        
        # Inicia a conexão
        conn = st.connection("gsheets", type=GSheetsConnection, **creds_info)
        
        # Lê a planilha usando a URL que está no TOML
        url_planilha = secrets_dict["spreadsheet"]
        data = conn.read(spreadsheet=url_planilha)
        return data
    except Exception as e:
        st.error(f"❌ Erro de Conexão: {e}")
        return None

# --- 4. EXECUÇÃO DO DASHBOARD ---
df = load_data()

if df is not None:
    # Tratamento de dados
    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
    
    # Filtra as ofertas mais recentes de cada loja
    df_atual = df.sort_values('Data').groupby('Loja').last().reset_index()

    # --- HEADER ---
    st.title("💎 Livelo Alpha Intel")
    st.markdown(f"**Última atualização do sistema:** {get_brasilia_time()}")
    
    # --- MÉTRICAS DE MERCADO (Requirement: Profit Intelligence) ---
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Parceiros Ativos", len(df_atual))
    
    with col2:
        top_row = df_atual.sort_values('Valor', ascending=False).iloc[0]
        st.metric("Melhor Acúmulo", f"{top_row['Valor']} pts", top_row['Loja'])
        
    with col3:
        # Valor médio do milheiro Livelo no mercado ~ R$ 35,00
        cashback_est = (top_row['Valor'] * 35 / 1000) * 100
        st.metric("Cashback Estimado", f"{cashback_est:.1f}%")
        
    with col4:
        st.metric("Recordes (ATH)", len(df[df['Valor'] >= 10]))

    st.divider()

    # --- ÁREA DE BUSCA E FILTROS ---
    st.sidebar.header("🎯 Filtros Alpha")
    search = st.sidebar.text_input("Buscar Loja", "")
    min_pts = st.sidebar.slider("Pontuação Mínima", 0, 20, 5)
    
    df_display = df_atual[df_atual['Valor'] >= min_pts]
    if search:
        df_display = df_display[df_display['Loja'].str.contains(search, case=False)]

    # --- VISUALIZAÇÃO ---
    tab1, tab2, tab3 = st.tabs(["🔥 Ofertas de Hoje", "📉 Histórico de Pontos", "🧮 Calculadora de Lucro"])

    with tab1:
        # Exibição em Grid de Cards
        cols = st.columns(4)
        for i, row in df_display.iterrows():
            with cols[i % 4]:
                with st.container(border=True):
                    st.image(row['Logo'], width=80)
                    st.subheader(row['Loja'])
                    color = "green" if row['Valor'] >= 10 else "blue"
                    st.markdown(f"### :{color}[{row['Pontos']}]")
                    st.caption(f"Tipo: {row['Tipo']}")

    with tab2:
        st.subheader("Análise Histórica")
        lojas_hist = st.multiselect("Selecione lojas para comparar histórico:", 
                                     df['Loja'].unique(), 
                                     default=[top_row['Loja']])
        if lojas_hist:
            fig = px.line(df[df['Loja'].isin(lojas_hist)], x='Data', y='Valor', color='Loja', markers=True)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        # Requirement: Mercado - Ferramenta de Decisão
        st.subheader("Calculadora de Oportunidade")
        c1, c2 = st.columns(2)
        with c1:
            valor_produto = st.number_input("Preço do Produto (R$)", value=1000.0)
            pts_loja = st.number_input("Pontos por Real da Loja", value=float(top_row['Valor']))
        with c2:
            valor_milheiro = st.slider("Valor de Venda do Milheiro (R$)", 20, 45, 35)
            pts_ganhos = valor_produto * pts_loja
            retorno_rs = (pts_ganhos / 1000) * valor_milheiro
            custo_final = valor_produto - retorno_rs
            
        st.divider()
        res1, res2, res3 = st.columns(3)
        res1.metric("Pontos a Receber", f"{pts_ganhos:,.0f}")
        res2.metric("Valor em R$", f"R$ {retorno_rs:.2f}")
        res3.metric("Custo Final Real", f"R$ {custo_final:.2f}", delta=f"{(retorno_rs/valor_produto)*-100:.1f}%")

else:
    st.info("💡 Dica: Certifique-se de que a Secret foi salva no painel do Streamlit Cloud.")