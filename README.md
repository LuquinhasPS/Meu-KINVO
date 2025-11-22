# Painel de Acompanhamento de Carteira de Investimentos

Este projeto é uma aplicação web, construída com Python e Streamlit, para acompanhamento de uma carteira de investimentos diversificada, incluindo ações, ETFs e criptomoedas. A aplicação foi desenvolvida para ser uma ferramenta similar ao Kinvo, focada em dar visibilidade sobre a evolução do património, a performance dos ativos e o recebimento de proventos.

## Funcionalidades Principais

- **Dashboard Interativo:** Interface web limpa e moderna para visualização dos dados.
- **Múltiplos Tipos de Ativos:** Suporte para Ações e ETFs da B3, além de Criptomoedas.
- **Análise de Performance Completa:**
  - Cálculo em tempo real de preço médio, custo total e valor atual.
  - **Rentabilidade Total:** Visualização do ganho de capital puro.
  - **Rentabilidade com Dividendos:** Métrica ajustada que inclui o retorno gerado por proventos.
  - **Lucro/Prejuízo Real:** Valores monetários de ganho/perda considerando dividendos recebidos.
- **Gestão de Dividendos e Proventos:**
  - **Histórico Detalhado:** Tabela com todos os proventos (dividendos, JCP) anunciados, provisionados e pagos.
  - **Gráfico de Proventos:** Visualização mensal dos dividendos recebidos nos últimos 12 meses e previsões futuras.
  - **Integração Automática:** Busca dados de proventos diretamente do site Fundamentus.
- **Gráficos Dinâmicos:**
  - **Evolução do Património:** Gráfico de linha que mostra o valor total da carteira ao longo do tempo.
  - **Alocação de Ativos:** Gráficos de pizza interativos para visualizar a distribuição da carteira por ativo e por tipo de ativo.
  - **Histórico de Aportes:** Gráfico de barras com o total investido a cada mês.
- **Entrada de Dados Facilitada:** Formulário na barra lateral para adicionar novas transações de compra sem precisar de editar ficheiros manualmente.
- **Atualização Automática de Ativos:** Inclui scripts auxiliares que buscam e atualizam automaticamente a lista de todas as ações da B3 e as principais criptomoedas do mercado.

## Estrutura do Projeto

- `app.py`: A aplicação web principal construída com Streamlit. Contém toda a lógica de visualização, cálculo de métricas e integração com APIs.
- `data/`: Diretório contendo os dados da aplicação.
  - `carteira.json`: Armazena todas as transações de compra do utilizador.
  - `all_tickers.json`: Lista completa de ativos disponíveis (gerada automaticamente).
  - `historico_portfolio.csv`: Histórico do valor total da carteira para o gráfico de evolução.
- `scripts/`: Diretório com scripts utilitários (opcionais) para manutenção.
  - `update_tickers.py`: Atualiza a lista de ativos disponíveis.
  - `backfill_historico.py`: Popula o histórico de valor da carteira retroativamente.
- `requirements.txt`: Lista de todas as bibliotecas Python necessárias.

## Configuração e Instalação

1.  **Clone o repositório** (ou descarregue os ficheiros para uma pasta).
2.  **(Opcional, mas recomendado)** Crie e ative um ambiente virtual:
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    ```
3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

## Como Usar a Aplicação

O uso da aplicação é simples e centrado no ficheiro `app.py`.

1.  **Executar o Painel Principal:**
    Para iniciar e visualizar a sua aplicação, execute:
    ```bash
    streamlit run app.py
    ```
    A aplicação abrirá automaticamente no seu navegador.

2.  **Adicionar Compras:**
    Use o formulário na barra lateral esquerda para registrar novas compras. Selecione o ativo, a data, a quantidade e o preço unitário.

3.  **(Manutenção) Atualizar Listas de Ativos:**
    Caso precise atualizar a lista de tickers disponíveis (novos IPOs, novas criptos), execute o script auxiliar:
    ```bash
    python scripts/update_tickers.py
    ```

## Demonstração Visual

A aplicação oferece uma visão completa e detalhada da carteira de investimentos.

### Painel Principal
O dashboard principal apresenta um resumo consolidado da carteira, incluindo valor investido, valor atual, rentabilidade total (com e sem dividendos) e o total de proventos recebidos.

### Detalhes dos Ativos
Uma tabela detalhada mostra a performance de cada ativo individualmente. As colunas foram otimizadas com abreviações (ex: "PM" para Preço Médio, "L/P" para Lucro/Prejuízo) para melhor visualização em telas padrão.

### Gestão de Proventos
Uma seção dedicada exibe:
- Tabela com o status de cada provento (Pago, Provisionado, Anunciado).
- Gráfico de barras comparando dividendos recebidos vs. previstos mês a mês.

### Análise Gráfica e de Aportes
Gráficos interativos permitem visualizar a alocação da carteira (por ativo e tipo) e a evolução dos aportes realizados ao longo do tempo.