"""
etl/extrair_cnes.py
Extrai do CNES as duas metades da cobertura assistencial fonoaudiológica,
lendo a base mensal do DATASUS por FTP sem baixar os 700 MB do ZIP.

Uso:
    python etl/extrair_cnes.py                      # competência mais recente
    python etl/extrair_cnes.py --competencia 202607
    python etl/extrair_cnes.py --listar             # competências disponíveis
    python etl/extrair_cnes.py --rebaixar           # ignora o cache e rebaixa

Saída: data/cobertura_cnes.json — por município.

AS DUAS METADES
---------------
  · força de trabalho — municípios com ao menos um vínculo de fonoaudiólogo
    (CBO 2238xx) em `tbCargaHorariaSus`;
  · rede especializada — municípios com estabelecimento que declara serviço
    fonoaudiológico ou auditivo em `rlEstabServClass`.

Publicadas separadamente porque fundi-las exigiria arbitrar um peso entre "tem
profissional" e "tem serviço", e peso arbitrário é estimativa disfarçada.

O CBO É POR PREFIXO EXATO DE FAMÍLIA, NÃO POR NOME
---------------------------------------------------
A família 2238 tem oito ocupações (2238-10 a 2238-45), todas marcadas
TP_CBO_SAUDE = 'S'. Casar por texto capturaria `234430 PROFESSOR DE
FONOAUDIOLOGIA`, que é docência, não assistência — o mesmo erro que casar
rótulo CINE por substring capturaria `Produção fonográfica`.

DUAS FASES, COM CACHE ENTRE ELAS
---------------------------------
Baixar e filtrar leva perto de uma hora (236 MB por um FTP que derruba a maior
parte das conexões). Agregar leva segundos. Misturar as duas coisas num passo
só significa pagar a hora de novo a cada ajuste de fórmula, o que na prática
desestimula ajustar a fórmula. As fatias filtradas ficam em
`etl/dados/cnes_<competência>/`, fora do versionamento.

O QUE NÃO DÁ PARA MEDIR AQUI
-----------------------------
A habilitação de Centro Especializado em Reabilitação (CER) NÃO é publicada
nesta base. Os códigos existem em `tbSubGruposHabilitacao` (2208–2211 para as
modalidades do CER, 8223–8225 para CER II/III/IV), mas nenhuma tabela-fato os
relaciona a estabelecimento ou município: `tbIncentivos` traz apenas cinco
códigos, todos de incentivo financeiro, e nenhum deles de reabilitação. Medir
outra coisa e chamar de CER seria inventar o indicador. Ele fica ausente.
"""
import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from rede import ZipRemotoFTP

REPO = Path(__file__).parent.parent
DADOS = REPO / "etl" / "dados"
DATA = REPO / "data"

HOST = "ftp.datasus.gov.br"
DIRETORIO = "/cnes"
PADRAO = "BASE_DE_DADOS_CNES_{competencia}.ZIP"

# Blocos grandes reduzem o número de conexões FTP, e cada conexão é uma aposta:
# o DATASUS derruba boa parte das conexões que usam REST. Blocos pequenos
# multiplicam as apostas; blocos grandes desperdiçam mais a cada queda.
BLOCO = 16 << 20

CBO_PREFIXO = "2238"           # família Fonoaudiólogo (2238-10 .. 2238-45)

# Serviço 107 inteiro é atenção à saúde auditiva. Do serviço 135 (reabilitação),
# só as duas classificações fonoaudiológicas — as demais são física, visual,
# intelectual, ortopédica.
SERVICO_AUDITIVO = "107"
SERVICO_REABILITACAO = "135"
CLASSIF_REABILITACAO_FONO = {"005", "010"}   # reabilitação auditiva; atenção fonoaudiológica

UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

# Fração de registros cujo CO_UNIDADE não existe em NENHUM estabelecimento do
# cadastro. Diferente de "estabelecimento desabilitado", que é exclusão
# deliberada e pode ser alta sem indicar defeito nenhum.
LIMITE_SEM_CADASTRO = 0.02

csv.field_size_limit(1 << 24)


def _limpo(valor):
    return (valor or "").strip().strip('"')


def competencias_disponiveis():
    z = ZipRemotoFTP(HOST, DIRETORIO, PADRAO.format(competencia="000000"))
    nomes = z.listar_diretorio()
    return sorted(
        m.group(1) for m in
        (re.match(r"BASE_DE_DADOS_CNES_(\d{6})\.ZIP$", n, re.I) for n in nomes)
        if m
    )


def _membro(z, sufixo, competencia):
    alvo = z.localizar(sufixo.lower(), competencia)
    if not alvo:
        raise SystemExit(f"[ERRO] membro {sufixo}{competencia} não encontrado no ZIP")
    return alvo


# --------------------------------------------------------------------------- #
# FASE 1 — baixar e filtrar (cara, cacheada)
# --------------------------------------------------------------------------- #

def _escrever(caminho, cabecalho, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)


def baixar_fatias(competencia, cache, rebaixar=False):
    """Grava três fatias filtradas em `cache`. Só baixa o que faltar."""
    alvos = {
        "estabelecimentos": cache / "estabelecimentos.csv",
        "vinculos": cache / "vinculos_fono.csv",
        "servicos": cache / "servicos_fono.csv",
    }
    if not rebaixar and all(p.exists() for p in alvos.values()):
        print(f"[CNES] usando fatias já filtradas em {cache}")
        return alvos

    nome = PADRAO.format(competencia=competencia)
    z = ZipRemotoFTP(HOST, DIRETORIO, nome)
    print(f"[CNES] {nome} — {z.tamanho() / 1048576:.0f} MB no servidor; "
          "lendo só os membros necessários")

    if rebaixar or not alvos["estabelecimentos"].exists():
        alvo = _membro(z, "tbEstabelecimento", competencia)
        print(f"[CNES] lendo {alvo} ...")
        linhas, ativos, desabilitados = [], 0, 0
        with z.membro_arquivo(alvo, bloco=BLOCO) as f:
            for linha in csv.DictReader(f, delimiter=";"):
                unidade = _limpo(linha.get("CO_UNIDADE"))
                if not unidade:
                    continue
                # Guardamos TODOS, com uma coluna dizendo se está ativo. O
                # desabilitado precisa continuar conhecido: é ele que permite
                # distinguir "excluído de propósito" de "não encontrado", e
                # essa distinção é o que dá sentido à guarda de junção.
                ativo = "0" if _limpo(linha.get("CO_MOTIVO_DESAB")) else "1"
                if ativo == "1":
                    ativos += 1
                else:
                    desabilitados += 1
                linhas.append([unidade,
                               _limpo(linha.get("CO_MUNICIPIO_GESTOR")),
                               _limpo(linha.get("CO_ESTADO_GESTOR")),
                               ativo])
        _escrever(alvos["estabelecimentos"],
                  ["CO_UNIDADE", "CO_MUNICIPIO_GESTOR", "CO_ESTADO_GESTOR", "ATIVO"],
                  linhas)
        print(f"[CNES] {ativos} estabelecimentos ativos, "
              f"{desabilitados} desabilitados -> {alvos['estabelecimentos'].name}")

    if rebaixar or not alvos["vinculos"].exists():
        alvo = _membro(z, "tbCargaHorariaSus", competencia)
        print(f"[CNES] lendo {alvo} ... (834 MB descomprimidos; leitura em fluxo)")
        linhas, total = [], 0
        with z.membro_arquivo(alvo, bloco=BLOCO) as f:
            for linha in csv.DictReader(f, delimiter=";"):
                total += 1
                cbo = _limpo(linha.get("CO_CBO"))
                if not cbo.startswith(CBO_PREFIXO):
                    continue
                linhas.append([_limpo(linha.get("CO_UNIDADE")),
                               _limpo(linha.get("CO_PROFISSIONAL_SUS")),
                               cbo,
                               _limpo(linha.get("TP_SUS_NAO_SUS"))])
        _escrever(alvos["vinculos"],
                  ["CO_UNIDADE", "CO_PROFISSIONAL_SUS", "CO_CBO", "TP_SUS_NAO_SUS"],
                  linhas)
        print(f"[CNES] {total} vínculos lidos; {len(linhas)} de CBO "
              f"{CBO_PREFIXO}xx -> {alvos['vinculos'].name}")

    if rebaixar or not alvos["servicos"].exists():
        alvo = _membro(z, "rlEstabServClass", competencia)
        print(f"[CNES] lendo {alvo} ...")
        linhas, total = [], 0
        with z.membro_arquivo(alvo, bloco=BLOCO) as f:
            for linha in csv.DictReader(f, delimiter=";"):
                total += 1
                servico = _limpo(linha.get("CO_SERVICO"))
                classificacao = _limpo(linha.get("CO_CLASSIFICACAO"))
                if servico != SERVICO_AUDITIVO and not (
                        servico == SERVICO_REABILITACAO
                        and classificacao in CLASSIF_REABILITACAO_FONO):
                    continue
                linhas.append([_limpo(linha.get("CO_UNIDADE")), servico,
                               classificacao, _limpo(linha.get("ST_ATIVO_SN"))])
        _escrever(alvos["servicos"],
                  ["CO_UNIDADE", "CO_SERVICO", "CO_CLASSIFICACAO", "ST_ATIVO_SN"],
                  linhas)
        print(f"[CNES] {total} registros de serviço; {len(linhas)} "
              f"fonoaudiológicos/auditivos -> {alvos['servicos'].name}")

    return alvos


# --------------------------------------------------------------------------- #
# FASE 2 — agregar (barata, refaz à vontade)
# --------------------------------------------------------------------------- #

def carregar_estabelecimentos(caminho):
    """Devolve (ativos, conhecidos): dict CO_UNIDADE->(mun, uf) e set de todos."""
    ativos, conhecidos = {}, set()
    with open(caminho, encoding="utf-8") as f:
        for linha in csv.DictReader(f, delimiter=";"):
            unidade = linha["CO_UNIDADE"]
            conhecidos.add(unidade)
            if linha["ATIVO"] == "1" and linha["CO_MUNICIPIO_GESTOR"]:
                ativos[unidade] = (linha["CO_MUNICIPIO_GESTOR"],
                                   UF_POR_CODIGO.get(linha["CO_ESTADO_GESTOR"]))
    return ativos, conhecidos


def _classificar(unidade, ativos, conhecidos, contadores):
    """
    Resolve o município de um CO_UNIDADE e classifica o que não resolve.

    Três desfechos, e a diferença entre eles é o ponto:
      · resolveu                   -> devolve o município
      · existe, mas desabilitado   -> exclusão DELIBERADA, esperada, não é erro
      · não existe no cadastro     -> falha de junção; é isso que a guarda vigia
    """
    local = ativos.get(unidade)
    if local:
        return local[0]
    if unidade in conhecidos:
        contadores["desabilitado"] += 1
    else:
        contadores["sem_cadastro"] += 1
    return None


def forca_de_trabalho(caminho, ativos, conhecidos):
    """
    Conta PROFISSIONAIS DISTINTOS por município, não vínculos: o mesmo
    fonoaudiólogo pode ter três vínculos no mesmo município, e contá-lo três
    vezes transformaria precariedade de vínculo em abundância de força de
    trabalho.
    """
    sus, todos = defaultdict(set), defaultdict(set)
    contadores = defaultdict(int)
    total = 0
    with open(caminho, encoding="utf-8") as f:
        for i, linha in enumerate(csv.DictReader(f, delimiter=";")):
            total += 1
            municipio = _classificar(linha["CO_UNIDADE"], ativos, conhecidos,
                                     contadores)
            if not municipio:
                continue
            chave = linha["CO_PROFISSIONAL_SUS"] or f"{linha['CO_UNIDADE']}:{i}"
            todos[municipio].add(chave)
            if linha["TP_SUS_NAO_SUS"].upper() == "S":
                sus[municipio].add(chave)
    return sus, todos, {
        "vinculos_fonoaudiologia": total,
        "vinculos_em_estabelecimento_desabilitado": contadores["desabilitado"],
        "vinculos_sem_cadastro": contadores["sem_cadastro"],
    }


def rede_especializada(caminho, ativos, conhecidos):
    por_municipio = defaultdict(set)
    detalhe = defaultdict(lambda: defaultdict(set))
    contadores = defaultdict(int)
    total = inativos = 0
    with open(caminho, encoding="utf-8") as f:
        for linha in csv.DictReader(f, delimiter=";"):
            total += 1
            if linha["ST_ATIVO_SN"].upper() == "N":
                inativos += 1
                continue
            municipio = _classificar(linha["CO_UNIDADE"], ativos, conhecidos,
                                     contadores)
            if not municipio:
                continue
            rotulo = f"{linha['CO_SERVICO']}/{linha['CO_CLASSIFICACAO']}"
            por_municipio[municipio].add(linha["CO_UNIDADE"])
            detalhe[municipio][rotulo].add(linha["CO_UNIDADE"])
    return por_municipio, detalhe, {
        "servicos_fonoaudiologicos": total,
        "servicos_marcados_inativos": inativos,
        "servicos_em_estabelecimento_desabilitado": contadores["desabilitado"],
        "servicos_sem_cadastro": contadores["sem_cadastro"],
    }


def conferir_juncao(casos, limite=LIMITE_SEM_CADASTRO):
    """
    Aborta se registros demais apontarem para CO_UNIDADE que não existe.

    Vigia SÓ o desconhecido. A primeira versão desta guarda somava o
    desabilitado junto e reprovou uma execução correta com 10,6% — dos quais
    quase tudo era estabelecimento fechado que o indicador exclui de propósito.
    Uma guarda que dispara no comportamento certo é pior que nenhuma: ensina a
    ignorá-la.

    A junção é por CO_UNIDADE, e o formato do campo não é uniforme na base (há
    registros de 30 caracteres ao lado dos de 13). Se o layout mudar numa
    competência futura, a junção degrada em silêncio: o pipeline roda, os testes
    passam, e a cobertura despenca como se a rede tivesse encolhido. Um número
    que cai por defeito de junção é pior que um erro, porque parece notícia.
    """
    problemas = []
    for rotulo, total, desconhecidos, desabilitados in casos:
        if total <= 0:
            problemas.append(f"{rotulo}: nenhum registro lido")
            continue
        fracao = desconhecidos / total
        marca = "OK" if fracao <= limite else "FALHOU"
        print(f"[JUNCAO] {marca}  {rotulo}: {desconhecidos}/{total} "
              f"({fracao:.2%}) sem cadastro; "
              f"{desabilitados} ({desabilitados / total:.1%}) em "
              "estabelecimento desabilitado (exclusão esperada)")
        if fracao > limite:
            problemas.append(
                f"{rotulo}: {fracao:.2%} sem cadastro (limite {limite:.0%})")
    if problemas:
        raise SystemExit("[ERRO] junção CO_UNIDADE degradada:\n  - "
                         + "\n  - ".join(problemas))


def montar(competencia, sus, todos, rede, detalhe, diagnostico):
    municipios = {}
    for codigo in set(sus) | set(todos) | set(rede):
        municipios[codigo] = {
            "fonoaudiologos_sus": len(sus.get(codigo, ())) or None,
            "fonoaudiologos_total": len(todos.get(codigo, ())) or None,
            "estabelecimentos_servico_fono": len(rede.get(codigo, ())) or None,
            "servicos": sorted(detalhe.get(codigo, {})) or None,
        }
    arquivo = PADRAO.format(competencia=competencia)
    return {
        "metadados": {
            "fonte": "Cadastro Nacional de Estabelecimentos de Saúde (CNES/DATASUS)",
            "arquivo": arquivo,
            "url": f"ftp://{HOST}{DIRETORIO}/{arquivo}",
            "competencia": competencia,          # do ARQUIVO, não do calendário
            "cbo_familia": CBO_PREFIXO,
            "servicos_considerados": {
                "107": "Atenção à Saúde Auditiva (todas as classificações)",
                "135/005": "Reabilitação auditiva",
                "135/010": "Atenção fonoaudiológica",
            },
            "cer_indisponivel": (
                "A habilitação de Centro Especializado em Reabilitação não é "
                "publicada nesta base: os códigos existem em "
                "tbSubGruposHabilitacao (2208-2211, 8223-8225) mas nenhuma "
                "tabela-fato os liga a estabelecimento ou município. O "
                "indicador de CER não existe e não foi substituído por proxy."
            ),
            "extraido_em": date.today().isoformat(),
            "diagnostico": diagnostico,
        },
        "municipios": municipios,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--competencia", help="AAAAMM; default: a mais recente publicada")
    p.add_argument("--listar", action="store_true",
                   help="lista as competências disponíveis e sai")
    p.add_argument("--rebaixar", action="store_true",
                   help="ignora o cache de fatias e baixa tudo de novo")
    p.add_argument("--saida", default=str(DATA / "cobertura_cnes.json"))
    args = p.parse_args()

    if args.listar:
        comps = competencias_disponiveis()
        print(f"{len(comps)} competências: {comps[0]} .. {comps[-1]}")
        print("últimas 12:", ", ".join(comps[-12:]))
        return

    competencia = args.competencia
    if not competencia:
        comps = competencias_disponiveis()
        if not comps:
            raise SystemExit("[ERRO] nenhuma competência encontrada no FTP")
        competencia = comps[-1]
        print(f"[CNES] competência mais recente: {competencia}")

    cache = DADOS / f"cnes_{competencia}"
    fatias = baixar_fatias(competencia, cache, args.rebaixar)

    ativos, conhecidos = carregar_estabelecimentos(fatias["estabelecimentos"])
    print(f"[CNES] {len(ativos)} estabelecimentos ativos de "
          f"{len(conhecidos)} cadastrados")

    sus, todos, diag_ch = forca_de_trabalho(fatias["vinculos"], ativos, conhecidos)
    rede, detalhe, diag_sc = rede_especializada(fatias["servicos"], ativos, conhecidos)

    conferir_juncao([
        ("vínculos de fonoaudiólogo",
         diag_ch["vinculos_fonoaudiologia"],
         diag_ch["vinculos_sem_cadastro"],
         diag_ch["vinculos_em_estabelecimento_desabilitado"]),
        ("serviços fonoaudiológicos",
         diag_sc["servicos_fonoaudiologicos"],
         diag_sc["servicos_sem_cadastro"],
         diag_sc["servicos_em_estabelecimento_desabilitado"]),
    ])

    saida = montar(competencia, sus, todos, rede, detalhe, {**diag_ch, **diag_sc})
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(
        json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")

    n_forca = sum(1 for m in saida["municipios"].values() if m["fonoaudiologos_sus"])
    n_rede = sum(1 for m in saida["municipios"].values()
                 if m["estabelecimentos_servico_fono"])
    print(f"\n[CNES] municípios com fonoaudiólogo no SUS: {n_forca}")
    print(f"[CNES] municípios com serviço fonoaudiológico: {n_rede}")
    print(f"[CNES] -> {args.saida}")


if __name__ == "__main__":
    main()
