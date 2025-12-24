import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta, timezone

# --- CONFIGURAÇÃO DA UI ---
st.set_page_config(page_title="Alpha Points Intel", page_icon="💎", layout="wide")

def get_now_br():
    return datetime.now(timezone(timedelta(hours=-3)))

# --- ESTILIZAÇÃO CSS CUSTOMIZADA ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .card { background-color: #ffffff; padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- CARREGAMENTO DE DADOS ---
@st.cache_data(ttl=300)
def load_market_data():
    try:
        # 1. Pegamos os dados brutos do TOML
        # Usamos dict() para criar uma cópia mutável
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        
        # 2. Extraímos a URL da planilha antes de limpar o dicionário
        url = creds_dict.get("spreadsheet")
        
        # 3. Sanitização da Private Key (O erro original de 65 caracteres)
        # Forçamos a conversão de \\n literal para quebra de linha real
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n").strip()
        
        # 4. Criamos a conexão passando o dicionário como um ÚNICO argumento
        # Isso evita que o 'project_id' ou 'spreadsheet' sejam interpretados como argumentos de função
        conn = st.connection(
            "gsheets",
            type=GSheetsConnection,
            service_account_info=creds_dict
        )
        
        # 5. Lemos a planilha usando a URL que extraímos
        df = conn.read(spreadsheet=url)
        
        # Limpeza e Tipagem
        if df is not None:
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
            df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
            return df
            
    except Exception as e:
        st.error(f"❌ Erro na extração de dados: {e}")
        return None

df = load_market_data()

if df is not None:
    # 1. Processamento para Visão "Real Time"
    df_latest = df.sort_values('Data').groupby('Loja').last().reset_index()
    
    # --- HEADER DO PRODUTO ---
    st.title("💎 Alpha Points Intelligence")
    st.caption(f"Monitoramento Profissional Livelo | Atualizado em: {get_now_br().strftime('%d/%m/%Y %H:%M')}")
    st.divider()

    # --- DASHBOARD DE MÉTRICAS (MARKET READY) ---
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        st.metric("Lojas Monitoradas", len(df_latest))
    with m2:
        top_offer = df_latest.sort_values('Valor', ascending=False).iloc[0]
        st.metric("Melhor Acúmulo", f"{top_offer['Valor']} pts", top_offer['Loja'])
    with m3:
        # Inteligência de Mercado: Valor de Mercado Estimado
        lucro_potencial = (top_offer['Valor'] * 35 / 1000) * 100
        st.metric("Cashback Máximo Est.", f"{lucro_potencial:.1f}%")
    with m4:
        ath_count = len(df[df['Valor'] >= 10])
        st.metric("Recordes Ativos", ath_count)

    # --- FILTROS E BUSCA ---
    st.sidebar.header("🎯 Filtros de Oportunidade")
    search = st.sidebar.text_input("🔍 Buscar Loja ou Marca")
    min_points = st.sidebar.slider("Pontuação Mínima", 1, 25, 5)
    
    df_view = df_latest[df_latest['Valor'] >= min_points]
    if search:
        df_view = df_view[df_view['Loja'].str.contains(search, case=False)]

    # --- ÁREA DE CONTEÚDO ---
    tab_now, tab_hist, tab_calc = st.tabs(["🔥 Ofertas Atuais", "📈 Análise Histórica", "🧮 Calculadora de Lucro"])

    with tab_now:
        # Exibição em Grid Visual
        st.subheader("Oportunidades em Destaque")
        cols = st.columns(4)
        for i, row in df_view.iterrows():
            with cols[i % 4]:
                with st.container(border=True):
                    st.image(row['Logo'], width=70)
                    st.markdown(f"**{row['Loja']}**")
                    color = "green" if row['Valor'] >= 10 else "blue"
                    st.markdown(f"### :{color}[{row['Pontos']}]")
                    st.caption(f"Válido para: {row['Tipo']}")

    with tab_hist:
        st.subheader("Evolução de Pontos (ATH Tracker)")
        lojas_comparar = st.multiselect("Selecione os parceiros para analisar", df['Loja'].unique(), default=df['Loja'].unique()[:2])
        if lojas_comparar:
            fig = px.line(df[df['Loja'].isin(lojas_comparar)], x='Data', y='Valor', color='Loja', markers=True, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

    with tab_calc:
        st.subheader("🧮 Calculadora Alpha de Arbitragem")
        c1, c2 = st.columns(2)
        with c1:
            valor_item = st.number_input("Preço do Produto (R$)", value=1000.0, step=100.0)
            pts_real = st.number_input("Pontos por Real da Oferta", value=float(top_offer['Valor']))
        with c2:
            venda_milheiro = st.slider("Preço de Venda das Milhas (R$ / 1.000)", 20.0, 45.0, 35.0)
            
            pontos_totais = valor_item * pts_real
            valor_recebido = (pontos_totais / 1000) * venda_milheiro
            custo_efetivo = valor_item - valor_recebido
            
        st.divider()
        r1, r2, r3 = st.columns(3)
        r1.metric("Pontos a Gerar", f"{pontos_totais:,.0f}")
        r2.metric("Valor de Volta (R$)", f"R$ {valor_recebido:.2f}")
        r3.success(f"Custo Final: R$ {custo_efetivo:.2f}")

else:
    st.warning("⚠️ Aguardando dados... Verifique se o formato das Secrets está correto.")

st.markdown("---")
st.caption("Alpha Points Intel © 2025 - Ferramenta de Análise de Fidelidade")