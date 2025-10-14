import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date, datetime
import json
import plotly.express as px
import os
import time
from io import StringIO
import requests

# --- Funções de Carregamento ---
def carregar_lista_de_ativos():
    ativos_manuais = ["IVVB11.SA", "GOLD11.SA", "SMAL11.SA", "BOVA11.SA"]
    try:
        with open('data/all_tickers.json', 'r', encoding='utf-8') as f:
            dados = json.load(f)
        lista_completa = dados.get("acoes_b3", []) + dados.get("criptomoedas", []) + dados.get("etfs", []) + ativos_manuais
    except FileNotFoundError:
        lista_completa = ["BTC-USD", "ETH-USD", "PETR4.SA", "VALE3.SA", "ITUB4.SA", "GOLD11.SA"]
    return ["Selecione ou pesquise um ativo..."] + sorted(list(set(lista_completa)))

# --- Configurações da Página ---
st.set_page_config(page_title="Meu Painel de Investimentos", layout="wide")

# --- Nossas Funções de Backend ---
def carregar_carteira():
    caminho = 'data/carteira.json'
    if not os.path.exists(caminho): return {}
    try:
        with open(caminho, 'r', encoding='utf-8') as arquivo:
            return json.load(arquivo)
    except (FileNotFoundError, json.JSONDecodeError): return {}

def salvar_carteira(carteira):
    with open('data/carteira.json', 'w', encoding='utf-8') as arquivo:
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

# --- VERSÃO FINAL E VALIDADA DA FUNÇÃO DE DIVIDENDOS ---
@st.cache_data(ttl=3600)
def buscar_info_dividendos_detalhados(ticker_symbol):
    if not ticker_symbol.endswith('.SA'):
        return []

    proventos_finais = []
    hoje = date.today()
    
    try:
        # Fonte Única e Primária: Fundamentus
        ticker_sem_sa = ticker_symbol.replace(".SA", "")
        url = f"https://www.fundamentus.com.br/proventos.php?papel={ticker_sem_sa}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tabelas = pd.read_html(StringIO(response.text), decimal=',', thousands='.')
        
        if not tabelas:
            return []

        df = tabelas[0].rename(columns={"Data": "data_ex", "Valor": "valor", "Data de Pagamento": "data_pag"})
        df['data_ex'] = pd.to_datetime(df['data_ex'], format='%d/%m/%Y').dt.date
        df['data_pag'] = pd.to_datetime(df['data_pag'], format='%d/%m/%Y', errors='coerce').dt.date

        # Lógica de Classificação Aplicada Diretamente
        for _, provento in df.iterrows():
            status = None
            data_ex = provento['data_ex']
            data_pag = provento['data_pag']

            if pd.notna(data_pag) and data_pag < hoje:
                status = "Recebido" # Será filtrado mais tarde, mas é bom classificar
            elif data_ex < hoje and (pd.isna(data_pag) or data_pag >= hoje):
                status = "Qualificado"
            elif data_ex > hoje:
                status = "Provisionado"
            
            if status:
                proventos_finais.append({
                    "valor": provento['valor'], "data_ex": data_ex,
                    "data_pag": data_pag, "status": status
                })
        return proventos_finais
    except Exception:
        return []

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

def colorir_status(status):
    if status == 'Qualificado': return 'color: lightgreen'
    elif status == 'Provisionado': return 'color: lightblue'
    elif status == 'Recebido': return 'color: grey'
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
    dados_processados, lista_de_aportes, proventos_detalhados = [], [], []
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
            
            valor_total_qualificado_e_provisionado = 0
            
            lista_proventos = buscar_info_dividendos_detalhados(ticker)
            for provento in lista_proventos:
                # Mostramos todos os proventos não recebidos na tabela de detalhes
                if provento['status'] in ['Qualificado', 'Provisionado']:
                    quantidade_habilitada = sum(t['quantidade'] for t in transacoes if t['tipo'] == 'compra' and datetime.strptime(t["data"], "%Y-%m-%d").date() < provento['data_ex'])
                    if quantidade_habilitada > 0:
                        valor_a_receber = quantidade_habilitada * provento['valor']
                        proventos_detalhados.append({
                            "Ativo": ticker, "Status": provento['status'], "Valor por Ação (R$)": provento['valor'],
                            "Data Ex": provento['data_ex'], "Data Pagamento": provento['data_pag'], "Total a Receber (R$)": valor_a_receber
                        })
                        # O resumo no topo só conta os proventos já garantidos ("Qualificado")
                        if provento['status'] == 'Qualificado':
                            valor_total_qualificado_e_provisionado += valor_a_receber
            
            dados_processados.append({
                "Ativo": ticker, "Quantidade": quantidade_total, "Preço Médio (R$)": preco_medio,
                "Custo Total (R$)": custo_total, "Preço Atual (R$)": preco_atual, "Valor Atual (R$)": valor_atual,
                "Dividendos a Receber (R$)": valor_total_qualificado_e_provisionado
            })
    
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
        nome_ficheiro_historico = 'data/historico_portfolio.csv'
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
        total_dividendos = df_filtrado["Dividendos a Receber (R$)"].sum()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Valor Total Investido", f"R$ {total_investido:,.2f}")
        col2.metric("Valor Atual da Carteira", f"R$ {total_atual_filtrado:,.2f}", f"{lucro_prejuizo_total:,.2f} R$")
        col3.metric("Rentabilidade Total", f"{rentabilidade_total:.2f}%", f"{rentabilidade_total:.2f}%")
        col4.metric("Dividendos a Receber", f"R$ {total_dividendos:,.2f}")

        st.subheader("Detalhes dos Ativos")
        df_para_exibir = df_filtrado[[ "Ativo", "Tipo", "Quantidade", "Preço Médio (R$)", "Custo Total (R$)", "Preço Atual (R$)", "Valor Atual (R$)", "Dividendos a Receber (R$)", "Lucro/Prejuízo (R$)", "Rentabilidade (%)" ]]
        formatador = { "Quantidade": "{:,.8f}", "Preço Médio (R$)": "R$ {:,.2f}", "Custo Total (R$)": "R$ {:,.2f}", "Preço Atual (R$)": "R$ {:,.2f}", "Valor Atual (R$)": "R$ {:,.2f}", "Dividendos a Receber (R$)": "R$ {:,.2f}", "Lucro/Prejuízo (R$)": "R$ {:+,.2f}", "Rentabilidade (%)": "{:+.2f}%" }
        st.dataframe(df_para_exibir.style.apply(lambda col: col.map(colorir_rentabilidade), subset=['Lucro/Prejuízo (R$)', 'Rentabilidade (%)']).format(formatador, decimal=",", thousands="."), use_container_width=True)
        
        st.subheader("Detalhes dos Proventos")
        if proventos_detalhados:
            df_proventos = pd.DataFrame(proventos_detalhados)
            df_proventos.sort_values(by="Data Ex", ascending=False, inplace=True)
            df_proventos['Data Ex'] = pd.to_datetime(df_proventos['Data Ex']).dt.strftime('%d/%m/%Y')
            df_proventos['Data Pagamento'] = df_proventos['Data Pagamento'].apply(lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else 'A confirmar')
            
            st.dataframe(df_proventos.style.apply(lambda col: col.map(colorir_status), subset=['Status']).format({ "Valor por Ação (R$)": "R$ {:,.4f}", "Total a Receber (R$)": "R$ {:,.2f}"}), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum provento (qualificado ou provisionado) encontrado para as ações na sua carteira.")

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