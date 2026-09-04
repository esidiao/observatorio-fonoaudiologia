"""
etl/registro_autoral.py
Registro de anterioridade autoral: resumo criptográfico de cada arquivo
autoral, com a data em que foi calculado.

Uso:
    python etl/registro_autoral.py
    python etl/registro_autoral.py --verificar

Saída: data/registro_autoral.json

O QUE ISTO É — E O QUE NÃO É
-----------------------------
É uma declaração datada de quais arquivos existiam, com que conteúdo exato, na
data do registro. Serve para comparar uma cópia com o original e mostrar o que
mudou, arquivo por arquivo.

NÃO é registro em cartório, não é depósito no INPI e não constitui prova
oponível a terceiros por si só. Dizer o contrário seria vender ao leitor uma
garantia que este arquivo não tem — e um projeto que se recusa a inventar
número não deveria inventar garantia jurídica.

O QUE ENTRA
-----------
Só o que é autoral: código, textos, templates e o desenho dos índices. Ficam de
fora os dados públicos (que são do INEP, do DATASUS e do IBGE, não deste
projeto) e as bibliotecas de terceiros em `site/static/vendor` e
`site/static/fonts`. Registrar o dado alheio como obra própria seria o oposto
do que este arquivo existe para fazer.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SAIDA = REPO / "data" / "registro_autoral.json"

AUTOR = {
    "nome": "Sidiao",
    "contato": "sidiao@i9educar.com",
    "obra": "Observatório Nacional da Fonoaudiologia",
    "descricao": (
        "Sítio estático data-driven com indicadores de acesso territorial, "
        "qualidade e cobertura assistencial dos cursos de Fonoaudiologia no "
        "Brasil, incluindo a formulação dos índices ICT, E, IAF, ICAF e ICRE."
    ),
}

# Diretórios e padrões varridos, na ordem em que aparecem no registro.
PADROES = [
    "README.md",
    "SECURITY.md",
    "requirements.txt",
    "etl/*.py",
    "site/*.py",
    "site/templates/*.j2",
    "site/static/css/*.css",
    "site/static/js/app.js",
    "tests/*.py",
    ".github/workflows/*.yml",
]

EXCLUIR = ("site/static/vendor", "site/static/fonts", "etl/dados",
           "site/dist", "__pycache__")


def _autorais():
    vistos = set()
    for padrao in PADROES:
        for caminho in sorted(REPO.glob(padrao)):
            relativo = caminho.relative_to(REPO).as_posix()
            if any(x in relativo for x in EXCLUIR):
                continue
            if not caminho.is_file() or relativo in vistos:
                continue
            vistos.add(relativo)
            yield relativo, caminho


def gerar():
    arquivos = []
    combinado = hashlib.sha256()
    for relativo, caminho in _autorais():
        conteudo = caminho.read_bytes()
        resumo = hashlib.sha256(conteudo).hexdigest()
        # A cadeia combinada inclui o CAMINHO, não só o conteúdo: sem isso,
        # renomear dois arquivos entre si daria o mesmo resumo global, e o
        # registro não perceberia a troca.
        combinado.update(relativo.encode("utf-8"))
        combinado.update(resumo.encode("ascii"))
        arquivos.append({
            "arquivo": relativo,
            "bytes": len(conteudo),
            "linhas": conteudo.count(b"\n") + 1,
            "sha256": resumo,
        })

    return {
        "autor": AUTOR,
        "registrado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "algoritmo": "SHA-256",
        "natureza": (
            "Declaração datada de conteúdo. Permite comparar uma cópia com o "
            "original arquivo a arquivo. Não é registro em cartório nem "
            "depósito no INPI, e não constitui, por si só, prova oponível a "
            "terceiros."
        ),
        "escopo": (
            "Apenas material autoral: código, textos, templates e o desenho "
            "dos índices. Não inclui os dados públicos (INEP, DATASUS, IBGE), "
            "que pertencem às respectivas fontes, nem bibliotecas de terceiros."
        ),
        "n_arquivos": len(arquivos),
        "bytes_totais": sum(a["bytes"] for a in arquivos),
        "sha256_combinado": combinado.hexdigest(),
        "arquivos": arquivos,
    }


def verificar():
    """Compara o estado atual com o registro gravado. Devolve código de saída."""
    if not SAIDA.exists():
        print("[REGISTRO] nenhum registro gravado; rode sem --verificar.")
        return 1
    anterior = json.loads(SAIDA.read_text(encoding="utf-8"))
    atual = gerar()

    antes = {a["arquivo"]: a["sha256"] for a in anterior["arquivos"]}
    agora = {a["arquivo"]: a["sha256"] for a in atual["arquivos"]}

    novos = sorted(set(agora) - set(antes))
    removidos = sorted(set(antes) - set(agora))
    alterados = sorted(a for a in set(antes) & set(agora) if antes[a] != agora[a])

    print(f"[REGISTRO] registrado em {anterior['registrado_em']}")
    print(f"[REGISTRO] {len(anterior['arquivos'])} arquivos no registro, "
          f"{len(atual['arquivos'])} agora")
    for rotulo, lista in (("novo", novos), ("removido", removidos),
                          ("alterado", alterados)):
        for arquivo in lista:
            print(f"  {rotulo:9} {arquivo}")

    if not (novos or removidos or alterados):
        print("[REGISTRO] idêntico ao registro gravado.")
        return 0
    print("[REGISTRO] há diferenças — regrave o registro se forem intencionais.")
    return 1


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--verificar", action="store_true",
                   help="compara o estado atual com o registro, sem regravar")
    args = p.parse_args()

    if args.verificar:
        raise SystemExit(verificar())

    registro = gerar()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(registro, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    print(f"[REGISTRO] {registro['n_arquivos']} arquivos, "
          f"{registro['bytes_totais']} bytes")
    print(f"[REGISTRO] sha256 combinado: {registro['sha256_combinado']}")
    print(f"[REGISTRO] -> {SAIDA}")


if __name__ == "__main__":
    main()
