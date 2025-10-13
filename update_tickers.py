import pandas as pd
import requests
import json

def fetch_b3_tickers():
    """Busca tickers da B3 via scraping do Fundamentus."""
    print("Buscando tickers de ações da B3...")
    try:
        url = "https://www.fundamentus.com.br/resultado.php"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tabelas = pd.read_html(response.text, decimal=',', thousands='.')
        if not tabelas:
            return []
        df = tabelas[0]
        tickers_sa = [ticker + ".SA" for ticker in df['Papel'].tolist()]
        print(f"-> {len(tickers_sa)} tickers de ações encontrados.")
        return tickers_sa
    except Exception as e:
        print(f"Erro ao buscar tickers da B3: {e}")
        return []

def fetch_crypto_tickers():
    """Busca os 250 tickers de criptomoedas mais populares da API do CoinGecko."""
    print("Buscando tickers de criptomoedas via API do CoinGecko...")
    try:
        # URL da API do CoinGecko para buscar o ranking de moedas por mercado
        url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1"
        response = requests.get(url)
        response.raise_for_status()
        dados = response.json()
        
        # Extrai o símbolo de cada cripto (ex: 'btc') e formata para o padrão do yfinance (ex: 'BTC-USD')
        crypto_tickers = [f"{item['symbol'].upper()}-USD" for item in dados]
        print(f"-> {len(crypto_tickers)} tickers de criptomoedas encontrados.")
        return crypto_tickers
    except Exception as e:
        print(f"Erro ao buscar tickers de cripto: {e}")
        return []

def atualizar_lista_completa():
    """Executa todas as buscas e guarda o resultado num ficheiro JSON estruturado."""
    print("Iniciando a atualização da lista completa de ativos...")
    
    b3_tickers = fetch_b3_tickers()
    crypto_tickers = fetch_crypto_tickers()
    
    # Adiciona alguns ETFs manualmente, pois não estão nas listas automáticas
    etfs = ["GOLD11.SA", "BOVA11.SA", "SMAL11.SA", "IVVB11.SA"]

    dados_finais = {
        "acoes_b3": sorted(b3_tickers),
        "criptomoedas": sorted(crypto_tickers),
        "etfs": sorted(etfs)
    }

    with open('all_tickers.json', 'w', encoding='utf-8') as f:
        json.dump(dados_finais, f, indent=4)
        
    total = len(b3_tickers) + len(crypto_tickers) + len(etfs)
    print(f"\nSucesso! {total} tickers foram guardados em 'all_tickers.json'.")

if __name__ == "__main__":
    atualizar_lista_completa()