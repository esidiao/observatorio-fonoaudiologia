"""
site/catalogo.py
Catálogo único dos indicadores: fonte de verdade para formatação, cor,
glossário e exportação.

POR QUE UM CATÁLOGO SÓ
-----------------------
No observatório de Farmácia o glossário mora num arquivo JS e os metadados de
formatação moram em outro. Nada garante que uma entrada exista nos dois, e
quando não existe o valor cai num fallback de três casas decimais: uma
contagem de 19 municípios aparece como `19,000` — dezenove mil, em pt-BR, na
página de uma UF.

Aqui as duas coisas são a MESMA estrutura, em Python, e o build gera o JS a
partir dela. Não é possível registrar um indicador no glossário e esquecer da
formatação, porque são o mesmo registro. `tests/test_catalogo.py` fecha a outra
ponta: todo campo publicado em data/nacional.json precisa estar aqui.

CAMPOS
------
  key        nome do campo no JSON publicado
  sigla      rótulo curto (tabelas, eixos)
  nome       nome por extenso (glossário, tooltips)
  cat        categoria para agrupar no glossário
  oque       explicação em linguagem corrente, sem jargão
  escala     texto da unidade ("0 a 1", "vagas/ano", "municípios")
  dir        'maior' | 'menor' | 'contextual'  — direção normativa
  fonte      origem do dado
  dec        casas decimais na formatação pt-BR
  min, max   limites para a escala de cor; None = sem escala de cor
  mult       fator aplicado antes de formatar (ex.: fração -> percentual)
  aliases    termos que a busca do glossário também aceita
"""

DIRECOES = {"maior", "menor", "contextual"}


def _i(key, sigla, nome, cat, oque, escala, direcao, fonte,
       dec=0, min=None, max=None, mult=None, aliases=()):
    return {
        "key": key, "sigla": sigla, "nome": nome, "cat": cat, "oque": oque,
        "escala": escala, "dir": direcao, "fonte": fonte, "dec": dec,
        "min": min, "max": max, "mult": mult, "aliases": list(aliases),
    }


INDICADORES = [

    # ---------------------------------------------------------------- índices
    _i("ICT", "ICT", "Índice de Concentração Territorial", "Território",
       "Mede o quanto a oferta de vagas se concentra em poucos municípios. "
       "Metade do índice olha a fatia de vagas na capital; a outra metade, a "
       "fração de municípios sem nenhuma oferta. Perto de 1, a formação está "
       "concentrada e o interior fica descoberto.",
       "0 a 1", "menor", "Censo INEP", dec=3, min=0, max=1, aliases=["ict"]),

    _i("E", "E", "Equidade Territorial", "Território",
       "Complemento do ICT (E = 1 − ICT). Quanto maior, mais distribuída pelo "
       "território está a oferta.",
       "0 a 1", "maior", "Calculado", dec=3, min=0, max=1,
       aliases=["equidade"]),

    _i("IAF", "IAF", "Índice de Adequação Formativa", "Qualidade",
       "Combina num só número de 0 a 100 três coisas: a qualidade dos cursos "
       "avaliados (CPC), a fatia das vagas que está em curso avaliado, e a "
       "equidade territorial. Fica em branco quando falta qualquer uma das "
       "três — um IAF calculado sobre dois terços dos componentes não é "
       "comparável com um calculado sobre três.",
       "0 a 100", "maior", "CPC INEP + Censo INEP", dec=1, min=0, max=100,
       aliases=["iaf", "adequação formativa"]),

    _i("ICAF", "ICAF", "Cobertura Assistencial — força de trabalho", "Cobertura",
       "Fração dos municípios do estado com ao menos um fonoaudiólogo "
       "vinculado ao SUS. Responde à pergunta de onde existe profissional "
       "capaz de absorver quem se forma.",
       "0 a 1", "maior", "CNES/DATASUS", dec=3, min=0, max=1,
       aliases=["icaf", "cobertura", "fonoaudiólogos por município"]),

    _i("ICRE", "ICRE", "Cobertura de Rede Especializada", "Cobertura",
       "Fração dos municípios do estado com estabelecimento que declara "
       "serviço fonoaudiológico ou de atenção à saúde auditiva no CNES. "
       "NÃO é o CER: a habilitação de Centro Especializado em Reabilitação "
       "não é publicada pelo CNES, e não foi substituída por aproximação.",
       "0 a 1", "maior", "CNES/DATASUS", dec=3, min=0, max=1,
       aliases=["icre", "rede especializada", "cer"]),

    # ------------------------------------------------------------ capacidade
    _i("vagas_total", "Vagas totais", "Capacidade total (presencial + EaD)",
       "Capacidade",
       "Todas as vagas anuais de Fonoaudiologia: presenciais mais EaD. As "
       "vagas EaD são atribuídas ao estado-sede da mantenedora, que é onde o "
       "Censo as registra.",
       "vagas/ano", "contextual", "Censo INEP", dec=0,
       aliases=["vagas totais", "capacidade"]),

    _i("vagas_presencial", "Vagas presenciais", "Vagas em cursos presenciais",
       "Capacidade",
       "Vagas anuais em cursos presenciais em funcionamento. Não inclui EaD.",
       "vagas/ano", "contextual", "Censo INEP", dec=0,
       aliases=["vagas presenciais"]),

    _i("vagas_ead", "Vagas EaD", "Vagas a distância", "Capacidade",
       "Vagas anuais em cursos a distância, registradas na sede da "
       "mantenedora. Um único curso EaD atende dezenas de municípios por meio "
       "de polos.",
       "vagas/ano", "contextual", "Censo INEP", dec=0, aliases=["vagas ead"]),

    _i("vagas_capital", "Vagas na capital", "Vagas presenciais na capital",
       "Capacidade",
       "Vagas presenciais oferecidas na capital do estado. É metade do cálculo "
       "do ICT.",
       "vagas/ano", "contextual", "Censo INEP", dec=0),

    _i("pct_ead", "% EaD", "Participação da EaD na capacidade", "Capacidade",
       "Percentual das vagas que são a distância. Valores muito altos acendem "
       "alerta sobre a oferta de prática clínica supervisionada, que é "
       "essencial à Fonoaudiologia.",
       "0 a 100%", "menor", "Censo INEP", dec=1, min=0, max=100,
       aliases=["% ead"]),

    _i("vagas_por_100k", "Vagas / 100 mil hab.", "Densidade de vagas",
       "Capacidade",
       "Vagas totais por 100 mil habitantes. Normaliza a capacidade pela "
       "população e revela excesso ou escassez que o número absoluto esconde.",
       "vagas/100 mil", "contextual", "Censo INEP + IBGE", dec=1,
       aliases=["100 mil", "densidade"]),

    _i("populacao", "População", "População residente estimada", "Capacidade",
       "Estimativa populacional do IBGE para o estado, usada como base dos "
       "indicadores per capita.",
       "habitantes", "contextual", "IBGE", dec=0, aliases=["população"]),

    _i("n_cursos_presencial", "Cursos presenciais", "Cursos presenciais",
       "Capacidade", "Número de cursos presenciais em funcionamento.",
       "cursos", "contextual", "Censo INEP", dec=0),

    _i("n_cursos_ead", "Cursos EaD", "Cursos a distância (sede)", "Capacidade",
       "Número de cursos EaD com sede no estado.",
       "cursos", "contextual", "Censo INEP", dec=0),

    _i("n_ies", "IES", "Instituições de ensino superior", "Capacidade",
       "Instituições distintas que ofertam o curso no estado, somando "
       "presencial e EaD.",
       "instituições", "contextual", "Censo INEP", dec=0,
       aliases=["instituições"]),

    _i("n_mantenedoras", "Mantenedoras", "Mantenedoras distintas", "Capacidade",
       "Grupos mantenedores distintos. Uma mantenedora pode operar várias "
       "instituições — é por isso que a concentração medida por mantenedora "
       "costuma ser bem maior que a medida por instituição.",
       "mantenedoras", "contextual", "Censo INEP", dec=0),

    # --------------------------------------------------------- concentração
    _i("HHI", "HHI (IES)", "Concentração por instituição", "Concentração",
       "Índice Herfindahl-Hirschman das fatias de vagas por instituição. "
       "Perto de 1, quase toda a capacidade está numa instituição só.",
       "0 a 1", "menor", "Censo INEP", dec=4, min=0, max=1, aliases=["hhi"]),

    _i("HHI_mantenedora", "HHI (mantenedora)", "Concentração por mantenedora",
       "Concentração",
       "O mesmo índice, agrupando por grupo mantenedor em vez de instituição. "
       "Calculado sobre a capacidade total, incluindo EaD — só assim os "
       "grandes grupos aparecem.",
       "0 a 1", "menor", "Censo INEP", dec=4, min=0, max=1,
       aliases=["hhi mantenedora", "concentração"]),

    _i("CR2", "CR2", "Participação das 2 maiores", "Concentração",
       "Fatia das vagas concentrada nas duas maiores instituições.",
       "0 a 100%", "menor", "Censo INEP", dec=1, min=0, max=1, mult=100,
       aliases=["cr2"]),

    _i("CR10", "CR10", "Participação das 10 maiores", "Concentração",
       "Fatia das vagas concentrada nas dez maiores instituições.",
       "0 a 100%", "menor", "Censo INEP", dec=1, min=0, max=1, mult=100,
       aliases=["cr10"]),

    # ------------------------------------------------------------ território
    _i("municipios_total", "Municípios do estado", "Municípios do estado",
       "Território",
       "Total de municípios do estado, conforme a base de localidades do "
       "IBGE. São 5.571 no país desde 2025, não 5.570.",
       "municípios", "contextual", "IBGE", dec=0),

    _i("municipios_oferta", "Municípios com curso",
       "Municípios com oferta presencial", "Território",
       "Municípios onde existe ao menos um curso presencial.",
       "municípios", "maior", "Censo INEP", dec=0,
       aliases=["municípios com oferta"]),

    _i("municipios_deserto", "Municípios sem curso",
       "Municípios sem oferta presencial", "Território",
       "Municípios do estado sem nenhum curso presencial de Fonoaudiologia.",
       "municípios", "menor", "Censo INEP", dec=0, aliases=["deserto"]),

    _i("cobertura_municipal", "Cobertura municipal",
       "Fração de municípios com curso", "Território",
       "Municípios com oferta presencial divididos pelo total de municípios "
       "do estado.",
       "0 a 1", "maior", "Censo INEP + IBGE", dec=4, min=0, max=1),

    _i("ead_polos_registros", "Polos EaD", "Polos EaD (registros)",
       "Território",
       "Registros de polo de apoio presencial de cursos EaD no estado. Um "
       "município pode ter mais de um polo.",
       "registros", "contextual", "Censo INEP", dec=0, aliases=["polos"]),

    _i("ead_polos_municipios", "Municípios com polo",
       "Municípios com polo EaD", "Território",
       "Municípios distintos que abrigam ao menos um polo EaD.",
       "municípios", "contextual", "Censo INEP", dec=0),

    _i("municipios_so_ead", "Municípios só EaD",
       "Municípios atendidos apenas por EaD", "Território",
       "Municípios que têm polo EaD e nenhum curso presencial. Mede até onde "
       "a EaD chega em território que a oferta presencial não alcança.",
       "municípios", "contextual", "Censo INEP", dec=0),

    # ------------------------------------------------------------- cobertura
    _i("municipios_com_fonoaudiologo", "Municípios com fonoaudiólogo",
       "Municípios com fonoaudiólogo no SUS", "Cobertura",
       "Municípios com ao menos um profissional de CBO 2238 vinculado ao SUS "
       "no CNES.",
       "municípios", "maior", "CNES/DATASUS", dec=0),

    _i("municipios_com_servico_fono", "Municípios com serviço",
       "Municípios com serviço fonoaudiológico", "Cobertura",
       "Municípios com estabelecimento que declara serviço de atenção à saúde "
       "auditiva ou reabilitação/atenção fonoaudiológica no CNES.",
       "municípios", "maior", "CNES/DATASUS", dec=0),

    _i("fonoaudiologos_sus", "Fonoaudiólogos no SUS",
       "Fonoaudiólogos vinculados ao SUS", "Cobertura",
       "Profissionais distintos, não vínculos: o mesmo fonoaudiólogo com três "
       "vínculos conta uma vez.",
       "profissionais", "maior", "CNES/DATASUS", dec=0),

    _i("fonoaudiologos_por_100k", "Fonoaudiólogos / 100 mil hab.",
       "Densidade de fonoaudiólogos no SUS", "Cobertura",
       "Fonoaudiólogos vinculados ao SUS por 100 mil habitantes.",
       "profissionais/100 mil", "maior", "CNES/DATASUS + IBGE", dec=1),

    # -------------------------------------------------------------- qualidade
    _i("CPC", "CPC (faixa)", "Conceito Preliminar de Curso — faixa",
       "Qualidade",
       "Média das faixas do CPC dos cursos do estado, ponderada pelo número "
       "de concluintes que participaram do ENADE. É deste valor que sai o "
       "componente de qualidade do IAF.",
       "1 a 5", "maior", "CPC INEP", dec=3, min=1, max=5, aliases=["cpc"]),

    _i("CPC_cont", "CPC contínuo", "Conceito Preliminar de Curso — contínuo",
       "Qualidade",
       "Média ponderada do CPC contínuo. Três casas decimais: com duas, "
       "nenhuma UF reproduz o valor publicado.",
       "0 a 5", "maior", "CPC INEP", dec=3, min=0, max=5),

    _i("ENADE_cont", "ENADE", "Conceito ENADE contínuo", "Qualidade",
       "Média ponderada do conceito ENADE contínuo dos cursos avaliados.",
       "0 a 5", "maior", "ENADE INEP", dec=3, min=0, max=5,
       aliases=["enade"]),

    _i("IDD", "IDD", "Indicador de Diferença entre Desempenhos", "Qualidade",
       "Mede quanto o curso agrega além do que a nota de ingresso do aluno já "
       "previa. Fica em branco para cursos sem nota de ENEM suficiente — 6 dos "
       "74 cursos avaliados no ciclo 2023.",
       "0 a 5", "maior", "CPC INEP", dec=3, min=0, max=5, aliases=["idd"]),

    _i("n_cursos_avaliados", "Cursos avaliados", "Cursos no ciclo do CPC",
       "Qualidade",
       "Cursos do estado avaliados no ciclo do CPC. Um estado com oferta e "
       "nenhum curso avaliado aparece sem dados de qualidade — é o caso de "
       "Tocantins no ciclo 2023.",
       "cursos", "contextual", "CPC INEP", dec=0),

    _i("vagas_avaliadas", "Vagas avaliadas", "Vagas em cursos avaliados",
       "Qualidade",
       "Vagas dos cursos que passaram pelo ciclo do CPC. É o componente de "
       "cobertura da avaliação dentro do IAF.",
       "vagas/ano", "maior", "CPC INEP + Censo INEP", dec=0),

    _i("pct_doc_mestres", "% Mestres", "Docentes com mestrado ou mais",
       "Qualidade",
       "Percentual do corpo docente com titulação de mestre ou superior.",
       "0 a 100%", "maior", "CPC INEP", dec=1, min=0, max=100),

    _i("pct_doc_doutores", "% Doutores", "Docentes com doutorado", "Qualidade",
       "Percentual do corpo docente com doutorado.",
       "0 a 100%", "maior", "CPC INEP", dec=1, min=0, max=100),

    _i("pct_doc_regime_integral", "% Regime integral",
       "Docentes em regime integral ou parcial", "Qualidade",
       "Percentual do corpo docente em regime de trabalho integral ou parcial "
       "— não horista.",
       "0 a 100%", "maior", "CPC INEP", dec=1, min=0, max=100),

    _i("dim_didatico_pedagogica", "Org. didático-pedagógica",
       "Organização didático-pedagógica", "Qualidade",
       "Dimensão avaliada pelos próprios estudantes no questionário do ENADE.",
       "0 a 6", "maior", "CPC INEP", dec=3, min=0, max=6),

    _i("dim_infraestrutura", "Infraestrutura",
       "Infraestrutura e instalações físicas", "Qualidade",
       "Dimensão avaliada pelos próprios estudantes no questionário do ENADE.",
       "0 a 6", "maior", "CPC INEP", dec=3, min=0, max=6),

    _i("dim_oportunidade_formacao", "Oport. de ampliação",
       "Oportunidade de ampliação da formação", "Qualidade",
       "Dimensão avaliada pelos próprios estudantes no questionário do ENADE.",
       "0 a 6", "maior", "CPC INEP", dec=3, min=0, max=6),

    # ------------------------------------------------------------------ fluxo
    _i("matriculas", "Matrículas", "Matrículas totais", "Fluxo",
       "Alunos matriculados, somando presencial e polos EaD.",
       "alunos", "contextual", "Censo INEP", dec=0, aliases=["matrículas"]),

    _i("matriculas_presencial", "Matrículas presenciais",
       "Matrículas em cursos presenciais", "Fluxo",
       "Alunos matriculados em cursos presenciais.",
       "alunos", "contextual", "Censo INEP", dec=0),

    _i("matriculas_ead", "Matrículas EaD", "Matrículas em polos EaD", "Fluxo",
       "Alunos matriculados registrados em polos EaD do estado. As linhas de "
       "polo carregam as matrículas; as vagas ficam na linha de sede.",
       "alunos", "contextual", "Censo INEP", dec=0),

    _i("ingressos", "Ingressos", "Ingressantes no ano", "Fluxo",
       "Alunos que ingressaram no curso no ano do Censo.",
       "alunos", "contextual", "Censo INEP", dec=0),

    _i("concluintes", "Concluintes", "Concluintes no ano", "Fluxo",
       "Alunos que concluíram o curso no ano do Censo.",
       "alunos", "contextual", "Censo INEP", dec=0),

    _i("taxa_conclusao", "Taxa de conclusão", "Concluintes sobre matrículas",
       "Fluxo",
       "Concluintes divididos por matriculados no mesmo ano. É um retrato "
       "pontual, não o acompanhamento de uma turma ao longo do tempo.",
       "0 a 100%", "maior", "Censo INEP", dec=1, min=0, max=25,
       aliases=["conclusão"]),

    # ----------------------------------------------------------------- perfil
    _i("pct_mulheres", "% Mulheres", "Mulheres entre os matriculados",
       "Perfil", "Percentual de mulheres entre os alunos matriculados.",
       "0 a 100%", "contextual", "Censo INEP", dec=1, min=0, max=100),

    _i("pct_ppi", "% Pretos, pardos e indígenas",
       "Pretos, pardos e indígenas entre os matriculados", "Perfil",
       "Percentual de alunos autodeclarados pretos, pardos ou indígenas. "
       "Leia junto com a cor não declarada: onde esta é alta, o percentual "
       "está subestimado.",
       "0 a 100%", "contextual", "Censo INEP", dec=1, min=0, max=100,
       aliases=["ppi"]),

    _i("pct_cor_nao_declarada", "% Cor não declarada",
       "Alunos sem declaração de cor ou raça", "Perfil",
       "Percentual de matriculados sem cor ou raça declarada. É a margem de "
       "incerteza do indicador de PPI, não um grupo à parte.",
       "0 a 100%", "contextual", "Censo INEP", dec=1, min=0, max=100),

    _i("pct_noturno", "% Noturno", "Matrículas em curso noturno", "Perfil",
       "Percentual de matriculados em cursos noturnos.",
       "0 a 100%", "contextual", "Censo INEP", dec=1, min=0, max=100),

    _i("pct_rede_publica", "% Rede pública", "Matrículas na rede pública",
       "Perfil",
       "Percentual de matriculados em instituições públicas.",
       "0 a 100%", "contextual", "Censo INEP", dec=1, min=0, max=100),

    _i("pct_financiamento", "% Com financiamento",
       "Matrículas com financiamento estudantil", "Perfil",
       "Percentual de matriculados com algum financiamento — FIES, ProUni ou "
       "outros, reembolsáveis ou não.",
       "0 a 100%", "contextual", "Censo INEP", dec=1, min=0, max=100,
       aliases=["fies", "prouni"]),

    _i("pct_apoio_social", "% Com apoio social",
       "Matrículas com apoio social", "Perfil",
       "Percentual de matriculados que recebem alguma modalidade de apoio "
       "social — moradia, alimentação, transporte, material.",
       "0 a 100%", "contextual", "Censo INEP", dec=1, min=0, max=100),

    # ------------------------------------------------- só no nível municipal
    # Existem apenas nas páginas de município. Precisam de entrada igual às
    # demais: a formatação vem do catálogo, e sem registro `polos_ead` cairia
    # no fallback de três casas — "2 polos" viraria "2,000".
    _i("cursos_presencial", "Cursos presenciais", "Cursos presenciais no município",
       "Capacidade", "Cursos presenciais de Fonoaudiologia no município.",
       "cursos", "contextual", "Censo INEP", dec=0),

    _i("polos_ead", "Polos EaD", "Polos de EaD no município", "Território",
       "Polos de apoio presencial de cursos a distância registrados no "
       "município. É por eles que a EaD alcança território sem curso "
       "presencial.",
       "registros", "contextual", "Censo INEP", dec=0),

    _i("estabelecimentos_servico_fono", "Estabelecimentos com serviço",
       "Estabelecimentos com serviço fonoaudiológico", "Cobertura",
       "Estabelecimentos do município que declaram no CNES serviço de atenção "
       "à saúde auditiva ou reabilitação/atenção fonoaudiológica.",
       "registros", "maior", "CNES/DATASUS", dec=0),

    _i("pct_reserva_vaga", "% Reserva de vagas",
       "Matrículas por reserva de vagas", "Perfil",
       "Percentual de matriculados que ingressaram por alguma política de "
       "reserva de vagas.",
       "0 a 100%", "contextual", "Censo INEP", dec=1, min=0, max=100,
       aliases=["cotas"]),
]

POR_CHAVE = {i["key"]: i for i in INDICADORES}

CATEGORIAS = ["Território", "Capacidade", "Concentração", "Cobertura",
              "Qualidade", "Fluxo", "Perfil"]


# --------------------------------------------------------------------------- #
# Campos publicados que NÃO são indicadores: identificam ou descrevem, não
# medem. Ficam declarados para que o teste de catálogo saiba distinguir "campo
# sem entrada no catálogo" de "campo que não precisa de entrada".
# --------------------------------------------------------------------------- #
CAMPOS_NAO_INDICADORES = {
    # identificação
    "uf", "regiao", "capital", "nome", "codigo", "slug",
    # sinalizadores de estado, lidos pelos templates para escolher o texto
    "tem_oferta_presencial", "tem_avaliacao", "tem_curso_presencial",
    # detalhamentos auxiliares, não exibidos como medida isolada
    "n_ies_presencial", "n_ies_ead", "n_com_cpc", "n_com_idd",
    "concluintes_participantes", "cursos_sem_vagas_no_censo",
    "servicos_fono", "fonoaudiologos_total",
}


def validar():
    """
    Confere a coerência interna do catálogo. Chamado pelo build e pelos testes.

    Devolve a lista de problemas; vazia significa catálogo íntegro.
    """
    problemas = []
    vistos = set()
    for ind in INDICADORES:
        key = ind["key"]
        if key in vistos:
            problemas.append(f"{key}: chave duplicada")
        vistos.add(key)
        if ind["dir"] not in DIRECOES:
            problemas.append(f"{key}: direção {ind['dir']!r} inválida")
        if ind["cat"] not in CATEGORIAS:
            problemas.append(f"{key}: categoria {ind['cat']!r} desconhecida")
        if not ind["oque"].strip():
            problemas.append(f"{key}: sem explicação")
        if (ind["min"] is None) != (ind["max"] is None):
            problemas.append(f"{key}: min e max precisam vir juntos ou nenhum")
        # Contagem com casa decimal é o defeito que este catálogo existe para
        # impedir: 19 municípios formatados com 3 casas viram "19,000".
        if ind["escala"] in ("municípios", "cursos", "instituições", "alunos",
                             "vagas/ano", "habitantes", "registros",
                             "profissionais", "mantenedoras") and ind["dec"] != 0:
            problemas.append(
                f"{key}: escala {ind['escala']!r} é contagem e exige dec=0, "
                f"tem dec={ind['dec']}")
    return problemas


def para_js():
    """Serializa o catálogo para o JS consumido pelo site."""
    import json

    meta = {i["key"]: {"label": i["sigla"], "nome": i["nome"], "dec": i["dec"],
                       "min": i["min"], "max": i["max"],
                       "mult": i["mult"], "dir": i["dir"]}
            for i in INDICADORES}
    glossario = [{"key": i["key"], "sigla": i["sigla"], "nome": i["nome"],
                  "cat": i["cat"], "oque": i["oque"], "escala": i["escala"],
                  "dir": i["dir"], "fonte": i["fonte"],
                  "aliases": i["aliases"]}
                 for i in INDICADORES]
    return (
        "/* GERADO por site/catalogo.py — não editar à mão.\n"
        "   Metadados de formatação e glossário saem da MESMA estrutura, então\n"
        "   é impossível um indicador existir num e faltar no outro. */\n"
        f"const INDICADOR_META = {json.dumps(meta, ensure_ascii=False, indent=2)};\n\n"
        f"const GLOSSARIO = {json.dumps(glossario, ensure_ascii=False, indent=2)};\n\n"
        f"const CATEGORIAS = {json.dumps(CATEGORIAS, ensure_ascii=False)};\n"
    )


if __name__ == "__main__":
    import sys

    problemas = validar()
    if problemas:
        print("[CATALOGO] FALHOU:")
        for p in problemas:
            print("  -", p)
        sys.exit(1)
    print(f"[CATALOGO] OK — {len(INDICADORES)} indicadores em "
          f"{len(CATEGORIAS)} categorias.")
