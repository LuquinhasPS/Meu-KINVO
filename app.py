import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date, datetime
import json
import pytz
import plotly.express as px
import os
import time

# --- Função para carregar a lista de tickers ---
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

# NOVIDADE: Função de dividendos agora busca também a data de pagamento
def buscar_info_dividendos(ticker_symbol):
    if not ticker_symbol.endswith('.SA'):
        return None, None, None # Retorna 3 valores
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        if 'exDividendDate' in info and info['exDividendDate'] is not None and \
           'lastDividendValue' in info and info['lastDividendValue'] is not None:
            
            timestamp_ex_date = info['exDividendDate']
            data_ex = datetime.fromtimestamp(timestamp_ex_date).date()

            if data_ex > date.today():
                valor_dividendo = info['lastDividendValue']
                data_pagamento = None
                
                # Tenta buscar a data de pagamento no calendário de eventos
                try:
                    calendar = ticker.calendar
                    if 'Dividend Date' in calendar and not calendar['Dividend Date'].empty:
                        pay_date_data = calendar['Dividend Date'].iloc[0]
                        # Converte para data, independentemente do formato (timestamp ou data)
                        if isinstance(pay_date_data, (int, float)):
                           data_pagamento = datetime.fromtimestamp(pay_date_data).date()
                        elif isinstance(pay_date_data, pd.Timestamp):
                           data_pagamento = pay_date_data.date()
                except Exception:
                    pass # Se não encontrar, data_pagamento continua None

                return valor_dividendo, data_ex, data_pagamento
                
        return None, None, None
    except Exception:
        return None, None, None

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
# ... (código do formulário continua o mesmo)
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
    dados_processados, lista_de_aportes, dividendos_detalhados = [], [], [] # Lista para os detalhes de dividendos

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
            
            valor_provisionado = 0
            # NOVIDADE: Agora capturamos os 3 valores da função
            valor_div, data_ex, data_pag = buscar_info_dividendos(ticker)
            if valor_div is not None:
                quantidade_habilitada = sum(t['quantidade'] for t in transacoes if t['tipo'] == 'compra' and datetime.strptime(t["data"], "%Y-%m-%d").date() < data_ex)
                if quantidade_habilitada > 0:
                    valor_provisionado = quantidade_habilitada * valor_div
                    # Adiciona os detalhes à nossa nova lista
                    dividendos_detalhados.append({
                        "Ativo": ticker,
                        "Valor por Ação (R$)": valor_div,
                        "Qtd. Habilitada": quantidade_habilitada,
                        "Data Ex": data_ex,
                        "Data Pagamento": data_pag,
                        "Total a Receber (R$)": valor_provisionado
                    })

            dados_processados.append({
                "Ativo": ticker, "Quantidade": quantidade_total, "Preço Médio (R$)": preco_medio,
                "Custo Total (R$)": custo_total, "Preço Atual (R$)": preco_atual, "Valor Atual (R$)": valor_atual,
                "Dividendos a Receber (R$)": valor_provisionado
            })
    
    df_carteira = pd.DataFrame(dados_processados)
    
    if not df_carteira.empty:
        # ... (código de cálculo, histórico e filtros continua igual) ...
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
        
        # NOVIDADE: Nova secção e tabela para os detalhes dos dividendos
        st.subheader("Detalhes dos Dividendos a Receber")
        if dividendos_detalhados:
            df_dividendos = pd.DataFrame(dividendos_detalhados)
            # Formata as colunas para melhor visualização
            df_dividendos['Data Ex'] = pd.to_datetime(df_dividendos['Data Ex']).dt.strftime('%d/%m/%Y')
            df_dividendos['Data Pagamento'] = pd.to_datetime(df_dividendos['Data Pagamento']).dt.strftime('%d/%m/%Y') if pd.notna(df_dividendos['Data Pagamento']).all() else 'A confirmar'
            df_dividendos['Valor por Ação (R$)'] = df_dividendos['Valor por Ação (R$)'].map('R$ {:,.4f}'.format)
            df_dividendos['Total a Receber (R$)'] = df_dividendos['Total a Receber (R$)'].map('R$ {:,.2f}'.format)
            st.dataframe(df_dividendos, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dividendo provisionado para as ações na sua carteira.")

        # ... (código dos gráficos de aportes e alocação continua igual)
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