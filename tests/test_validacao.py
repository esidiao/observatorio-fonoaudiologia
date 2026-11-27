"""
tests/test_validacao.py
Integridade do conjunto publicado, contra âncoras conhecidas.

As âncoras foram apuradas no Censo 2025, no CPC 2023 e no CNES 202609, e
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

CENSO = 2025
CICLO_CPC = "2023"
COMPETENCIA_CNES = "202609"

# ------------------------------------------------------------------ âncoras
#
# A EDIÇÃO MUDOU DE FORMA, NÃO SÓ DE NÚMERO.
#
# O INEP normalizou os microdados em 2025: o cadastro único virou sete tabelas
# e `TP_DIMENSAO` deixou de existir. Por isso `REGISTROS_CENSO` cai de 939 para
# 209 sem que nada tenha encolhido — antes era uma linha por curso E POR
# CAMADA, agora é uma linha por curso.
#
# E o Decreto 12.456/2025 encerrou a graduação em saúde inteiramente a
# distância. Em Fonoaudiologia não resta nenhum curso a distância em atividade:
# os 24 que existem estão, um a um, declarados em extinção. No lugar deles
# apareceu o formato SEMIPRESENCIAL — e ele é maior que todo o presencial do
# país: 33.256 vagas contra 23.429.
REGISTROS_CENSO = 209            # cursos, não mais curso × camada

# DUAS UFs DEIXARAM DE SER DESERTO, E ISSO É NOTÍCIA, NÃO DEFEITO.
#
# Até o Censo 2024 três estados não tinham nenhum curso presencial de
# Fonoaudiologia: Amapá, Mato Grosso do Sul e Roraima. Em 2025, Mato Grosso do
# Sul abriu três cursos presenciais e Roraima abriu um. Só o Amapá continua sem.
# Conferido no recorte bruto das duas edições, não deduzido do agregado.
UFS_COM_PRESENCIAL = 26
UFS_SEM_PRESENCIAL = ["AP"]

MUNICIPIOS_COM_OFERTA = 119      # presencial ou semipresencial, em atividade
VAGAS_PRESENCIAL = 23429
VAGAS_SEMIPRESENCIAL = 33256     # categoria nova, e maior que o presencial
VAGAS_EAD = 0                    # encerrada por decreto
VAGAS_EM_EXTINCAO = 39580        # fora da capacidade ativa, publicada ao lado
VAGAS_TOTAL_ATIVA = 56685        # presencial + semipresencial

# Polos contados por LOCAL distinto e separados pela situação do curso que
# atendem. Polo de curso presencial não entra em nenhum dos dois: a fonte marca
# 100 endereços de curso presencial como polo, e contá-los como alcance de
# oferta não presencial seria inflar o país.
POLOS_REGISTROS = 3345           # rede ativa (semipresencial)
POLOS_MUNICIPIOS = 1404
POLOS_EM_EXTINCAO = 5755         # rede que está sendo desmontada
POLOS_EM_EXTINCAO_MUNICIPIOS = 1851
# Polo que a fonte não localiza: contado e declarado, nunca atribuído a UF.
POLOS_SEM_UF_ATIVOS = 21
POLOS_SEM_UF_EM_EXTINCAO = 26
# Linhas de polo que a fonte traz sem identificar o local. O código vazio
# entrava no conjunto de locais como se fosse um local, e todas as linhas sem
# código de uma mesma UF colapsavam em UM polo que não existe. O município
# delas, que é conhecido, continua contando no alcance.
POLOS_SEM_CODIGO_ATIVOS = 9
POLOS_SEM_CODIGO_EM_EXTINCAO = 21

# Pessoas NÃO se filtram por situação: quem está matriculado agora existe, e
# tem direito a concluir no formato em que ingressou.
MATRICULAS = 49505
CONCLUINTES = 2463
INGRESSOS = 35116
MATRICULAS_EM_EXTINCAO = 25574
# 22.073 de 35.116: quase dois terços de quem entrou em Fonoaudiologia neste
# ano entrou num curso já declarado em extinção.
INGRESSOS_EM_EXTINCAO = 22073

# Soma das contagens por UF. NÃO é o número de instituições do país: quem atua
# em três estados é contada três vezes. As distintas são 172, e a diferença
# está declarada na página da série.
IES_DISTINTAS = 182

# Oferta sem endereço próprio, atribuída à UF-sede da mantenedora: cinco
# linhas a distância e quatro semipresenciais, nenhuma presencial. São 41.152
# vagas — 73% da capacidade ativa do país. Descartá-las publicaria uma
# Fonoaudiologia de um quarto do tamanho que ela tem.
ATRIBUIDAS_PELA_SEDE_LINHAS = 9
ATRIBUIDAS_PELA_SEDE_VAGAS = 41152

CURSOS_AVALIADOS = 74
UFS_AVALIADAS = 23
CURSOS_COM_CPC = 73
CURSOS_COM_IDD = 68

# --------------------------------------------------------- âncoras: CNES 202609
# A cobertura assistencial nunca teve âncora neste projeto, e foi justamente
# por isso que uma mudança de 2.230 para 2.118 municípios passaria despercebida
# (números da 202607, quando o defeito foi encontrado).
#
# Ao trocar de competência, estes números MUDAM, e é por isso que a troca
# falha o teste em vez de passar calada: cada valor abaixo foi reconferido
# contra a competência declarada acima, não ajustado até o teste passar.
MUNICIPIOS_COM_FONOAUDIOLOGO = 4244
FONOAUDIOLOGOS_SUS = 24124
# Rede especializada: só o que é ofertado AO SUS entra no índice; o total
# declarado, que inclui a clínica privada, fica ao lado.
MUNICIPIOS_COM_SERVICO_FONO = 2150
MUNICIPIOS_COM_SERVICO_FONO_TOTAL = 2266

MUNICIPIOS_BRASIL = 5571          # IBGE, desde a instalação de Boa Esperança
MUNICIPIOS_MT = 142               # do Norte (MT) em 01/01/2025


def _ler(nome):
    caminho = DATA / nome
    if not caminho.exists():
        raise SystemExit(
            f"[ERRO] {caminho} ausente. Rode o pipeline antes dos testes.")
    return json.loads(caminho.read_text(encoding="utf-8"))


def _esquema():
    prov = _ler("_proveniencia.json").get("fontes", {}).get("censo", {})
    return prov.get("esquema", "unico")


def _fatia_de_curso():
    import csv
    csv.field_size_limit(1 << 24)
    caminho = (DATA.parent / "etl" / "dados"
               / f"curso_fonoaudiologia_{CENSO}.csv")
    if not caminho.exists():
        return None
    with caminho.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


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

def test_composicao_da_capacidade_ativa():
    """
    Cada formato somado separadamente — e o zero da EaD tem de ser provado.

    ATÉ 2024 ESTE TESTE EXIGIA O CONTRÁRIO. Ele dizia que "vagas EaD zeradas é
    sintoma clássico de somar as linhas de polo em vez das de sede", e exigia
    `ead > 0`. Era um bom guarda: naquele modelo, zero só podia ser defeito de
    leitura.

    Em 2025 zero é a verdade — o Decreto 12.456/2025 encerrou a graduação em
    saúde inteiramente a distância. Trocar `> 0` por `== 0` resolveria a falha
    e perderia o guarda: as duas causas possíveis de um zero, a lei e o defeito
    de leitura, ficariam indistinguíveis.

    Então o zero passa a exigir PROVA: se não há capacidade ativa a distância,
    tem de haver capacidade em extinção a distância. É o rastro que a lei deixa
    e que um erro de leitura não deixaria — um pipeline que somasse a tabela
    errada zeraria os dois.
    """
    ufs = _ler("nacional.json")["ufs"]
    presencial = _soma(ufs, "vagas_presencial")
    semi = _soma(ufs, "vagas_semipresencial")
    ead = _soma(ufs, "vagas_ead")
    extin = _soma(ufs, "vagas_em_extincao")

    assert presencial == VAGAS_PRESENCIAL, (
        f"vagas presenciais: esperado {VAGAS_PRESENCIAL}, veio {presencial}")
    assert semi == VAGAS_SEMIPRESENCIAL, (
        f"vagas semipresenciais: esperado {VAGAS_SEMIPRESENCIAL}, veio {semi}")
    assert ead == VAGAS_EAD, f"vagas EaD: esperado {VAGAS_EAD}, veio {ead}"
    assert extin == VAGAS_EM_EXTINCAO, (
        f"vagas em extinção: esperado {VAGAS_EM_EXTINCAO}, veio {extin}")

    if ead == 0:
        assert extin > 0, (
            "capacidade ativa a distância zerada E nenhuma capacidade em "
            "extinção. Um zero por força de lei deixa rastro — os cursos "
            "encerrados continuam no cadastro. Zero nos dois é sintoma de "
            "leitura errada, não de regulação.")

    assert _soma(ufs, "vagas_total") == VAGAS_TOTAL_ATIVA, (
        f"capacidade ativa: esperado {VAGAS_TOTAL_ATIVA}, veio "
        f"{_soma(ufs, 'vagas_total')}")
    assert presencial + semi + ead == VAGAS_TOTAL_ATIVA, (
        "a capacidade ativa publicada não é a soma dos formatos ativos")


def test_polos_ead():
    """
    As três populações de polo, contadas separadamente.

    A bandeira de polo marca, na mesma tabela, a rede de curso em extinção, a
    de curso ativo não presencial e o endereço de curso PRESENCIAL. Somar as
    três publica um alcance que não corresponde a rede nenhuma.

    E o polo que a fonte não localiza é contado e declarado, nunca atribuído: o
    total nacional é a soma das UFs, então sem essa declaração ele fica alguns
    polos abaixo das linhas da fonte, sem nada explicando a diferença.
    """
    ufs = _ler("nacional.json")["ufs"]
    assert _soma(ufs, "ead_polos_registros") == POLOS_REGISTROS, (
        f"polos da rede ativa: esperado {POLOS_REGISTROS}, veio "
        f"{_soma(ufs, 'ead_polos_registros')}")
    assert _soma(ufs, "ead_polos_municipios") == POLOS_MUNICIPIOS
    assert _soma(ufs, "polos_em_extincao") == POLOS_EM_EXTINCAO, (
        f"polos da rede em extinção: esperado {POLOS_EM_EXTINCAO}, veio "
        f"{_soma(ufs, 'polos_em_extincao')}")
    assert (_soma(ufs, "polos_em_extincao_municipios")
            == POLOS_EM_EXTINCAO_MUNICIPIOS)

    sem_uf = ((_ler("bruto.json")["metadados"].get("sem_localizacao") or {})
              .get("polos_sem_uf") or {})
    assert sem_uf.get("ativos") == POLOS_SEM_UF_ATIVOS, (
        f"polos ativos sem UF: esperado {POLOS_SEM_UF_ATIVOS}, veio "
        f"{sem_uf.get('ativos')}")
    assert sem_uf.get("em_extincao") == POLOS_SEM_UF_EM_EXTINCAO
    sem_codigo = ((_ler("bruto.json")["metadados"].get("sem_localizacao") or {})
                  .get("polos_sem_codigo") or {})
    assert sem_codigo.get("ativos") == POLOS_SEM_CODIGO_ATIVOS, (
        f"linhas de polo ativo sem código de local: esperado "
        f"{POLOS_SEM_CODIGO_ATIVOS}, veio {sem_codigo.get('ativos')}")
    assert sem_codigo.get("em_extincao") == POLOS_SEM_CODIGO_EM_EXTINCAO


def test_fluxo():
    ufs = _ler("nacional.json")["ufs"]
    assert _soma(ufs, "matriculas") == MATRICULAS, (
        f"matrículas: esperado {MATRICULAS}, veio {_soma(ufs, 'matriculas')}")
    assert _soma(ufs, "concluintes") == CONCLUINTES


def test_concentracao_cobre_toda_a_capacidade_ativa():
    """
    O HHI de mantenedora tem de ser calculado sobre a capacidade ATIVA inteira,
    não só sobre o presencial.

    ESTE TESTE MUDOU DE FORMA, E O MOTIVO IMPORTA.

    Até o Censo 2024 ele exigia o HHI de São Paulo acima de um limiar, porque a
    EaD estava incluída e a concentração morava nos grandes grupos de EaD: só
    sobre o presencial o número despencava. O limiar era a prova de que a EaD
    entrava na conta.

    Com a mudança de formato de oferta em 2025, o limiar perdeu o referente —
    um número escolhido para passar, sem nada atrás. A pergunta que continua
    respondível é ESTRUTURAL: a concentração cobre a mesma base que a
    capacidade publicada? Então é ela que o teste faz.
    """
    ufs = _ler("nacional.json")["ufs"]
    problemas = []
    for sigla, d in ufs.items():
        tem_capacidade = (d.get("vagas_total") or 0) > 0
        if tem_capacidade and d.get("HHI_mantenedora") is None:
            problemas.append(f"{sigla}: tem capacidade ativa e HHI nulo")
        if not tem_capacidade and d.get("HHI_mantenedora") is not None:
            problemas.append(
                f"{sigla}: HHI {d['HHI_mantenedora']} sem capacidade ativa")
        if d.get("HHI") is not None and not 0 <= d["HHI"] <= 1:
            problemas.append(f"{sigla}: HHI fora de 0..1")
    assert not problemas, "\n  - ".join(problemas)

    # A base do HHI inclui o que não é presencial. Numa UF onde essa parte é a
    # maior da oferta, um HHI calculado só sobre o presencial seria o HHI de
    # outra coisa.
    nao_presencial = [s for s, d in ufs.items()
                      if (d.get("vagas_semipresencial") or 0)
                      + (d.get("vagas_ead") or 0) > 0]
    assert nao_presencial, (
        "nenhuma UF com oferta não presencial: se a categoria sumiu da edição, "
        "este teste e as âncoras do semipresencial precisam sair, não ser "
        "afrouxados")
    for sigla in nao_presencial:
        assert ufs[sigla]["HHI_mantenedora"] is not None, (
            f"{sigla} tem oferta não presencial e HHI nulo — sinal de que a "
            "concentração foi calculada só sobre o presencial")


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

def test_o_esquema_declarado_bate_com_a_edicao():
    """
    As invariantes do esquema normalizado só rodam nele. Esta garante que elas
    vão ACORDAR.

    Sem ela, bastaria `_esquema()` ler a chave errada para os testes seguintes
    ficarem inertes para sempre — passando sem olhar nada, inclusive depois de
    a edição nova entrar. Teste que se desliga sozinho e continua verde é pior
    que teste ausente, porque dá a impressão de cobertura.

    A regra é simples e verificável: o INEP normalizou os microdados a partir
    de 2025. Edição de 2025 em diante tem de declarar `normalizado`; anterior,
    `unico`.
    """
    esperado = "normalizado" if CENSO >= 2025 else "unico"
    assert _esquema() == esperado, (
        f"o Censo publicado é {CENSO} e a proveniência declara esquema "
        f"{_esquema()!r}; esperado {esperado!r}. Se o INEP mudou de novo, "
        "ajuste a regra aqui — mas confira antes que as invariantes do "
        "esquema continuam rodando.")


def test_so_a_oferta_sem_endereco_e_atribuida_pela_sede():
    """
    Atribuir pela mantenedora é legítimo para um caso e proibido para o outro.

    Até 2024 a coluna `TP_DIMENSAO` separava dois tipos de ausência:

      · a SEDE de curso a distância vinha sem UF POR NATUREZA, e era atribuída
        pela mantenedora. Curso a distância não tem endereço; a sede é o lugar
        que a fonte conhece.
      · a camada "sem localização" era a fonte dizendo que NÃO SABE onde
        aquilo está. Essa não se atribui: atribuir faz o total fechar
        inventando dado.

    Sem a coluna de dimensão, o que separa os dois é o FORMATO DE OFERTA: um
    curso presencial tem endereço por definição. Presencial sem localização é
    informação faltando, não oferta deslocalizada.

    Então a proibição continua de pé, com o alvo certo: nenhuma atribuição pela
    sede pode vir de curso presencial.
    """
    if _esquema() != "normalizado":
        return
    cursos = _fatia_de_curso()
    if cursos is None:
        return

    sem_uf = [l for l in cursos if not (l.get("SG_UF_LO") or "").strip()]
    presenciais = [l for l in sem_uf
                   if (l.get("TP_MODALIDADE_ENSINO") or "").strip() == "1"]
    meta = _ler("bruto.json")["metadados"]
    por_ies = (meta.get("sem_localizacao") or {}).get(
        "atribuidas_pela_sede_da_ies") or {}

    assert por_ies.get("linhas", 0) == len(sem_uf) - len(presenciais), (
        f"{len(sem_uf)} cursos sem local de oferta, {len(presenciais)} deles "
        f"presenciais, e {por_ies.get('linhas')} atribuições pela sede. Os "
        "presenciais não podem estar entre as atribuídas.")
    assert por_ies.get("linhas") == ATRIBUIDAS_PELA_SEDE_LINHAS, (
        f"atribuições pela sede: esperado {ATRIBUIDAS_PELA_SEDE_LINHAS}, veio "
        f"{por_ies.get('linhas')}")
    assert por_ies.get("vagas") == ATRIBUIDAS_PELA_SEDE_VAGAS, (
        f"vagas atribuídas pela sede: esperado {ATRIBUIDAS_PELA_SEDE_VAGAS}, "
        f"veio {por_ies.get('vagas')}")

    if presenciais:
        sobraram = (meta.get("sem_localizacao") or {}).get("linhas", 0)
        assert sobraram >= len(presenciais), (
            f"{len(presenciais)} cursos presenciais sem localização "
            f"desapareceram: só {sobraram} linhas ficaram em sem_localizacao. "
            "Presencial sem endereço é informação faltando, e tem de aparecer "
            "como tal em vez de ser posto numa UF.")


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
    Totais conhecidos do CNES 202609, como teste de regressão.

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
    entra como rede pública: medido na 202609, isso leva a cobertura de 2.150
    para 2.266 municípios e os estabelecimentos de 5.568 para 9.354 — 40% do
    que seria
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
