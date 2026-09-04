"""
etl/consolidar.py
Junta as três fontes num único conjunto publicável e aplica os índices.

Uso:
    python etl/consolidar.py

Entrada:  data/bruto.json           (Censo, de ingestao.py)
          data/qualidade.json       (CPC, de extrair_cpc.py)
          data/cobertura_cnes.json  (CNES, de extrair_cnes.py)
Saída:    data/nacional.json
          data/municipios/<UF>.json
          data/_proveniencia.json

A ORDEM IMPORTA
---------------
`ingestao.py` produz `vagas_presencial` e `vagas_ead`; só depois disso faz
sentido calcular `pct_ead`, `HHI` sobre a capacidade total e o ICT. Rodar o
consolidador antes da ingestão grava `None` em cadeia sem reclamar de nada — o
arquivo fica com as chaves certas e os valores vazios, e nenhum teste de
integridade repara, porque as chaves existem.

FONTE AUSENTE NÃO VIRA ZERO
---------------------------
Se `cobertura_cnes.json` não existir, os campos de cobertura ficam `None` e o
conjunto sai marcado com a fonte faltando na proveniência. O que não acontece é
o ICAF virar 0,0 — isso afirmaria que nenhum município do país tem
fonoaudiólogo, uma afirmação forte sustentada por um arquivo que não foi lido.
"""
import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from indices import aplicar

REPO = Path(__file__).parent.parent
DATA = REPO / "data"


def _ler(caminho, obrigatorio=True):
    caminho = Path(caminho)
    if caminho.exists():
        return json.loads(caminho.read_text(encoding="utf-8"))
    if obrigatorio:
        raise SystemExit(f"[ERRO] {caminho} ausente — rode o passo anterior do pipeline.")
    print(f"[CONSOLIDAR] {caminho.name} ausente; os campos dessa fonte ficam nulos.")
    return None


def juntar_qualidade(ufs, qualidade):
    """Copia os indicadores de qualidade do CPC para cada UF."""
    campos = ("n_cursos_avaliados", "n_com_cpc", "n_com_idd",
              "concluintes_participantes", "CPC", "CPC_cont", "ENADE_cont",
              "IDD", "pct_doc_mestres", "pct_doc_doutores",
              "pct_doc_regime_integral", "dim_didatico_pedagogica",
              "dim_infraestrutura", "dim_oportunidade_formacao",
              "vagas_avaliadas")
    por_uf = (qualidade or {}).get("ufs", {})
    for sigla, d in ufs.items():
        q = por_uf.get(sigla, {})
        for campo in campos:
            d[campo] = q.get(campo)
        # UF com oferta mas sem nenhum curso avaliado é caso real, não erro:
        # TO tem curso presencial de Fonoaudiologia e nenhum curso no CPC 2023.
        d["tem_avaliacao"] = bool(q)
    return ufs


def juntar_cobertura(ufs, municipios_por_uf, cobertura):
    """
    Agrega a cobertura do CNES por UF e anexa aos municípios.

    O CNES identifica município por código IBGE de 6 dígitos (sem o dígito
    verificador); o Censo usa 7. A junção é pelos 6 primeiros — não por nome,
    que tem grafia divergente entre as bases e homônimos entre UFs.
    """
    # Os campos da fonte, nomeados uma vez só. Repetir a lista no ramo do
    # "sem fonte" foi o que fez `fonoaudiologos_por_100k` sumir do conjunto em
    # vez de sair nulo: o campo não existia, e um campo ausente não aparece
    # como "sem dados" — some da página inteira, sem alarme nenhum.
    CAMPOS = ("municipios_com_fonoaudiologo", "municipios_com_servico_fono",
              "fonoaudiologos_sus", "fonoaudiologos_por_100k")

    if not cobertura:
        for d in ufs.values():
            for campo in CAMPOS:
                d[campo] = None
        for lista in municipios_por_uf.values():
            for m in lista:
                m["fonoaudiologos_sus"] = None
                m["estabelecimentos_servico_fono"] = None
                m["servicos_fono"] = None
        return ufs, municipios_por_uf

    por_municipio = cobertura["municipios"]

    # Precisa saber a UF de cada município do CNES para agregar. O código IBGE
    # começa com o código da UF, então os dois primeiros dígitos bastam.
    codigo_uf = {
        "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
        "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
        "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
        "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
        "51": "MT", "52": "GO", "53": "DF",
    }

    com_fono = defaultdict(int)
    com_servico = defaultdict(int)
    profissionais = defaultdict(int)
    for codigo, m in por_municipio.items():
        uf = codigo_uf.get(str(codigo)[:2])
        if not uf:
            continue
        if m.get("fonoaudiologos_sus"):
            com_fono[uf] += 1
            profissionais[uf] += m["fonoaudiologos_sus"]
        if m.get("estabelecimentos_servico_fono"):
            com_servico[uf] += 1

    for sigla, d in ufs.items():
        d["municipios_com_fonoaudiologo"] = com_fono.get(sigla, 0)
        d["municipios_com_servico_fono"] = com_servico.get(sigla, 0)
        d["fonoaudiologos_sus"] = profissionais.get(sigla, 0) or None
        d["fonoaudiologos_por_100k"] = (
            round(100_000 * profissionais[sigla] / d["populacao"], 1)
            if profissionais.get(sigla) and d.get("populacao") else None)

    for uf, lista in municipios_por_uf.items():
        for m in lista:
            chave = str(m["codigo"])[:6]
            cnes = por_municipio.get(chave, {})
            m["fonoaudiologos_sus"] = cnes.get("fonoaudiologos_sus")
            m["estabelecimentos_servico_fono"] = cnes.get(
                "estabelecimentos_servico_fono")
            m["servicos_fono"] = cnes.get("servicos")

    return ufs, municipios_por_uf


def proveniencia(bruto, qualidade, cobertura):
    fontes = {
        "censo": {
            "presente": True,
            **(bruto["metadados"].get("proveniencia_censo") or {}),
        },
        "cpc": ({"presente": True, **qualidade["metadados"]} if qualidade
                else {"presente": False,
                      "motivo": "data/qualidade.json não gerado"}),
        "cnes": ({"presente": True, **cobertura["metadados"]} if cobertura
                 else {"presente": False,
                       "motivo": "data/cobertura_cnes.json não gerado"}),
        # As fontes do IBGE também declaram `presente`, como as demais. Sem o
        # campo, elas ficam de fora de qualquer varredura que pergunte "quais
        # fontes faltaram?" — e uma fonte que nunca aparece na resposta é uma
        # fonte que ninguém percebe ter sumido.
        "ibge_municipios": {"presente": True,
                            **(bruto["metadados"].get("municipios_ibge") or {})},
        "ibge_populacao": {"presente": True,
                           **(bruto["metadados"].get("populacao_ibge") or {})},
    }
    return {
        "gerado_em": date.today().isoformat(),
        "fontes": fontes,
        "limitacoes_conhecidas": [
            "A habilitação de Centro Especializado em Reabilitação (CER) não é "
            "publicada na base do CNES; o indicador não existe e não foi "
            "substituído por aproximação.",
            "Amapá, Mato Grosso do Sul e Roraima não têm curso presencial de "
            "Fonoaudiologia. Os indicadores que dependem de oferta presencial "
            "ficam nulos nessas UFs, não zerados.",
            "Tocantins tem oferta presencial e nenhum curso no ciclo do CPC "
            "2023; os indicadores de qualidade ficam nulos.",
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bruto", default=str(DATA / "bruto.json"))
    p.add_argument("--qualidade", default=str(DATA / "qualidade.json"))
    p.add_argument("--cobertura", default=str(DATA / "cobertura_cnes.json"))
    p.add_argument("--saida", default=str(DATA / "nacional.json"))
    args = p.parse_args()

    bruto = _ler(args.bruto)
    qualidade = _ler(args.qualidade, obrigatorio=False)
    cobertura = _ler(args.cobertura, obrigatorio=False)

    ufs = bruto["ufs"]
    municipios = bruto["municipios"]

    juntar_qualidade(ufs, qualidade)
    juntar_cobertura(ufs, municipios, cobertura)
    aplicar(ufs)

    metadados = dict(bruto["metadados"])
    metadados["proveniencia"] = proveniencia(bruto, qualidade, cobertura)
    nacional = {"metadados": metadados, "ufs": ufs}

    Path(args.saida).write_text(
        json.dumps(nacional, ensure_ascii=False, indent=1), encoding="utf-8")
    campos = len(next(iter(ufs.values())))
    print(f"[CONSOLIDAR] {len(ufs)} UFs, {campos} campos por UF -> {args.saida}")

    destino_mun = DATA / "municipios"
    destino_mun.mkdir(parents=True, exist_ok=True)
    total = 0
    for uf, lista in municipios.items():
        (destino_mun / f"{uf}.json").write_text(
            json.dumps({"uf": uf, "municipios": lista},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        total += len(lista)
    print(f"[CONSOLIDAR] {total} municípios em {len(municipios)} arquivos "
          f"-> {destino_mun}")

    (DATA / "_proveniencia.json").write_text(
        json.dumps(metadados["proveniencia"], ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"[CONSOLIDAR] proveniência -> data/_proveniencia.json")

    faltando = [n for n, f in metadados["proveniencia"]["fontes"].items()
                if isinstance(f, dict) and f.get("presente") is False]
    if faltando:
        print(f"[CONSOLIDAR] ATENÇÃO: fontes ausentes: {faltando}. "
              "Os indicadores correspondentes estão nulos, não zerados.")


if __name__ == "__main__":
    main()
