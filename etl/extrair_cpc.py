"""
etl/extrair_cpc.py
Extrai do CPC 2023 (INEP) os indicadores de qualidade dos cursos de
Fonoaudiologia: CPC, ENADE, IDD, perfil docente e as dimensões avaliadas
pelos estudantes.

Uso:
    python etl/extrair_cpc.py
    python etl/extrair_cpc.py --area FONOAUDIOLOGIA --ciclo 2023

Saída: data/qualidade.json (por curso e agregado por UF).

Fonoaudiologia ESTÁ no ciclo do CPC 2023: 74 cursos avaliados em 23 UFs, 73 com
CPC contínuo e 68 com IDD. Não há adaptação de fórmula a fazer — só respeitar
as lacunas.

TRÊS CASAS DECIMAIS, PONDERADO POR CONCLUINTES PARTICIPANTES
-------------------------------------------------------------
As médias por UF são ponderadas pelo número de concluintes participantes, e
arredondadas com TRÊS casas. Com duas, nenhuma UF reproduz o valor publicado —
um curso com 4 participantes e outro com 180 movem a terceira casa, e a
diferença aparece exatamente onde alguém vai conferir.

O COMPONENTE Q DO IAF USA CPC (FAIXA), NÃO O CONTÍNUO
------------------------------------------------------
`q_qualidade` espera conceitos na escala 1 a 5, porque calcula (v−1)/4. O CPC
contínuo vai de 0 a 5 e produziria componente negativo para os cursos abaixo de
1. As faixas de ENADE e IDD não vêm nesta planilha, e derivá-las dos contínuos
seria reconstruir número que o INEP não publicou — então Q usa só o CPC em
faixa. ENADE contínuo, IDD, docentes e dimensões são publicados como
indicadores próprios, não dobrados dentro do Q.

CABEÇALHO DA PLANILHA VEM COM ESPAÇO À ESQUERDA
------------------------------------------------
As colunas do arquivo do INEP chegam como ' Ano', ' Área de Avaliação' — com um
espaço inicial que não aparece ao imprimir. Buscar por nome exato falha com
KeyError; buscar por nome normalizado, não. Por isso `_coluna()`.
"""
import argparse
import csv
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

from rede import baixar, sondar

REPO = Path(__file__).parent.parent
DADOS = REPO / "etl" / "dados"
DATA = REPO / "data"

URL_CPC = ("https://download.inep.gov.br/educacao_superior/indicadores/"
           "resultados/{ciclo}/CPC_{ciclo}.xlsx")


def normalizar(texto):
    s = unicodedata.normalize("NFD", str(texto or "").strip().upper())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)


def _coluna(colunas, *trechos):
    """Acha a coluna cujo nome normalizado contém todos os trechos."""
    alvos = [normalizar(t) for t in trechos]
    for original in colunas:
        norm = normalizar(original)
        if all(a in norm for a in alvos):
            return original
    return None


def _num(serie):
    """Texto -> número, com vírgula decimal e vazio virando NaN."""
    return pd.to_numeric(
        serie.astype(str).str.strip().str.replace(",", ".", regex=False),
        errors="coerce")


def baixar_planilha(ciclo, forcar=False):
    url = URL_CPC.format(ciclo=ciclo)
    destino = DADOS / f"CPC_{ciclo}.xlsx"
    if destino.exists() and not forcar:
        print(f"[CPC] usando cópia local {destino.name}")
        return destino, url
    existe, detalhe = sondar(url)
    if existe is False:
        raise SystemExit(f"[ERRO] CPC {ciclo} confirmadamente ausente em {url}")
    if existe is None:
        raise SystemExit(
            f"[ERRO] não foi possível verificar {url} ({detalhe}). "
            "Indeterminado não é ausente — tente de novo em vez de seguir sem o dado.")
    baixar(url, destino)
    return destino, url


def carregar(caminho, area, ciclo):
    bruto = pd.read_excel(caminho, sheet_name=f"CPC_{ciclo}", dtype=str)
    bruto.columns = [str(c).strip() for c in bruto.columns]
    cols = list(bruto.columns)

    mapa = {
        "area": _coluna(cols, "AREA", "AVALIACAO"),
        "cod_area": _coluna(cols, "CODIGO", "AREA"),
        "cod_ies": _coluna(cols, "CODIGO", "IES"),
        "nome_ies": _coluna(cols, "NOME", "IES"),
        "sigla_ies": _coluna(cols, "SIGLA", "IES"),
        "categoria": _coluna(cols, "CATEGORIA", "ADMINISTRATIVA"),
        "cod_curso": _coluna(cols, "CODIGO", "CURSO"),
        "modalidade": _coluna(cols, "MODALIDADE"),
        "cod_mun": _coluna(cols, "CODIGO", "MUNICIPIO"),
        "municipio": _coluna(cols, "MUNICIPIO", "CURSO"),
        "uf": _coluna(cols, "SIGLA", "UF"),
        "concluintes": _coluna(cols, "CONCLUINTES", "PARTICIPANTES"),
        "enade_cont": _coluna(cols, "CONCEITO ENADE", "CONTINUO"),
        "idd": _coluna(cols, "NOTA PADRONIZADA", "IDD"),
        "cpc_cont": _coluna(cols, "CPC", "CONTINUO"),
        "cpc_faixa": _coluna(cols, "CPC", "FAIXA"),
        "mestres": _coluna(cols, "NOTA BRUTA", "MESTRES"),
        "doutores": _coluna(cols, "NOTA BRUTA", "DOUTORES"),
        "regime": _coluna(cols, "NOTA BRUTA", "REGIME"),
        "dim_didatica": _coluna(cols, "NOTA BRUTA", "DIDATICO"),
        "dim_infra": _coluna(cols, "NOTA BRUTA", "INFRAESTRUTURA"),
        "dim_oportunidade": _coluna(cols, "NOTA BRUTA", "OPORTUNIDADE"),
    }
    faltando = [k for k, v in mapa.items() if v is None]
    if faltando:
        raise SystemExit(
            f"[ERRO] colunas não localizadas na planilha: {faltando}\n"
            f"Colunas disponíveis: {cols}")

    df = bruto[[v for v in mapa.values()]].copy()
    df.columns = list(mapa)

    alvo = normalizar(area)
    df = df[df["area"].map(normalizar) == alvo].copy()
    if df.empty:
        disponiveis = sorted({normalizar(a) for a in bruto[mapa["area"]].dropna()})
        raise SystemExit(
            f"[ERRO] área {area!r} não encontrada. Match é EXATO, não substring.\n"
            f"Áreas com trecho parecido: "
            f"{[a for a in disponiveis if alvo.split()[0][:4] in a]}")

    for col in ("concluintes", "enade_cont", "idd", "cpc_cont", "cpc_faixa",
                "mestres", "doutores", "regime",
                "dim_didatica", "dim_infra", "dim_oportunidade"):
        df[col] = _num(df[col])
    return df


def vagas_por_curso(ano_censo):
    """CO_CURSO -> vagas, lido do recorte do Censo já extraído."""
    caminho = DADOS / f"curso_fonoaudiologia_{ano_censo}.csv"
    if not caminho.exists():
        print(f"[CPC] {caminho.name} ausente — vagas_avaliadas ficará nulo. "
              "Rode etl/extrair_censo.py antes para preencher.")
        return {}
    vagas = {}
    with open(caminho, encoding="utf-8") as f:
        for linha in csv.DictReader(f, delimiter=";"):
            codigo = (linha.get("CO_CURSO") or "").strip()
            bruto = (linha.get("QT_VG_TOTAL") or "").strip()
            if codigo and bruto.lstrip("-").isdigit():
                vagas[codigo] = vagas.get(codigo, 0) + int(bruto)
    return vagas


def _ponderada(grupo, coluna, casas=3, fator=1.0):
    """
    Média ponderada por concluintes participantes, `casas` decimais.

    Cursos sem valor na coluna saem da conta — não entram como zero. Um curso
    sem IDD não é um curso com IDD zero, e a diferença muda o ranking da UF.
    """
    sub = grupo.dropna(subset=[coluna])
    if sub.empty:
        return None
    pesos = sub["concluintes"].fillna(0)
    if pesos.sum() > 0:
        valor = float((sub[coluna] * pesos).sum() / pesos.sum())
    else:
        valor = float(sub[coluna].mean())
    return round(valor * fator, casas)


def agregar(df, vagas, ciclo, url, area):
    cursos = []
    for _, linha in df.iterrows():
        codigo = str(linha["cod_curso"]).strip()
        cursos.append({
            "cod_curso": codigo,
            "cod_ies": str(linha["cod_ies"]).strip(),
            "ies": linha["nome_ies"],
            "sigla_ies": linha["sigla_ies"],
            "categoria": linha["categoria"],
            "modalidade": linha["modalidade"],
            "uf": linha["uf"],
            "municipio": linha["municipio"],
            "cod_municipio": str(linha["cod_mun"]).strip(),
            "concluintes_participantes": _ou_nulo(linha["concluintes"], int),
            "CPC_faixa": _ou_nulo(linha["cpc_faixa"], int),
            "CPC_cont": _ou_nulo(linha["cpc_cont"], lambda v: round(v, 3)),
            "ENADE_cont": _ou_nulo(linha["enade_cont"], lambda v: round(v, 3)),
            "IDD": _ou_nulo(linha["idd"], lambda v: round(v, 3)),
            "vagas": vagas.get(codigo),
        })

    ufs = {}
    for uf, grupo in df.groupby("uf"):
        codigos = {str(c).strip() for c in grupo["cod_curso"]}
        avaliadas = [vagas[c] for c in codigos if c in vagas]
        ufs[str(uf).strip().upper()] = {
            "n_cursos_avaliados": int(len(grupo)),
            "n_com_cpc": int(grupo["cpc_cont"].notna().sum()),
            "n_com_idd": int(grupo["idd"].notna().sum()),
            "concluintes_participantes": int(grupo["concluintes"].fillna(0).sum()),
            # Q do IAF vem daqui: escala 1 a 5.
            "CPC": _ponderada(grupo, "cpc_faixa"),
            "CPC_cont": _ponderada(grupo, "cpc_cont"),
            "ENADE_cont": _ponderada(grupo, "enade_cont"),
            "IDD": _ponderada(grupo, "idd"),
            # perfil docente: as notas brutas são proporções 0 a 1.
            "pct_doc_mestres": _ponderada(grupo, "mestres", casas=1, fator=100),
            "pct_doc_doutores": _ponderada(grupo, "doutores", casas=1, fator=100),
            "pct_doc_regime_integral": _ponderada(grupo, "regime", casas=1, fator=100),
            # dimensões avaliadas pelos estudantes: notas brutas 0 a 5.
            "dim_didatico_pedagogica": _ponderada(grupo, "dim_didatica"),
            "dim_infraestrutura": _ponderada(grupo, "dim_infra"),
            "dim_oportunidade_formacao": _ponderada(grupo, "dim_oportunidade"),
            # vagas em cursos avaliados: componente V do IAF.
            "vagas_avaliadas": sum(avaliadas) if avaliadas else None,
            "cursos_sem_vagas_no_censo": sorted(c for c in codigos if c not in vagas),
        }

    return {
        "metadados": {
            "fonte": "Conceito Preliminar de Curso (INEP)",
            "url": url,
            "ciclo": ciclo,                 # do ARQUIVO, não do calendário
            "area_avaliacao": area,
            "match": "igualdade sobre o rótulo normalizado, nunca substring",
            "ponderacao": "média ponderada por concluintes participantes, 3 casas",
            "componente_q_do_iaf": "CPC (Faixa), escala 1 a 5",
            "cursos_avaliados": len(cursos),
            "ufs_avaliadas": len(ufs),
            "extraido_em": date.today().isoformat(),
        },
        "ufs": ufs,
        "cursos": cursos,
    }


def _ou_nulo(valor, conversor):
    if valor is None or pd.isna(valor):
        return None
    return conversor(float(valor))


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ciclo", default="2023")
    p.add_argument("--area", default="FONOAUDIOLOGIA")
    p.add_argument("--ano-censo", type=int, default=2024)
    p.add_argument("--forcar-download", action="store_true")
    p.add_argument("--saida", default=str(DATA / "qualidade.json"))
    args = p.parse_args()

    caminho, url = baixar_planilha(args.ciclo, args.forcar_download)
    df = carregar(caminho, args.area, args.ciclo)
    print(f"[CPC] {len(df)} cursos de {args.area} no ciclo {args.ciclo}; "
          f"{df['uf'].nunique()} UFs")
    print(f"[CPC] com CPC contínuo: {int(df['cpc_cont'].notna().sum())}; "
          f"com IDD: {int(df['idd'].notna().sum())}")

    vagas = vagas_por_curso(args.ano_censo)
    saida = agregar(df, vagas, args.ciclo, url, args.area)

    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(
        json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[CPC] -> {args.saida}")

    sem_vagas = sum(len(u["cursos_sem_vagas_no_censo"]) for u in saida["ufs"].values())
    if sem_vagas:
        print(f"[CPC] atenção: {sem_vagas} cursos avaliados sem correspondência "
              "de vagas no Censo (curso extinto ou código alterado). "
              "Ficam fora de vagas_avaliadas, não entram como zero.")


if __name__ == "__main__":
    main()
