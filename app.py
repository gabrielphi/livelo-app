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
        # 1. Carrega o dicionário e garante que é mutável
        creds_dict = dict(st.secrets["connections"]["gsheets"])

        # 2. Tratamento Robusto da Private Key
        if "private_key" in creds_dict:
            # Pegamos a chave e removemos espaços/quebras extras nas extremidades
            key = creds_dict["private_key"].strip()
            
            # CORREÇÃO: Todo o tratamento deve estar dentro deste IF
            # Primeiro: Resolvemos as quebras de linha literais
            key = key.replace("\\n", "\n")
            
            # Segundo: Removemos aspas extras que o TOML às vezes insere por erro de colagem
            key = key.replace('"', '').replace("'", "")
            
            # Terceiro: Garantimos os delimitadores padrão (essencial para o Base64)
            if not key.startswith("-----BEGIN PRIVATE KEY-----"):
                key = "-----BEGIN PRIVATE KEY-----\n" + key
            if not key.endswith("-----END PRIVATE KEY-----"):
                key = key + "\n-----END PRIVATE KEY-----"
            
            # Devolvemos para o dicionário
            creds_dict["private_key"] = key
        else:
            st.error("Chave 'private_key' não encontrada no Secrets.")
            return None

        # 3. Escopo e Autenticação
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        
        # 4. Acessa a planilha e limpa dados
        sheet = client.open_by_url(creds_dict["spreadsheet"]).get_worksheet(0)
        data = sheet.get_all_records()
        
        df = pd.DataFrame(data)
        
        # 5. Tratamento de colunas (opcional mas recomendado)
        if not df.empty:
            # Remove espaços nos nomes das colunas que vêm do Excel/Sheets
            df.columns = [col.strip() for col in df.columns]
            return df
        
        return None

    except Exception as e:
        # Log detalhado do erro para facilitar o debug
        st.error(f"❌ Erro na conexão: {str(e)}")
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