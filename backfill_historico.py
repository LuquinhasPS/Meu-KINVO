import pandas as pd
import yfinance as yf
from datetime import date, timedelta
import json
import os

def carregar_carteira():
    if not os.path.exists('carteira.json'):
        print("Erro: Ficheiro 'carteira.json' não encontrado!")
        return None
    try:
        with open('carteira.json', 'r', encoding='utf-8') as arquivo:
            return json.load(arquivo)
    except Exception as e:
        print(f"Erro ao ler o ficheiro JSON: {e}")
        return None

def backfill_historico():
    print("Iniciando o preenchimento do histórico da carteira...")
    
    carteira = carregar_carteira()
    if not carteira: return

    data_final = date.today()
    data_inicial = data_final - timedelta(days=90)
    
    print(f"Buscando dados históricos de {data_inicial} a {data_final}...")

    tickers_brl = [t for t in carteira.keys() if t.endswith('.SA')]
    tickers_usd = [t for t in carteira.keys() if t.endswith('-USD')]
    
    historico_precos_brl = yf.download(tickers_brl, start=data_inicial, end=data_final, auto_adjust=False)['Close'] if tickers_brl else pd.DataFrame()
    historico_precos_usd = yf.download(tickers_usd, start=data_inicial, end=data_final, auto_adjust=False)['Close'] if tickers_usd else pd.DataFrame()
    taxa_dolar_historico = yf.download("BRL=X", start=data_inicial, end=data_final, auto_adjust=False)['Close']

    dados_historicos_gerados = []
    
    print("\nProcessando histórico dia a dia...")
    for dia in pd.date_range(start=data_inicial, end=data_final):
        valor_total_no_dia = 0.0
        taxa_dolar_no_dia = taxa_dolar_historico.asof(dia)
        
        for ticker, transacoes in carteira.items():
            quantidade_no_dia = sum(t['quantidade'] for t in transacoes if t['tipo'] == 'compra' and pd.to_datetime(t['data']).date() <= dia.date())
            
            if quantidade_no_dia > 0:
                valor_do_ativo = 0
                try:
                    if ticker in tickers_brl and not historico_precos_brl.empty:
                        preco_no_dia = historico_precos_brl[ticker].asof(dia)
                        valor_do_ativo = quantidade_no_dia * preco_no_dia
                    
                    elif ticker in tickers_usd and not historico_precos_usd.empty:
                        preco_no_dia_usd = historico_precos_usd[ticker].asof(dia)
                        if isinstance(preco_no_dia_usd, pd.Series): preco_no_dia_usd = preco_no_dia_usd.iloc[0]
                        if isinstance(taxa_dolar_no_dia, pd.Series): taxa_dolar_no_dia = taxa_dolar_no_dia.iloc[0]
                        valor_do_ativo = quantidade_no_dia * preco_no_dia_usd * taxa_dolar_no_dia
                    
                    if pd.notna(valor_do_ativo):
                        valor_total_no_dia += valor_do_ativo
                except Exception:
                    pass
        
        if valor_total_no_dia > 0:
            dados_historicos_gerados.append({ 'Data': dia.strftime('%Y-%m-%d'), 'ValorTotal': valor_total_no_dia })

    if dados_historicos_gerados:
        df_gerado = pd.DataFrame(dados_historicos_gerados)
        
        # --- A CORREÇÃO ESTÁ AQUI ---
        # Agora verificamos se o ficheiro existe E se não está vazio
        if os.path.exists('historico_portfolio.csv') and os.path.getsize('historico_portfolio.csv') > 0:
            df_existente = pd.read_csv('historico_portfolio.csv')
            df_final = pd.concat([df_existente, df_gerado], ignore_index=True)
        else:
            df_final = df_gerado
        
        df_final.drop_duplicates(subset='Data', keep='last', inplace=True)
        df_final.sort_values(by='Data', inplace=True)
        
        df_final.to_csv('historico_portfolio.csv', index=False)
        print("\nFicheiro 'historico_portfolio.csv' criado/atualizado com sucesso!")
        print(f"{len(df_final)} registos de histórico foram guardados.")
    else:
        print("Nenhum dado de histórico foi gerado.")

if __name__ == "__main__":
    backfill_historico()