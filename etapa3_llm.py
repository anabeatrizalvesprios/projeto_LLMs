"""
Etapa 3 — Geração de resumos executivos com LLM (Google Gemini API)

Lê as métricas calculadas na Etapa 1 (metricas_etapa1.json) e, para cada
representante, pede ao modelo um resumo executivo em texto sobre a
cobertura e a saúde da carteira.

Requer a variável de ambiente GEMINI_API_KEY configurada.
"""

from google import genai
import json
import re
import time

ARQUIVO_METRICAS = "metricas.json"
ARQUIVO_SAIDA = "resumos.json"
MODELO = "gemini-3.6-flash"

# Pausa entre cada chamada, para não estourar o limite de requisições/minuto
# da camada gratuita. Se continuar dando erro 429, aumente esse valor.
PAUSA_ENTRE_CHAMADAS_SEGUNDOS = 12
MAX_TENTATIVAS = 5


def extrair_tempo_espera(mensagem_erro: str) -> float:
    """Extrai o tempo de espera sugerido pela API na mensagem de erro 429."""
    match = re.search(r"retry in ([\d.]+)s", mensagem_erro)
    if match:
        return float(match.group(1)) + 2  # margem de segurança
    return 30.0  # valor padrão se não conseguir extrair


def montar_prompt(rep: dict) -> str:
    return f"""Você é um analista de vendas. Com base nos dados abaixo sobre um
representante comercial, escreva um resumo executivo curto (3 a 5 frases,
em português) sobre a cobertura geográfica e a saúde da carteira de
clientes desse representante. Destaque pontos de atenção, se houver
(ex: concentração excessiva em poucos estados, alta proporção de clientes
suspensos ou baixados). Responda apenas com o resumo, sem título nem
introdução.

Representante: {rep['nome']}
Região: {rep['regiao']}
Gerente: {rep['gerente']}
Total de clientes: {rep['total_clientes']}
Clientes por estado: {json.dumps(rep['clientes_por_estado'], ensure_ascii=False)}
Clientes por situação cadastral: {json.dumps(rep['clientes_por_situacao'], ensure_ascii=False)}
Principais CNAEs atendidos: {json.dumps(rep['top_cnaes'], ensure_ascii=False)}
"""


def gerar_resumo(client: genai.Client, rep: dict) -> str:
    prompt = montar_prompt(rep)

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            interaction = client.interactions.create(
                model=MODELO,
                input=prompt,
            )
            return interaction.output_text.strip()
        except Exception as e:
            mensagem = str(e)
            if "429" in mensagem or "quota" in mensagem.lower() or "rate" in mensagem.lower():
                espera = extrair_tempo_espera(mensagem)
                print(f"  Limite de requisições atingido. Aguardando {espera:.0f}s "
                      f"(tentativa {tentativa}/{MAX_TENTATIVAS})...")
                time.sleep(espera)
            else:
                raise  # erro diferente de rate limit, não faz sentido tentar de novo

    raise RuntimeError(f"Falhou após {MAX_TENTATIVAS} tentativas para {rep['nome']}")


def carregar_resultado_existente() -> dict:
    """Se o script já rodou parcialmente antes, carrega o que já foi feito."""
    try:
        with open(ARQUIVO_SAIDA, "r", encoding="utf-8") as f:
            dados_existentes = json.load(f)
        ja_processados = {r["nome"]: r for r in dados_existentes["representantes"]}
        return ja_processados
    except FileNotFoundError:
        return {}


def main():
    with open(ARQUIVO_METRICAS, "r", encoding="utf-8") as f:
        dados = json.load(f)

    client = genai.Client()  # lê a chave de GEMINI_API_KEY automaticamente

    ja_processados = carregar_resultado_existente()
    if ja_processados:
        print(f"Retomando execução: {len(ja_processados)} representante(s) já processado(s) anteriormente.\n")

    resultado = list(ja_processados.values())
    pendentes = [r for r in dados["representantes"] if r["nome"] not in ja_processados]

    for i, rep in enumerate(pendentes):
        print(f"Gerando resumo para {rep['nome']}...")
        resumo = gerar_resumo(client, rep)
        rep_com_resumo = {**rep, "resumo_executivo": resumo}
        resultado.append(rep_com_resumo)
        print(f"  -> {resumo}\n")

        # Salva o progresso a cada representante, para não perder nada
        # se o script for interrompido no meio do caminho
        with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
            json.dump({"representantes": resultado, "gerentes": dados["gerentes"]}, f, ensure_ascii=False, indent=2)

        if i < len(pendentes) - 1:
            time.sleep(PAUSA_ENTRE_CHAMADAS_SEGUNDOS)

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump({"representantes": resultado, "gerentes": dados["gerentes"]}, f, ensure_ascii=False, indent=2)

    print(f"\nConcluído. Resultado salvo em {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()
