import yfinance as yf
from bcb import sgs
from datetime import date, datetime
import json
import pytz

def buscar_taxa_dolar():
    """Busca a cotação atual do Dólar (USD para BRL)."""
    try:
        dolar = yf.Ticker("BRL=X")
        taxa = dolar.history(period="1d")['Close'].iloc[-1]
        return taxa
    except Exception as e:
        print(f"Erro ao buscar taxa do Dólar: {e}")
        return None

def buscar_preco_ativo(ticker_symbol, taxa_dolar):
    """Busca o preço de um ativo, fazendo a conversão para BRL se for cripto em USD."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # Se for cripto (ex: BTC-USD), pega o preço em dólar e converte
        if "-USD" in ticker_symbol:
            info = ticker.info
            preco_usd = info.get('regularMarketPrice')
            if preco_usd and taxa_dolar:
                return preco_usd * taxa_dolar
            return None # Retorna None se não conseguir o preço em USD ou a taxa do dólar
        
        # Para ações e ETFs da B3
        dados_hoje = ticker.history(period="1d")
        if dados_hoje.empty: return None
        return dados_hoje['Close'].iloc[-1]
    except Exception:
        return None

# ... (as outras funções buscar_rentabilidade_cdi_anual, carregar_carteira, buscar_info_dividendos continuam as mesmas) ...
def buscar_rentabilidade_cdi_anual():
    try:
        ano_atual = date.today().year
        cdi_diario = sgs.get({'cdi': 12}, start=f'{ano_atual}-01-01')
        rentabilidade_acumulada = (1 + cdi_diario['cdi'] / 100).prod() - 1
        return rentabilidade_acumulada * 100
    except Exception: return None

def carregar_carteira():
    try:
        with open('carteira.json', 'r', encoding='utf-8') as arquivo:
            return json.load(arquivo)
    except FileNotFoundError:
        print("Erro: Arquivo 'carteira.json' não encontrado!")
        return None
    except json.JSONDecodeError:
        print("Erro: O arquivo 'carteira.json' tem um formato inválido.")
        return None

def buscar_info_dividendos(ticker_symbol):
    if not ticker_symbol.endswith('.SA'):
        return None, None
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        if 'exDividendDate' in info and info['exDividendDate'] is not None and \
           'lastDividendValue' in info and info['lastDividendValue'] is not None:
            timestamp_ex_date = info['exDividendDate']
            data_ex = datetime.fromtimestamp(timestamp_ex_date).date()
            if data_ex > date.today():
                valor_dividendo = info['lastDividendValue']
                return valor_dividendo, data_ex
        return None, None
    except Exception:
        return None, None

# --- PARTE PRINCIPAL (COM PEQUENOS AJUSTES) ---
minha_carteira = carregar_carteira()
if minha_carteira:
    # Busca a taxa do dólar UMA VEZ no início para ser mais eficiente
    print("Buscando a cotação do Dólar para conversão...")
    taxa_dolar_atual = buscar_taxa_dolar()
    if not taxa_dolar_atual:
        print("Não foi possível obter a taxa do dólar. Os valores de cripto não serão calculados.")

    valor_total_investido_carteira = 0.0
    valor_total_atual_carteira = 0.0
    total_dividendos_provisionados = 0.0
    
    print("\n--- Análise da Carteira, incluindo Provisão de Dividendos ---")
    
    for ticker, transacoes in minha_carteira.items():
        # ... (cálculo de posição continua igual) ...
        quantidade_total = 0
        custo_total = 0.0
        for transacao in transacoes:
            if transacao["tipo"] == "compra":
                quantidade_total += transacao["quantidade"]
                custo_total += transacao["quantidade"] * transacao["preco_unitario"]
        if quantidade_total == 0: continue
        preco_medio = custo_total / quantidade_total
        print(f"\n----- {ticker} -----")
        print(f"Posição: {quantidade_total} cotas/unidades a um preço médio de R$ {preco_medio:.2f}")
        
        # Agora passamos a taxa do dólar para a função que busca o preço
        preco_atual = buscar_preco_ativo(ticker, taxa_dolar_atual)
        
        if preco_atual is not None:
            valor_atual_da_posicao = quantidade_total * preco_atual
            lucro_prejuizo = valor_atual_da_posicao - custo_total
            print(f"-> Rentabilidade: R$ {lucro_prejuizo:+.2f} ({(lucro_prejuizo/custo_total)*100:+.2f}%)")
            valor_total_investido_carteira += custo_total
            valor_total_atual_carteira += valor_atual_da_posicao
        else:
            print(f"-> Não foi possível buscar o preço atual para {ticker}.")
            valor_total_investido_carteira += custo_total
            valor_total_atual_carteira += custo_total # Adiciona o custo para não distorcer o total

        # ... (lógica de dividendos continua igual) ...
        valor_div, data_ex = buscar_info_dividendos(ticker)
        if valor_div is not None:
            quantidade_habilitada = 0
            for transacao in transacoes:
                data_compra = datetime.strptime(transacao["data"], "%Y-%m-%d").date()
                if transacao["tipo"] == "compra" and data_compra < data_ex:
                    quantidade_habilitada += transacao["quantidade"]
            if quantidade_habilitada > 0:
                valor_provisionado = quantidade_habilitada * valor_div
                total_dividendos_provisionados += valor_provisionado
                print(f"-> Dividendo Anunciado: R$ {valor_div:.4f} por cota.")
                print(f"   - Data-Ex: {data_ex.strftime('%d/%m/%Y')} (Você precisa ter as cotas antes desta data)")
                print(f"   - Posição Habilitada: {quantidade_habilitada} cotas")
                print(f"   - VALOR A RECEBER: R$ {valor_provisionado:.2f}")

    # ... (relatório final continua igual) ...
    cdi_anual = buscar_rentabilidade_cdi_anual()
    lucro_total_carteira = valor_total_atual_carteira - valor_total_investido_carteira
    rentabilidade_total = (lucro_total_carteira / valor_total_investido_carteira) * 100 if valor_total_investido_carteira > 0 else 0
    print("\n----------------------------------------------------")
    print("               RESULTADO CONSOLIDADO                ")
    print("----------------------------------------------------")
    print(f"Total Investido: R$ {valor_total_investido_carteira:.2f}")
    print(f"Valor Atual:     R$ {valor_total_atual_carteira:.2f}")
    print(f"Rentabilidade:   {rentabilidade_total:+.2f}%")
    if cdi_anual: print(f"CDI (no ano):    {cdi_anual:+.2f}%")
    print("----------------------------------------------------")
    print(f"TOTAL DE DIVIDENDOS PROVISIONADOS: R$ {total_dividendos_provisionados:.2f}")
    print("----------------------------------------------------")