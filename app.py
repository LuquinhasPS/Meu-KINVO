import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date, datetime
import json
import pytz
import plotly.express as px
import os
import time

# --- Função para carregar a lista de tickers ATUALIZADA ---
def carregar_lista_de_ativos():
    """
    Carrega a lista de tickers do ficheiro JSON estruturado.
    """
    # Lista de ativos manuais que não vêm do scraping (opcional)
    ativos_manuais = [
        "IVVB11.SA", "GOLD11.SA", "SMAL11.SA", "BOVA11.SA"
    ]
    
    try:
        with open('all_tickers.json', 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        # Junta todas as listas de ativos numa só
        lista_completa = dados.get("acoes_b3", []) + dados.get("criptomoedas", []) + dados.get("etfs", []) + ativos_manuais
        
    except FileNotFoundError:
        # Se o ficheiro não existir, usa uma lista manual como fallback
        print("Aviso: Ficheiro 'all_tickers.json' não encontrado. Usando lista de ativos padrão.")
        lista_completa = [
            "BTC-USD", "ETH-USD", "PETR4.SA", "VALE3.SA", "ITUB4.SA", "GOLD11.SA"
        ]
        
    # Remove duplicados e ordena a lista
    lista_completa = sorted(list(set(lista_completa)))
    
    return ["Selecione ou pesquise um ativo..."] + lista_completa

# --- Configurações da Página ---
st.set_page_config(
    page_title="Meu Painel de Investimentos",
    layout="wide"
)

# --- Nossas Funções de Backend ---
def carregar_carteira():
    if not os.path.exists('carteira.json'): return {}
    try:
        with open('carteira.json', 'r', encoding='utf-8') as arquivo:
            return json.load(arquivo)
    except (FileNotFoundError, json.JSONDecodeError): return {}

def salvar_carteira(carteira):
    with open('carteira.json', 'w', encoding='utf-8') as arquivo:
        json.dump(carteira, arquivo, indent=4)

def buscar_taxa_dolar():
    try:
        dolar = yf.Ticker("BRL=X")
        return dolar.history(period="1d", auto_adjust=False)['Close'].iloc[-1]
    except Exception: return None

def buscar_preco_ativo(ticker_symbol, taxa_dolar):
    try:
        ticker = yf.Ticker(ticker_symbol)
        if "-USD" in ticker_symbol:
            preco_usd = ticker.info.get('regularMarketPrice')
            return preco_usd * taxa_dolar if preco_usd and taxa_dolar else None
        dados_hoje = ticker.history(period="1d", auto_adjust=False)
        return dados_hoje['Close'].iloc[-1] if not dados_hoje.empty else None
    except Exception: return None

def validar_ticker(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        return not ticker.history(period='1d').empty
    except Exception: return False

def colorir_rentabilidade(valor):
    if isinstance(valor, (int, float)):
        cor = 'green' if valor > 0 else 'red' if valor < 0 else 'white'
        return f'color: {cor}'
    return ''

# --- Formulário na Barra Lateral ---
with st.sidebar:
    st.header("Adicionar Nova Compra")
    
    lista_de_ativos_completa = carregar_lista_de_ativos()
    novo_ticker = st.selectbox("Ticker do Ativo", options=lista_de_ativos_completa)
    
    data_compra = st.date_input("Data da Compra", value=date.today())
    qtd_comprada = st.number_input("Quantidade Comprada", min_value=0.0, format="%.8f")
    preco_unitario = st.number_input("Preço Unitário (R$)", min_value=0.0, format="%.2f")
    
    botao_adicionar = st.button("Adicionar Compra")

    if botao_adicionar:
        if novo_ticker == lista_de_ativos_completa[0] or qtd_comprada <= 0 or preco_unitario <= 0:
            st.error("Por favor, selecione um ativo e preencha os outros campos.")
        elif not validar_ticker(novo_ticker):
            st.error(f"Ticker '{novo_ticker}' parece ser inválido. A transação não foi guardada.")
        else:
            nova_transacao = {"tipo": "compra", "data": data_compra.strftime("%Y-%m-%d"), "quantidade": qtd_comprada, "preco_unitario": preco_unitario}
            carteira_atual = carregar_carteira()
            ticker_upper = novo_ticker.upper()
            if ticker_upper in carteira_atual:
                carteira_atual[ticker_upper].append(nova_transacao)
            else:
                carteira_atual[ticker_upper] = [nova_transacao]
            salvar_carteira(carteira_atual)
            st.success("Compra adicionada com sucesso!")
            time.sleep(1)
            st.rerun()

# --- Início da Interface Principal ---
st.title("Meu Painel de Investimentos")
st.write(f"Dados atualizados em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

minha_carteira = carregar_carteira()

if minha_carteira:
    taxa_dolar_atual = buscar_taxa_dolar()
    dados_processados, lista_de_aportes = [], []
    for ticker, transacoes in minha_carteira.items():
        quantidade_total, custo_total = 0, 0.0
        for t in transacoes:
            if t["tipo"] == "compra":
                quantidade_total += t["quantidade"]
                custo_total += t["quantidade"] * t["preco_unitario"]
                lista_de_aportes.append({"Data": t["data"], "Ticker": ticker, "Valor do Aporte": t["quantidade"] * t["preco_unitario"]})
        if quantidade_total > 0:
            preco_medio = custo_total / quantidade_total
            preco_atual = buscar_preco_ativo(ticker, taxa_dolar_atual)
            valor_atual = preco_atual * quantidade_total if preco_atual else custo_total
            dados_processados.append({"Ativo": ticker, "Quantidade": quantidade_total, "Preço Médio (R$)": preco_medio, "Custo Total (R$)": custo_total, "Preço Atual (R$)": preco_atual, "Valor Atual (R$)": valor_atual})
    
    df_carteira = pd.DataFrame(dados_processados)
    
    if not df_carteira.empty:
        df_carteira['Lucro/Prejuízo (R$)'] = df_carteira['Valor Atual (R$)'] - df_carteira['Custo Total (R$)']
        df_carteira['Rentabilidade (%)'] = (df_carteira['Lucro/Prejuízo (R$)'] / df_carteira['Custo Total (R$)'] * 100).fillna(0)
        def categorizar_ativo(ticker):
            if "-USD" in ticker: return "Criptomoeda"
            elif "11.SA" in ticker: return "ETF"
            else: return "Ação"
        df_carteira['Tipo'] = df_carteira['Ativo'].apply(categorizar_ativo)
        
        st.subheader("Evolução do Património")
        nome_ficheiro_historico = 'historico_portfolio.csv'
        total_atual_completo = df_carteira["Valor Atual (R$)"].sum()
        hoje = date.today().strftime('%Y-%m-%d')
        if os.path.exists(nome_ficheiro_historico) and os.path.getsize(nome_ficheiro_historico) > 0:
            df_historico = pd.read_csv(nome_ficheiro_historico)
            if hoje not in df_historico['Data'].values:
                novo_registo = pd.DataFrame([{'Data': hoje, 'ValorTotal': total_atual_completo}])
                df_historico = pd.concat([df_historico, novo_registo], ignore_index=True)
        else:
            df_historico = pd.DataFrame([{'Data': hoje, 'ValorTotal': total_atual_completo}])
        df_historico.to_csv(nome_ficheiro_historico, index=False)
        fig_historico = px.line(df_historico, x='Data', y='ValorTotal', title='Valor Total da Carteira ao Longo do Tempo', markers=True)
        st.plotly_chart(fig_historico, use_container_width=True)
        
        st.subheader("Filtros")
        tipos_de_ativo = df_carteira['Tipo'].unique().tolist()
        tipos_selecionados = st.multiselect("Filtrar por Tipo de Ativo:", options=tipos_de_ativo, default=tipos_de_ativo)
        df_filtrado = df_carteira[df_carteira['Tipo'].isin(tipos_selecionados)]
        
        st.subheader("Resumo da Carteira")
        total_investido = df_filtrado["Custo Total (R$)"].sum()
        total_atual_filtrado = df_filtrado["Valor Atual (R$)"].sum()
        lucro_prejuizo_total = total_atual_filtrado - total_investido
        rentabilidade_total = (lucro_prejuizo_total / total_investido) * 100 if total_investido > 0 else 0
        col1, col2, col3 = st.columns(3)
        col1.metric("Valor Total Investido", f"R$ {total_investido:,.2f}")
        col2.metric("Valor Atual da Carteira", f"R$ {total_atual_filtrado:,.2f}", f"{lucro_prejuizo_total:,.2f} R$")
        col3.metric("Rentabilidade Total", f"{rentabilidade_total:.2f}%", f"{rentabilidade_total:.2f}%")
        
        st.subheader("Detalhes dos Ativos")
        df_para_exibir = df_filtrado[[ "Ativo", "Tipo", "Quantidade", "Preço Médio (R$)", "Custo Total (R$)", "Preço Atual (R$)", "Valor Atual (R$)", "Lucro/Prejuízo (R$)", "Rentabilidade (%)" ]]
        formatador = {"Quantidade": "{:,.8f}", "Preço Médio (R$)": "R$ {:,.2f}", "Custo Total (R$)": "R$ {:,.2f}", "Preço Atual (R$)": "R$ {:,.2f}", "Valor Atual (R$)": "R$ {:,.2f}", "Lucro/Prejuízo (R$)": "R$ {:+,.2f}", "Rentabilidade (%)": "{:+.2f}%"}
        st.dataframe(df_para_exibir.style.apply(lambda col: col.map(colorir_rentabilidade), subset=['Lucro/Prejuízo (R$)', 'Rentabilidade (%)']).format(formatador, decimal=",", thousands="."), use_container_width=True)
        
        st.subheader("Análise de Aportes")
        if lista_de_aportes:
            col_graf_aportes, col_lista_aportes = st.columns(2)
            with col_graf_aportes:
                df_aportes = pd.DataFrame(lista_de_aportes)
                df_aportes['Data'] = pd.to_datetime(df_aportes['Data'])
                aportes_mensais = df_aportes.set_index('Data').groupby(pd.Grouper(freq='M'))['Valor do Aporte'].sum().reset_index()
                aportes_mensais['Mês'] = aportes_mensais['Data'].dt.strftime('%Y-%m')
                fig_aportes = px.bar(aportes_mensais, x='Mês', y='Valor do Aporte', title='Aportes Mensais', text_auto='.2s')
                st.plotly_chart(fig_aportes, use_container_width=True)
            with col_lista_aportes:
                st.write("Histórico de Aportes (Dia a Dia)")
                df_aportes_detalhado = pd.DataFrame(lista_de_aportes)
                df_aportes_detalhado.sort_values(by="Data", ascending=False, inplace=True)
                df_aportes_detalhado['Valor do Aporte'] = df_aportes_detalhado['Valor do Aporte'].map('R$ {:,.2f}'.format)
                st.dataframe(df_aportes_detalhado.rename(columns={'Ticker': 'Ativo'}), use_container_width=True, hide_index=True)
        
        st.subheader("Análise Gráfica da Carteira")
        if not df_filtrado.empty:
            col_graf1, col_graf2 = st.columns(2)
            fig_alocacao_ativo = px.pie(df_filtrado, values='Valor Atual (R$)', names='Ativo', title='Alocação por Ativo')
            col_graf1.plotly_chart(fig_alocacao_ativo, use_container_width=True)
            df_agrupado_tipo = df_filtrado.groupby('Tipo')['Valor Atual (R$)'].sum().reset_index()
            fig_alocacao_tipo = px.pie(df_agrupado_tipo, values='Valor Atual (R$)', names='Tipo', title='Alocação por Tipo de Ativo')
            col_graf2.plotly_chart(fig_alocacao_tipo, use_container_width=True)
else:
    st.info("A sua carteira está vazia. Adicione a sua primeira compra através do formulário na barra lateral.")