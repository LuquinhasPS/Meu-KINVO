import pandas as pd
from datetime import date, datetime
import requests
from io import StringIO

def buscar_e_classificar_proventos(ticker_symbol):
    """
    Busca proventos da fonte Fundamentus e aplica a lógica de classificação.
    Esta é a nossa abordagem final e mais robusta.
    """
    print(f"\n--- INICIANDO DIAGNÓSTICO DEFINITIVO PARA: {ticker_symbol} ---")
    
    proventos_finais = []
    hoje = date.today()
    
    try:
        # --- FONTE ÚNICA E PRIMÁRIA: FUNDAMENTUS ---
        ticker_sem_sa = ticker_symbol.replace(".SA", "")
        url = f"https://www.fundamentus.com.br/proventos.php?papel={ticker_sem_sa}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        tabelas = pd.read_html(StringIO(response.text), decimal=',', thousands='.')
        
        if not tabelas:
            print("DIAGNÓSTICO: Nenhuma tabela encontrada no Fundamentus.")
            return

        df = tabelas[0].rename(columns={"Data": "data_ex", "Valor": "valor", "Data de Pagamento": "data_pag"})
        df['data_ex'] = pd.to_datetime(df['data_ex'], format='%d/%m/%Y').dt.date
        df['data_pag'] = pd.to_datetime(df['data_pag'], format='%d/%m/%Y', errors='coerce').dt.date

        # --- LÓGICA DE CLASSIFICAÇÃO APLICADA DIRETAMENTE ---
        for _, provento in df.iterrows():
            status = None
            data_ex = provento['data_ex']
            data_pag = provento['data_pag']

            if pd.notna(data_pag) and data_pag < hoje:
                status = "Recebido"
            elif data_ex < hoje and (pd.isna(data_pag) or data_pag >= hoje):
                status = "Qualificado"
            elif data_ex > hoje:
                status = "Provisionado"
            
            if status:
                proventos_finais.append({
                    "Ativo": ticker_symbol, "Status": status,
                    "Valor/Ação": provento['valor'], "Data Ex": data_ex,
                    "Data Pagamento": data_pag
                })

        # --- RELATÓRIO FINAL ---
        if proventos_finais:
            df_final = pd.DataFrame(proventos_finais).sort_values(by="Data Ex", ascending=False)
            print("\n--- RELATÓRIO FINAL: PROVENTOS ENCONTRADOS E CLASSIFICADOS ---")
            print(df_final.to_string(index=False))
        else:
            print("\nRELATÓRIO FINAL: Nenhum provento se encaixa nos critérios.")

    except Exception as e:
        print(f"\nERRO CRÍTICO: {e}")

# --- Executa o diagnóstico ---
if __name__ == "__main__":
    buscar_e_classificar_proventos("BBDC4.SA")
    print("\n" + "="*50 + "\n")
    buscar_e_classificar_proventos("WEGE3.SA")
    print("\n" + "="*50 + "\n")
    buscar_e_classificar_proventos("PETR4.SA")