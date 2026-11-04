import streamlit as st
import pandas as pd
from datetime import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Controle de Gastos", page_icon="📊")
st.title("Controle e Identificação de Gastos 📊")

# --- CONEXÃO COM O GOOGLE SHEETS ---
@st.cache_resource
def conectar_planilha():
    # Puxa a chave secreta que vamos colar no painel do Streamlit
    credenciais_json = json.loads(st.secrets["google"]["credenciais"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credenciais_json, scope)
    client = gspread.authorize(creds)

    # Conecta direto na planilha do seu Drive
    url = "https://docs.google.com/spreadsheets/d/1MxAYCiQEOUz7exr-ZHh2v2khgMdZQoFy9dFQZwo6roU/edit"
    return client.open_by_url(url).sheet1

try:
    aba = conectar_planilha()
except Exception as e:
    st.error("Aguardando configuração da chave no painel do Streamlit...")
    st.stop()

# --- INTERFACE E LÓGICA ---
with st.form("form_novo_gasto"):
    st.subheader("Adicionar Novo Gasto")

    col1, col2 = st.columns(2)
    with col1:
        # Formata a data para o padrão brasileiro DD/MM/AAAA
        data = st.date_input("Data", datetime.today()).strftime("%d/%m/%Y")
        categoria = st.selectbox("Categoria", ["Imobiliária", "Pessoal", "Veículo", "Alimentação", "Moradia", "Outros"])
    with col2:
        valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f", step=10.0)
        descricao = st.text_input("Descrição (Ex: Gasolina, Anúncios, Mercado)")

    submit = st.form_submit_button("Salvar Gasto")

    if submit:
        nova_linha = [data, descricao, categoria, float(valor)]
        aba.append_row(nova_linha)
        st.success("Gasto salvo com sucesso na nuvem!")
        st.rerun()

# --- VISUALIZAÇÃO ---
st.divider()
st.subheader("Histórico e Resumo")

# Puxa os dados da planilha usando a primeira linha como cabeçalho
dados = aba.get_all_records()

if dados:
    df_gastos = pd.DataFrame(dados)
    df_gastos['Valor (R$)'] = pd.to_numeric(df_gastos['Valor (R$)'], errors='coerce')

    st.dataframe(df_gastos, use_container_width=True)

    st.subheader("Gastos por Categoria")
    resumo = df_gastos.groupby('Categoria')['Valor (R$)'].sum().reset_index()
    st.bar_chart(resumo, x='Categoria', y='Valor (R$)')

    total = df_gastos['Valor (R$)'].sum()
    st.metric(label="Total Gasto", value=f"R$ {total:.2f}")
else:
    st.info("Planilha vazia. Adicione o primeiro gasto acima!")