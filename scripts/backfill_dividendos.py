# scripts/backfill_dividendos.py
import pandas as pd
import requests
from io import StringIO
import json
import os

# --- Lógica de Caminhos Robusta ---
script_dir = os.path.dirname(os.path.realpath(__file__))
project_root = os.path.dirname(script_dir)
data_folder_path = os.path.join(project_root, 'data')

def carregar_carteira():
    caminho_carteira = os.path.join(data_folder_path, 'carteira.json')
    try:
        with open(caminho_carteira, 'r', encoding='utf-8') as arquivo:
            return json.load(arquivo)
    except Exception as e:
        print(f"Erro ao ler '{caminho_carteira}': {e}")
        return None

def fetch_from_fundamentus(ticker_symbol):
    ticker_sem_sa = ticker_symbol.replace(".SA", "")
    url = f"https://www.fundamentus.com.br/proventos.php?papel={ticker_sem_sa}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tabelas = pd.read_html(StringIO(response.text), decimal=',', thousands='.')
        if not tabelas: return pd.DataFrame()
        
        df = tabelas[0].rename(columns={"Data": "Data Ex", "Valor": "Valor", "Data de Pagamento": "Data Pagamento"})
        df['Ativo'] = ticker_symbol
        return df[['Ativo', 'Data Ex', 'Valor', 'Data Pagamento']]
    except Exception:
        return pd.DataFrame()

def recriar_historico_dividendos():
    print("Iniciando a criação do histórico de dividendos retroativo...")
    carteira = carregar_carteira()
    if not carteira: return

    todos_proventos = []
    tickers_acoes = [ticker for ticker in carteira.keys() if ticker.endswith('.SA')]
    
    for ticker in tickers_acoes:
        print(f"Buscando histórico completo para {ticker}...")
        df_proventos = fetch_from_fundamentus(ticker)
        if not df_proventos.empty:
            todos_proventos.append(df_proventos)

    if not todos_proventos:
        print("Nenhum provento encontrado para os ativos na carteira.")
        return

    df_completo = pd.concat(todos_proventos, ignore_index=True)
    df_completo.sort_values(by="Data Ex", ascending=False, inplace=True)
    
    caminho_historico = os.path.join(data_folder_path, 'historico_dividendos.csv')
    df_completo.to_csv(caminho_historico, index=False)
    print(f"\nSucesso! Histórico de dividendos criado com {len(df_completo)} registos.")
    print(f"Ficheiro guardado em: {caminho_historico}")

if __name__ == "__main__":
    recriar_historico_dividendos()