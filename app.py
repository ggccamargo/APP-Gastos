import streamlit as st
import pandas as pd
from datetime import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Controle de Gastos V2", page_icon="📊", layout="wide")
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
tab_novo, tab_historico, tab_dashboard = st.tabs(["➕ Novo Lançamento", "📋 Histórico e Edição", "📊 Dashboard Inteligente"])

with tab_novo:
    with st.form("form_novo_gasto"):
        st.subheader("Registrar Novo Gasto")
        col1, col2 = st.columns(2)
        with col1:
            data = st.date_input("Data", datetime.today()).strftime("%d/%m/%Y")
            categoria = st.selectbox("Categoria", [
                "Camargo Gestão Imobiliária", 
                "Pessoal", 
                "Veículo (Jeep Compass)", 
                "Alimentação", 
                "Moradia", 
                "Outros"
            ])
        with col2:
            valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f", step=10.0)
            descricao = st.text_input("Descrição")
            
        if st.form_submit_button("Salvar Gasto"):
            aba.append_row([data, descricao, categoria, float(valor)])
            st.success("Gasto salvo na nuvem com sucesso!")
            st.rerun()

with tab_historico:
    st.subheader("Gerenciar Lançamentos")
    st.write("Edite valores, corrija textos ou clique na lixeira para excluir uma linha. Depois, clique em Salvar.")
    
    colunas_exibicao = ["Data", "Descrição", "Categoria", "Valor (R$)"]
    
    if not df.empty:
        df_editado = st.data_editor(df[colunas_exibicao], num_rows="dynamic", use_container_width=True)
        
        if st.button("💾 Salvar Alterações na Nuvem", type="primary"):
            aba.clear()
            aba.append_row(colunas_exibicao)
            aba.append_rows(df_editado.values.tolist())
            st.success("Planilha atualizada perfeitamente!")
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
            mes_selecionado = st.selectbox("Filtrar por Mês", sorted(meses_disponiveis), format_func=lambda x: f"{int(x):02d}")
        with col_f2:
            ano_selecionado = st.selectbox("Filtrar por Ano", sorted(anos_disponiveis))
            
        df_filtrado = df[(df['Data_dt'].dt.month == mes_selecionado) & (df['Data_dt'].dt.year == ano_selecionado)]
        
        if not df_filtrado.empty:
            total_imobiliaria = df_filtrado[df_filtrado['Categoria'] == 'Camargo Gestão Imobiliária']['Valor (R$)'].sum()
            total_pessoal = df_filtrado[df_filtrado['Categoria'] != 'Camargo Gestão Imobiliária']['Valor (R$)'].sum()
            total_geral = df_filtrado['Valor (R$)'].sum()
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total do Mês", f"R$ {total_geral:.2f}")
            col_m2.metric("Camargo Gestão", f"R$ {total_imobiliaria:.2f}")
            col_m3.metric("Pessoal/Outros", f"R$ {total_pessoal:.2f}")
            
            st.divider()
            st.subheader("Distribuição de Custos")
            resumo_cat = df_filtrado.groupby('Categoria')['Valor (R$)'].sum().reset_index()
            st.bar_chart(resumo_cat.set_index('Categoria'))
        else:
            st.warning("Nenhum gasto encontrado para este mês/ano.")
    else:
        st.info("Adicione dados para gerar os gráficos.")
