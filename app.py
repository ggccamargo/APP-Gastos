import streamlit as st
import pandas as pd
from datetime import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px

st.set_page_config(page_title="Controle de Gastos", page_icon="📊", layout="wide")
st.title("Controle e Identificação de Gastos 📊")

# --- CONEXÃO COM O GOOGLE SHEETS ---
@st.cache_resource
def conectar_planilha():
    credenciais_json = json.loads(st.secrets["google"]["credenciais"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciais_json, scope)
    client = gspread.authorize(creds)
    url = "https://docs.google.com/spreadsheets/d/1MxAYCiQEOUz7exr-ZHh2v2khgMdZQoFy9dFQZwo6roU/edit"
    return client.open_by_url(url).sheet1

try:
    aba = conectar_planilha()
except Exception as e:
    st.error(f"Erro de conexão: {e}")
    st.stop()

# --- CARREGAMENTO DE DADOS ---
dados = aba.get_all_records()
if dados:
    df = pd.DataFrame(dados)
    df['Valor (R$)'] = pd.to_numeric(df['Valor (R$)'], errors='coerce')
    df['Data_dt'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
else:
    df = pd.DataFrame(columns=["Data", "Descrição", "Categoria", "Valor (R$)"])
    df['Data_dt'] = pd.Series(dtype='datetime64[ns]')

# --- INTERFACE COM ABAS ---
tab_novo, tab_historico, tab_dashboard = st.tabs(["➕ Novo", "📋 Histórico", "📊 Dashboard"])

with tab_novo:
    with st.form("form_novo_gasto"):
        st.subheader("Registrar Novo Gasto")
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data", datetime.today()).strftime("%d/%m/%Y")
            categoria = st.selectbox("Categoria", [
                "Casa", 
                "Crianças", 
                "Alimentação", 
                "Carro", 
                "Compras", 
                "Viagens"
            ])
        with col2:
            # Novo campo de texto preparado para ler os dois últimos dígitos como centavos
            valor_input = st.text_input("Valor (Ex: digite 1500 para R$ 15,00)")
            descricao = st.text_input("Descrição")
            
        if st.form_submit_button("Salvar Gasto"):
            try:
                # Remove letras, pontos ou vírgulas se o usuário digitar sem querer
                apenas_numeros = ''.join(filter(str.isdigit, str(valor_input)))
                
                if apenas_numeros == "":
                    st.error("Por favor, digite um valor válido.")
                else:
                    # A mágica dos centavos: divide por 100
                    valor_final = float(apenas_numeros) / 100.0
                    
                    aba.append_row([data, descricao, categoria, valor_final])
                    st.success(f"Gasto de R$ {valor_final:.2f} salvo com sucesso!")
                    st.rerun()
            except Exception as e:
                st.error("Erro ao formatar o valor. Tente digitar apenas os números.")

with tab_historico:
    st.subheader("Gerenciar Lançamentos")
    st.write("Edite valores, corrija textos ou clique na lixeira para excluir uma linha.")
    
    colunas_exibicao = ["Data", "Descrição", "Categoria", "Valor (R$)"]
    
    if not df.empty:
        df_editado = st.data_editor(df[colunas_exibicao], num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Salvar Alterações", type="primary"):
            aba.clear()
            aba.append_row(colunas_exibicao)
            aba.append_rows(df_editado.values.tolist())
            st.success("Planilha atualizada!")
            st.rerun()
    else:
        st.info("Nenhum gasto para editar ainda.")

with tab_dashboard:
    st.subheader("Visão Geral do Orçamento")
    
    if not df.empty:
        col_f1, col_f2 = st.columns(2)
        meses_disponiveis = df['Data_dt'].dt.month.dropna().unique()
        anos_disponiveis = df['Data_dt'].dt.year.dropna().unique()
        
        with col_f1:
            mes_selecionado = st.selectbox("Mês", sorted(meses_disponiveis), format_func=lambda x: f"{int(x):02d}")
        with col_f2:
            ano_selecionado = st.selectbox("Ano", sorted(anos_disponiveis))
            
        df_filtrado = df[(df['Data_dt'].dt.month == mes_selecionado) & (df['Data_dt'].dt.year == ano_selecionado)]
        
        if not df_filtrado.empty:
            total_geral = df_filtrado['Valor (R$)'].sum()
            st.metric("Total do Mês", f"R$ {total_geral:.2f}")
            
            st.divider()
            
            # NOVO GRÁFICO DE PIZZA
            resumo_cat = df_filtrado.groupby('Categoria')['Valor (R$)'].sum().reset_index()
            fig = px.pie(
                resumo_cat, 
                values='Valor (R$)', 
                names='Categoria', 
                title="Distribuição por Categoria",
                hole=0.4, # Deixa com um visual de rosca moderno (Donut Chart)
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Nenhum gasto encontrado para este mês.")
    else:
        st.info("Adicione dados para gerar os gráficos.")
