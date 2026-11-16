"""
Etapa 1 — Preparação dos dados (sem LLM)

Lê as planilhas de representantes e clientes, faz o merge e calcula
métricas agregadas por representante e por gerente.
"""

import pandas as pd
import json

CAMINHO_REPRESENTANTES = "base_representante.xlsx"
CAMINHO_CLIENTES = "base_clientes.xlsx"


def carregar_dados():
    reps = pd.read_excel(CAMINHO_REPRESENTANTES)
    clientes = pd.read_excel(CAMINHO_CLIENTES)
    return reps, clientes


def calcular_metricas_por_representante(reps: pd.DataFrame, clientes: pd.DataFrame) -> list[dict]:
    """Gera um bloco de métricas por representante, pronto para virar prompt na Etapa 3."""
    resultado = []

    for _, rep in reps.iterrows():
        codigo = rep["Codigo Representante"]
        clientes_rep = clientes[clientes["CÓDIGO"] == codigo]

        total_clientes = len(clientes_rep)
        por_estado = clientes_rep["ESTADO"].value_counts().to_dict()
        por_situacao = clientes_rep["SITUACAO_CNPJ"].value_counts().to_dict()
        top_cnaes = clientes_rep["CNAE_PRINCIPAL"].value_counts().head(3).to_dict()

        resultado.append({
            "codigo": int(codigo),
            "nome": rep["Representante"],
            "regiao": rep["Região"],
            "gerente": rep["GERENTE"],
            "supervisora": rep["SUPERVISORA INTERNA"],
            "total_clientes": total_clientes,
            "clientes_por_estado": por_estado,
            "clientes_por_situacao": por_situacao,
            "top_cnaes": top_cnaes,
        })

    return resultado


def calcular_metricas_por_gerente(reps: pd.DataFrame, clientes: pd.DataFrame) -> list[dict]:
    """Agrega quantidade de representantes e de clientes por gerente."""
    clientes_por_codigo = clientes["CÓDIGO"].value_counts()

    reps_com_contagem = reps.copy()
    reps_com_contagem["total_clientes"] = reps_com_contagem["Codigo Representante"].map(
        clientes_por_codigo
    ).fillna(0).astype(int)

    agrupado = (
        reps_com_contagem.groupby("GERENTE")
        .agg(
            total_representantes=("Codigo Representante", "count"),
            total_clientes=("total_clientes", "sum"),
        )
        .reset_index()
        .sort_values(["total_representantes", "total_clientes"], ascending=False)
    )

    return agrupado.to_dict(orient="records")


def main():
    reps, clientes = carregar_dados()

    metricas_representantes = calcular_metricas_por_representante(reps, clientes)
    metricas_gerentes = calcular_metricas_por_gerente(reps, clientes)

    saida = {
        "representantes": metricas_representantes,
        "gerentes": metricas_gerentes,
    }

    with open("metricas.json", "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2)

    print("=== Métricas por representante ===")
    for r in metricas_representantes:
        print(f"\n{r['nome']} ({r['regiao']}) — gerente: {r['gerente']}")
        print(f"  Total de clientes: {r['total_clientes']}")
        print(f"  Por estado: {r['clientes_por_estado']}")
        print(f"  Por situação: {r['clientes_por_situacao']}")
        print(f"  Top CNAEs: {r['top_cnaes']}")

    print("\n=== Gerentes com mais representantes / mais clientes ===")
    for g in metricas_gerentes:
        print(f"  {g['GERENTE']}: {g['total_representantes']} representante(s), {g['total_clientes']} cliente(s)")


if __name__ == "__main__":
    main()
