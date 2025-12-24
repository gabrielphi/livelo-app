import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone

# --- CONFIGURAÇÃO DA UI ---
st.set_page_config(page_title="Alpha Points Intel", page_icon="💎", layout="wide")

# CSS para melhorar a estética dos cards
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #155724; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px 5px 0 0; padding: 10px; }
    .stTabs [aria-selected="true"] { background-color: #007bff; color: white !important; }
    </style>
""", unsafe_allow_html=True)

def get_now_br():
    return datetime.now(timezone(timedelta(hours=-3)))

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
            # Garantir que Data seja datetime e Valor seja numérico
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
            df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
            return df
        return None
    except Exception as e:
        st.error(f"❌ Erro na conexão: {str(e)}")
        return None

# --- EXECUÇÃO ---
df = load_market_data()

if df is not None:
    # --- SIDEBAR DE FILTROS ---
    st.sidebar.image("https://www.livelo.com.br/file/general/livelo-logo.svg", width=150)
    st.sidebar.title("Filtros de Busca")
    
    min_pts = st.sidebar.slider("Pontuação Mínima", 0, int(df['Valor'].max()), 0)
    search_loja = st.sidebar.text_input("Buscar Loja", "")
    
    # Filtragem Global
    df_filtered = df[df['Valor'] >= min_pts]
    if search_loja:
        df_filtered = df_filtered[df_filtered['Loja'].str.contains(search_loja, case=False)]
    
    # Processamento Real Time (Última atualização de cada loja)
    df_latest = df_filtered.sort_values('Data').groupby('Loja').last().reset_index()

    # --- HEADER ---
    st.title("💎 Alpha Points Intelligence")
    st.caption(f"Monitoramento Profissional Livelo | {get_now_br().strftime('%d/%m/%Y %H:%M')}")
    
    # --- MÉTRICAS DE TOPO ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Parceiros Ativos", len(df_latest))
    with m2:
        top_offer = df_latest.sort_values('Valor', ascending=False).iloc[0]
        st.metric("Melhor Acúmulo", f"{top_offer['Valor']} pts", top_offer['Loja'])
    with m3:
        # Cálculo de cashback baseado em milheiro de R$ 35,00
        cashback_est = (top_offer['Valor'] * 35 / 1000) * 100
        st.metric("Cashback Máximo", f"{cashback_est:.1f}%", help="Considerando venda de pontos a R$ 35/milheiro")
    with m4:
        df_7days = df[df['Data'] > (get_now_br() - timedelta(days=7))]
        st.metric("Atualizações (7d)", len(df_7days))

    st.divider()

    # --- TABS ---
    tab_now, tab_hist, tab_calc = st.tabs(["🔥 Oportunidades Atuais", "📈 Evolução Histórica", "🧮 Calculadora de Lucro"])

    with tab_now:
        # Layout em Grid para evitar listas infinitas
        if not df_latest.empty:
            cols = st.columns(4)
            for i, row in df_latest.iterrows():
                with cols[i % 4]:
                    with st.container(border=True):
                        # Centralizando imagem e conteúdo
                        if 'Logo' in row and pd.notnull(row['Logo']):
                            st.image(row['Logo'], width=80)
                        st.subheader(f"{row['Loja']}")
                        st.markdown(f"## :green[{row['Valor']} pts]")
                        st.caption(f"📅 {row['Data'].strftime('%d/%m %H:%M')}")
                        st.info(f"Tipo: {row.get('Tipo', 'Padrão')}")
        else:
            st.warning("Nenhuma oferta encontrada para os filtros aplicados.")

    with tab_hist:
        st.subheader("Análise de Tendência")
        selected_lojas = st.multiselect(
            "Selecione as lojas para comparar", 
            df['Loja'].unique(), 
            default=df['Loja'].unique()[:3]
        )
        
        if selected_lojas:
            df_plot = df[df['Loja'].isin(selected_lojas)].sort_values('Data')
            # O erro KeyError: 'Lo_ja' foi corrigido aqui para 'Loja'
            fig = px.line(
                df_plot, 
                x='Data', 
                y='Valor', 
                color='Loja', 
                markers=True,
                template="plotly_white",
                labels={'Valor': 'Pontos por Real', 'Data': 'Data da Verificação'}
            )
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

    with tab_calc:
        st.subheader("Simulador de Compra")
        c1, c2 = st.columns(2)
        
        with c1:
            valor_produto = st.number_input("Valor do Produto (R$)", min_value=1.0, value=1000.0)
            pontos_por_real = st.selectbox("Parceiro (Pontuação)", 
                                         options=df_latest['Loja'].tolist(),
                                         index=0)
            pts_selecionados = df_latest[df_latest['Loja'] == pontos_por_real]['Valor'].values[0]
            st.write(f"Pontuação atual deste parceiro: **{pts_selecionados} pts/$1**")

        with c2:
            valor_milheiro = st.slider("Valor de Venda do Milheiro (R$)", 15.0, 45.0, 35.0)
            
            total_pontos = valor_produto * pts_selecionados
            valor_em_pontos = (total_pontos / 1000) * valor_milheiro
            custo_final = valor_produto - valor_em_pontos
            desconto_perc = (valor_em_pontos / valor_produto) * 100

        st.divider()
        res1, res2, res3 = st.columns(3)
        res1.metric("Pontos a Receber", f"{int(total_pontos):,}")
        res2.metric("Valor de Retorno (Cashback)", f"R$ {valor_em_pontos:.2f}")
        res3.metric("Custo Final Efetivo", f"R$ {custo_final:.2f}", f"-{desconto_perc:.1f}%")

else:
    st.error("⚠️ Erro crítico: O DataFrame não pôde ser carregado. Verifique o log do console.")