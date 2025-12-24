import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, timezone

# --- CONFIGURAÇÃO DA UI ---
st.set_page_config(page_title="Alpha Points Intel", page_icon="💎", layout="wide")

def get_now_br():
    return datetime.now(timezone(timedelta(hours=-3)))

# --- FUNÇÃO DE CONEXÃO DIRETA (SEM ST.CONNECTION) ---
@st.cache_data(ttl=300)
def load_market_data():
    try:
        # 1. Recuperar segredos do Streamlit
        # Certifique-se de que no seu secrets.toml as chaves estão identadas corretamente
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        
        # 2. Definir o Escopo
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # 3. Formatar a Private Key (correção de quebras de linha)
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        # 4. Autenticação direta com Google Auth
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # 5. Abrir a planilha pela URL
        # Extraímos a URL que você forneceu no TOML
        spreadsheet_url = creds_dict.get("spreadsheet")
        sheet = client.open_by_url(spreadsheet_url).get_worksheet(0) # Abre a primeira aba
        
        # 6. Converter para DataFrame
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Limpeza e Tipagem
        if not df.empty:
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
            return df
        return None
            
    except Exception as e:
        st.error(f"❌ Erro crítico na conexão: {e}")
        return None

# --- EXECUÇÃO ---
df = load_market_data()

if df is not None:
    # 1. Processamento para Visão "Real Time"
    df_latest = df.sort_values('Data').groupby('Loja').last().reset_index()
    
    st.title("💎 Alpha Points Intelligence")
    st.caption(f"Monitoramento Profissional Livelo | Atualizado em: {get_now_br().strftime('%d/%m/%Y %H:%M')}")
    st.divider()

    # --- DASHBOARD DE MÉTRICAS ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Lojas Monitoradas", len(df_latest))
    with m2:
        top_offer = df_latest.sort_values('Valor', ascending=False).iloc[0]
        st.metric("Melhor Acúmulo", f"{top_offer['Valor']} pts", top_offer['Loja'])
    with m3:
        lucro_potencial = (top_offer['Valor'] * 35 / 1000) * 100
        st.metric("Cashback Máximo Est.", f"{lucro_potencial:.1f}%")
    with m4:
        ath_count = len(df[df['Valor'] >= 10])
        st.metric("Recordes Ativos", ath_count)

    # --- ABAS DE CONTEÚDO ---
    tab_now, tab_hist, tab_calc = st.tabs(["🔥 Ofertas Atuais", "📈 Análise Histórica", "🧮 Calculadora"])

    with tab_now:
        st.subheader("Oportunidades em Destaque")
        cols = st.columns(4)
        for i, row in df_latest.iterrows():
            with cols[i % 4]:
                with st.container(border=True):
                    # Tenta carregar imagem, se falhar usa placeholder
                    if 'Logo' in row and pd.notnull(row['Logo']):
                        st.image(row['Logo'], width=70)
                    st.markdown(f"**{row['Loja']}**")
                    st.markdown(f"### :green[{row['Valor']} pts]")
                    st.caption(f"Tipo: {row.get('Tipo', 'N/A')}")

    with tab_hist:
        st.subheader("Evolução de Pontos")
        lojas = st.multiselect("Selecione parceiros", df['Loja'].unique(), default=df['Loja'].unique()[:2])
        if lojas:
            fig = px.line(df[df['Lo_ja'].isin(lojas)], x='Data', y='Valor', color='Loja', markers=True)
            st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("⚠️ Não foi possível carregar os dados. Verifique as credenciais no Secrets.")