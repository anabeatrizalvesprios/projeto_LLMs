# Análise de Representantes com LLM

Mini-projeto desenvolvido para experiência com LLMs.

## Objetivo

Transformar dados tabulares (planilhas de representantes comerciais e de clientes) em **resumos executivos em linguagem natural**, usando um LLM para gerar insights de negócio a partir de métricas agregadas — algo que uma query SQL sozinha não entrega.

## Dados utilizados

Duas planilhas com dados fictícios de uma empresa (projeto CRM) — nomes de representantes, gerentes e supervisores fictícios (ex: "Representante A") antes de qualquer chamada à API externa.

- **Base de representantes**: Região, Código, Nome, Gerente, Supervisora Interna
- **Base de clientes**: Código do representante, CNPJ, Razão Social, Situação Cadastral (ATIVA/SUSPENSA/BAIXADA), Cidade, Estado, CNAE Principal, entre outros

## Arquitetura

O projeto foi dividido em duas etapas independentes, por design:

### Etapa 1 — Preparação dos dados (`etapa1_metricas.py`)
Sem uso de LLM. Faz o merge das duas planilhas (por código do representante) e calcula métricas agregadas:
- Total de clientes por representante
- Distribuição por estado
- Distribuição por situação cadastral
- Top CNAEs atendidos
- Ranking de gerentes por número de representantes e de clientes

Saída: `metricas_etapa1.json`, um formato estruturado e independente de qual LLM será usado depois.

### Etapa 3 — Geração de resumos com LLM (`etapa3_llm.py`)
Lê o JSON da Etapa 1 e, para cada representante, envia um prompt estruturado ao modelo pedindo um resumo executivo (3-5 frases) sobre cobertura geográfica e saúde da carteira, destacando pontos de atenção.

Saída: `resumos_etapa3.json`, com as métricas originais + o resumo gerado.

## Por que separar preparação de dados e geração de texto?

Essa separação é uma decisão deliberada de design: cálculos determinísticos (somas, contagens, agrupamentos) devem ser feitos em código tradicional, não pelo LLM — é mais rápido, mais barato e 100% confiável. O LLM entra só na parte em que ele agrega valor de verdade: transformar dados estruturados em texto natural com interpretação e recomendação.

## Stack utilizada

- **Python** + **pandas** (leitura e agregação de dados)
- **Google Gemini API** (`google-genai`, modelo `gemini-3.8-flash`) — escolhida por ter tier gratuito sem necessidade de cartão de crédito
- Chave de API gerenciada via variável de ambiente (`GEMINI_API_KEY`), nunca hardcoded no código

## Como rodar

```bash
pip install -U google-genai pandas openpyxl

# Windows (cmd)
set GEMINI_API_KEY=sua_chave_aqui

# Windows (PowerShell)
$env:GEMINI_API_KEY="sua_chave_aqui"

python etapa1_metricas.py
python etapa3_llm.py
```

## Robustez frente a limites da camada gratuita

A camada gratuita da API impõe limites de requisições por minuto e por dia, que variam por modelo. Para lidar com isso, o `etapa3_llm.py` foi construído com:

- **Retry automático com backoff**: ao receber um erro de limite de requisições, o script aguarda o tempo sugerido pela própria API e tenta novamente (até 5 tentativas)
- **Salvamento incremental**: o resultado é salvo a cada representante processado, não só ao final
- **Retomada de execução**: ao rodar novamente, o script identifica quais representantes já têm resumo gerado e processa apenas os pendentes, evitando refazer trabalho e economizando cota da API

Essas escolhas refletem uma preocupação de engenharia real ao trabalhar com APIs de LLM em produção: elas têm limites de uso, e um pipeline robusto precisa lidar com isso de forma automática, não manual.

## Exemplo de saída

> "O Representante A apresenta uma carteira com excessiva dispersão geográfica, pulverizada em 14 estados, com apenas 35% dos clientes concentrados em sua região de atuação designada (Sudeste). A saúde da base cadastral requer atenção crítica, uma vez que 40% dos clientes estão inoperantes (...) Recomenda-se realizar o saneamento imediato da base inativa e reorientar os esforços de prospecção para consolidar a presença regional no Sudeste."

## Possíveis extensões futuras

- Interface simples (Streamlit) para visualizar os resumos
- Comparação de diferentes prompts para avaliar qual gera o melhor insight
- Extensão para responder perguntas ad-hoc sobre a base (ex: "quais representantes têm mais clientes baixados?")
