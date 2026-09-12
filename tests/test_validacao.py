"""
tests/test_validacao.py
Integridade do conjunto publicado, contra âncoras conhecidas.

As âncoras foram apuradas no Censo 2024, no CPC 2023 e no CNES 202607, e
conferidas contra o recorte bruto. Servem como teste de REGRESSÃO: se o pipeline passar a produzir
outra coisa, o mais provável é defeito no pipeline, não notícia nos dados. Uma
edição nova do Censo muda os números de propósito — e aí estas constantes mudam
junto, num commit que diz isso.

Roda como script ou sob pytest.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

CENSO = 2024
CICLO_CPC = "2023"
COMPETENCIA_CNES = "202607"

# ------------------------------------------------------------------ âncoras
REGISTROS_CENSO = 939
UFS_COM_PRESENCIAL = 24
UFS_SEM_PRESENCIAL = ["AP", "MS", "RR"]
MUNICIPIOS_COM_OFERTA = 83
VAGAS_PRESENCIAL = 17028
VAGAS_EAD = 12876
POLOS_REGISTROS = 793
POLOS_MUNICIPIOS = 618
MATRICULAS = 22996
CONCLUINTES = 2027
IES_DISTINTAS = 129

CURSOS_AVALIADOS = 74
UFS_AVALIADAS = 23
CURSOS_COM_CPC = 73
CURSOS_COM_IDD = 68

# --------------------------------------------------------- âncoras: CNES 202607
# A cobertura assistencial nunca teve âncora neste projeto, e foi justamente
# por isso que uma mudança de 2.230 para 2.118 municípios passaria despercebida.
MUNICIPIOS_COM_FONOAUDIOLOGO = 4207
FONOAUDIOLOGOS_SUS = 23760
# Rede especializada: só o que é ofertado AO SUS entra no índice; o total
# declarado, que inclui a clínica privada, fica ao lado.
MUNICIPIOS_COM_SERVICO_FONO = 2118
MUNICIPIOS_COM_SERVICO_FONO_TOTAL = 2230

MUNICIPIOS_BRASIL = 5571          # IBGE, desde a instalação de Boa Esperança
MUNICIPIOS_MT = 142               # do Norte (MT) em 01/01/2025


def _ler(nome):
    caminho = DATA / nome
    if not caminho.exists():
        raise SystemExit(
            f"[ERRO] {caminho} ausente. Rode o pipeline antes dos testes.")
    return json.loads(caminho.read_text(encoding="utf-8"))


def _soma(ufs, campo):
    return sum(d.get(campo) or 0 for d in ufs.values())


# ------------------------------------------------------------------ território

def test_27_ufs_presentes():
    ufs = _ler("nacional.json")["ufs"]
    assert len(ufs) == 27, f"esperado 27 UFs, veio {len(ufs)}"


def test_ufs_sem_oferta_aparecem_explicitamente():
    """
    AP, MS e RR não têm curso presencial — e precisam estar no conjunto.

    Omiti-las faria o mapa parecer completo e o país parecer coberto. Um estado
    cinza é informação; um estado ausente é uma afirmação que ninguém fez.
    """
    ufs = _ler("nacional.json")["ufs"]
    sem = sorted(u for u, d in ufs.items() if not d.get("tem_oferta_presencial"))
    assert sem == UFS_SEM_PRESENCIAL, f"esperado {UFS_SEM_PRESENCIAL}, veio {sem}"
    for sigla in UFS_SEM_PRESENCIAL:
        assert sigla in ufs, f"{sigla} foi omitida do conjunto"
        assert ufs[sigla]["municipios_total"] > 0, (
            f"{sigla} sem contagem de municípios")


def test_ufs_com_presencial():
    ufs = _ler("nacional.json")["ufs"]
    com = [u for u, d in ufs.items() if d.get("tem_oferta_presencial")]
    assert len(com) == UFS_COM_PRESENCIAL, (
        f"esperado {UFS_COM_PRESENCIAL} UFs com oferta presencial, veio {len(com)}")


def test_contagem_de_municipios_do_ibge():
    ufs = _ler("nacional.json")["ufs"]
    total = _soma(ufs, "municipios_total")
    assert total == MUNICIPIOS_BRASIL, (
        f"esperado {MUNICIPIOS_BRASIL} municípios, veio {total}. "
        "Se o IBGE instalou ou extinguiu município, a mudança é real — "
        "atualize a âncora num commit que explique.")
    assert ufs["MT"]["municipios_total"] == MUNICIPIOS_MT, (
        f"MT deveria ter {MUNICIPIOS_MT} municípios, "
        f"veio {ufs['MT']['municipios_total']}")


def test_municipios_com_oferta():
    ufs = _ler("nacional.json")["ufs"]
    total = _soma(ufs, "municipios_oferta")
    assert total == MUNICIPIOS_COM_OFERTA, (
        f"esperado {MUNICIPIOS_COM_OFERTA}, veio {total}")


# ------------------------------------------------------------------ capacidade

def test_vagas_presenciais_e_ead():
    """
    As duas camadas da EaD somadas separadamente.

    Somar QT_VG_TOTAL por SG_UF sem separar sede de polo devolve vagas EaD
    zeradas — e o resultado parece plausível, que é o que torna o erro caro.
    """
    ufs = _ler("nacional.json")["ufs"]
    presencial = _soma(ufs, "vagas_presencial")
    ead = _soma(ufs, "vagas_ead")
    assert presencial == VAGAS_PRESENCIAL, (
        f"vagas presenciais: esperado {VAGAS_PRESENCIAL}, veio {presencial}")
    assert ead == VAGAS_EAD, f"vagas EaD: esperado {VAGAS_EAD}, veio {ead}"
    assert ead > 0, ("vagas EaD zeradas — sintoma clássico de somar as linhas "
                     "de polo em vez das de sede")


def test_polos_ead():
    ufs = _ler("nacional.json")["ufs"]
    assert _soma(ufs, "ead_polos_registros") == POLOS_REGISTROS
    assert _soma(ufs, "ead_polos_municipios") == POLOS_MUNICIPIOS


def test_fluxo():
    ufs = _ler("nacional.json")["ufs"]
    assert _soma(ufs, "matriculas") == MATRICULAS, (
        f"matrículas: esperado {MATRICULAS}, veio {_soma(ufs, 'matriculas')}")
    assert _soma(ufs, "concluintes") == CONCLUINTES


def test_concentracao_inclui_ead():
    """
    HHI de mantenedora precisa refletir a capacidade total.

    Calculado só sobre o presencial, SP dá 0,07 — como se o estado tivesse um
    mercado pulverizado. Com a EaD atribuída à UF-sede, dá 0,18. A concentração
    mora justamente nos grandes grupos de EaD.
    """
    ufs = _ler("nacional.json")["ufs"]
    sp = ufs["SP"]
    assert sp["HHI_mantenedora"] is not None
    assert sp["HHI_mantenedora"] > 0.12, (
        f"HHI_mantenedora de SP = {sp['HHI_mantenedora']}; abaixo de 0,12 "
        "indica cálculo feito só sobre o presencial")
    for sigla, d in ufs.items():
        if d["vagas_total"]:
            assert d["HHI"] is not None, f"{sigla} com vagas mas sem HHI"
            assert 0 <= d["HHI"] <= 1, f"{sigla}: HHI fora de 0..1"


# ------------------------------------------------------------------- qualidade

def test_qualidade_cpc():
    q = _ler("qualidade.json")
    assert q["metadados"]["ciclo"] == CICLO_CPC
    assert len(q["cursos"]) == CURSOS_AVALIADOS, (
        f"esperado {CURSOS_AVALIADOS} cursos avaliados, veio {len(q['cursos'])}")
    assert len(q["ufs"]) == UFS_AVALIADAS
    com_cpc = sum(1 for c in q["cursos"] if c["CPC_cont"] is not None)
    com_idd = sum(1 for c in q["cursos"] if c["IDD"] is not None)
    assert com_cpc == CURSOS_COM_CPC, f"com CPC: esperado {CURSOS_COM_CPC}, veio {com_cpc}"
    assert com_idd == CURSOS_COM_IDD, f"com IDD: esperado {CURSOS_COM_IDD}, veio {com_idd}"


def test_uf_com_oferta_e_sem_avaliacao_fica_nula():
    """
    Tocantins tem curso presencial e nenhum curso no ciclo do CPC 2023.

    Os indicadores de qualidade têm de ficar `None` — não zero. Zero colocaria
    TO no fundo de qualquer ranking de qualidade como se tivesse sido avaliado
    e tivesse ido mal.
    """
    ufs = _ler("nacional.json")["ufs"]
    to = ufs["TO"]
    assert to["tem_oferta_presencial"] is True
    for campo in ("CPC", "CPC_cont", "IDD", "IAF"):
        assert to[campo] is None, (
            f"TO.{campo} deveria ser None (sem curso avaliado), veio {to[campo]}")


# ------------------------------------------------------- princípio inegociável

def test_ausencia_nunca_e_zero():
    """
    Varre o conjunto atrás de zeros que deveriam ser nulos.

    Regra: se a UF não tem oferta presencial, os índices que dependem dela não
    podem ter valor numérico. `None` chega à tela como "sem dados"; `0` chega
    como afirmação.
    """
    ufs = _ler("nacional.json")["ufs"]
    problemas = []
    for sigla, d in ufs.items():
        if d.get("tem_oferta_presencial"):
            continue
        for campo in ("ICT", "E", "IAF", "HHI", "HHI_mantenedora", "CR2", "CR10"):
            if d.get(campo) is not None:
                problemas.append(f"{sigla}.{campo} = {d[campo]} (deveria ser None)")
    assert not problemas, "valores numéricos onde deveria haver ausência:\n  - " \
                          + "\n  - ".join(problemas)


def test_iaf_so_existe_com_os_tres_componentes():
    ufs = _ler("nacional.json")["ufs"]
    problemas = []
    for sigla, d in ufs.items():
        tem_tudo = (d.get("CPC") is not None
                    and d.get("vagas_avaliadas") is not None
                    and d.get("ICT") is not None)
        if d.get("IAF") is not None and not tem_tudo:
            problemas.append(f"{sigla}: IAF={d['IAF']} sem os três componentes")
        if d.get("IAF") is None and tem_tudo:
            problemas.append(f"{sigla}: componentes completos mas IAF nulo")
    assert not problemas, "\n  - ".join(problemas)


def test_percentuais_dentro_da_faixa():
    ufs = _ler("nacional.json")["ufs"]
    problemas = []
    for sigla, d in ufs.items():
        for campo, valor in d.items():
            if campo.startswith("pct_") and valor is not None:
                if not 0 <= valor <= 100:
                    problemas.append(f"{sigla}.{campo} = {valor}")
    assert not problemas, "percentuais fora de 0..100:\n  - " + "\n  - ".join(problemas)


# ---------------------------------------------------------------- proveniência

def test_proveniencia_vem_do_arquivo():
    """
    O ano do Censo tem de vir do arquivo lido, não do calendário.

    Derivar `ano - 1` da data de hoje rotula o Censo 2024 como 2025 durante todo
    o ano seguinte, e o erro só aparece muito depois, num gráfico de série.
    """
    meta = _ler("nacional.json")["metadados"]
    assert meta["ano_censo"] == CENSO
    prov = meta["proveniencia"]["fontes"]["censo"]
    assert prov.get("ano_censo") == CENSO
    assert prov.get("md5_publicado"), "sem md5 publicado pelo INEP na proveniência"
    assert str(CENSO) in prov.get("membro_cursos", ""), (
        "o membro lido não confere com o ano declarado")


def test_ancoras_da_cobertura_do_cnes():
    """
    Totais conhecidos do CNES 202607, como teste de regressão.

    Este projeto publicava cobertura assistencial sem nenhuma âncora: o número
    podia mudar de uma execução para outra sem nada acusar. Foi assim que a
    contagem da rede especializada ficou incluindo clínica privada até ser
    corrigida — 2.230 municípios onde a rede pública alcança 2.118.
    """
    ufs = _ler("nacional.json")["ufs"]
    for campo, esperado in [
        ("municipios_com_fonoaudiologo", MUNICIPIOS_COM_FONOAUDIOLOGO),
        ("fonoaudiologos_sus", FONOAUDIOLOGOS_SUS),
        ("municipios_com_servico_fono", MUNICIPIOS_COM_SERVICO_FONO),
        ("municipios_com_servico_fono_total", MUNICIPIOS_COM_SERVICO_FONO_TOTAL),
    ]:
        obtido = _soma(ufs, campo)
        assert obtido == esperado, (
            f"{campo}: esperado {esperado}, veio {obtido}")

    prov = _ler("_proveniencia.json")["fontes"]["cnes"]
    assert prov.get("competencia") == COMPETENCIA_CNES


def test_rede_especializada_publica_e_menor_que_a_declarada():
    """
    O filtro de SUS precisa continuar existindo.

    Sem ele, a clínica privada que declara serviço fonoaudiológico no cadastro
    entra como rede pública: medido, isso leva a cobertura de 2.118 para 2.230
    municípios e os estabelecimentos de 5.471 para 9.159 — 40% do que seria
    contado como rede pública não atende pelo SUS. Se os dois números
    empatarem, o filtro caiu.
    """
    ufs = _ler("nacional.json")["ufs"]
    sus = _soma(ufs, "municipios_com_servico_fono")
    total = _soma(ufs, "municipios_com_servico_fono_total")
    assert sus < total, (
        f"municípios com serviço ao SUS ({sus}) igualou o total declarado "
        f"({total}) — o filtro CO_AMBULATORIAL_SUS/CO_HOSPITALAR_SUS caiu")


def test_st_ativo_sn_nao_passa_por_filtro():
    """
    A coluna vem vazia no export, e isso precisa continuar declarado.

    O extrator tinha um filtro que lia ST_ATIVO_SN e excluía o que estivesse
    marcado como inativo. Medido: a coluna está em branco em 100% das linhas —
    o filtro nunca excluiu nada, em nenhuma execução, e existia dando a
    impressão de que a limpeza acontecia. Se uma competência futura passar a
    preencher a coluna, este teste falha e a decisão volta a ser possível.
    """
    diag = (_ler("_proveniencia.json")["fontes"]["cnes"].get("diagnostico")
            or {})
    assert diag.get("st_ativo_sn_vazio_no_export") is True, (
        "ST_ATIVO_SN deixou de vir vazia: "
        f"{diag.get('servicos_com_situacao_preenchida')} linhas com situação "
        "preenchida. Vale reavaliar se o filtro de serviço inativo deve voltar.")

    texto = " ".join(_ler("_proveniencia.json")["limitacoes_conhecidas"]).lower()
    assert "st_ativo_sn" in texto, (
        "a limitação do ST_ATIVO_SN não está declarada na proveniência")


def test_limitacoes_declaradas():
    """O que não foi medido precisa estar escrito, não subentendido."""
    prov = _ler("_proveniencia.json")
    texto = " ".join(prov["limitacoes_conhecidas"]).lower()
    assert "cer" in texto, "a indisponibilidade do CER não está declarada"
    assert "presencial" in texto, "as UFs sem oferta presencial não estão declaradas"


def main():
    testes = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    falhas = 0
    for teste in testes:
        try:
            teste()
            print(f"  OK      {teste.__name__}")
        except AssertionError as e:
            falhas += 1
            print(f"  FALHOU  {teste.__name__}: {e}")
    print(f"\n{len(testes) - falhas}/{len(testes)} testes de integridade passaram.")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
