# Observatório Nacional da Fonoaudiologia

Site estático data-driven com indicadores de acesso territorial, qualidade e cobertura
assistencial dos cursos de Fonoaudiologia no Brasil.

Projeto irmão — e independente — do
[Observatório Nacional da Formação Farmacêutica](https://github.com/esidiao/observatorio-formacao-farmaceutica).
Compartilha o método e o design system; não compartilha código, dados nem dependências.

## O que este observatório mede

| | Fonoaudiologia (Censo 2024) |
|---|---|
| Registros no Censo | 939 |
| UFs com oferta **presencial** | **24** de 27 |
| Municípios com oferta presencial | 83 |
| Vagas presenciais | 17.028 |
| Vagas EaD (atribuídas à UF-sede) | 12.876 |
| Polos EaD | 793 registros em 616 municípios |
| Cursos avaliados no CPC 2023 | 74, em 23 UFs |

**A oferta presencial cobre 24 UFs, não 27.** Amapá, Mato Grosso do Sul e Roraima não têm
curso presencial de Fonoaudiologia. Eles aparecem no site como *sem oferta presencial* —
explicitamente, com o dado de EaD e de polos que lhes cabe. Não são omitidos: um estado
cinza no mapa é informação, não falha de pipeline. Toda validação de fechamento
territorial vale sobre as UFs presentes, nunca sobre o país inteiro.

## Estrutura

```
/etl                        Scripts ETL (Python): extração, índices, pipeline
/data                       Dados versionados: nacional.json, _proveniencia.json
/etl/dados                  Recortes brutos — NÃO versionados (ver .gitignore)
/site                       Gerador estático (Python/Jinja2) + templates + assets
/site/dist                  Site gerado — NÃO versionar
/tests                      Portão de qualidade (GO) + integridade + verificador de fontes
/.github/workflows/ci.yml   CI: valida -> constrói -> publica
```

## Fontes

| Indicador | Fonte | Acesso |
|---|---|---|
| Oferta, vagas, matrículas, polos | Censo da Educação Superior 2024 (INEP) | HTTPS, ZIP lido por `Range` |
| CPC, IDD, ENADE, perfil docente | CPC 2023 (INEP), área FONOAUDIOLOGIA | HTTPS |
| Força de trabalho no SUS | CNES — vínculos com CBO `2238xx` | FTP DATASUS |
| Rede especializada | CNES — serviços 107 e 135 (fonoaudiológicos/auditivos) | FTP DATASUS |
| População e municípios | IBGE (agregado 6579; API de localidades) | HTTPS |

### Por que dois indicadores de cobertura, e não um

O ICON do observatório de Farmácia é `municípios com Farmácia Popular / municípios com
oferta`. Essa proxy é específica da profissão farmacêutica e não transfere. Para
Fonoaudiologia a pergunta "onde existe rede pública que absorve a formação?" tem duas
metades que nenhuma fonte única responde:

* **força de trabalho** — municípios com ao menos um vínculo de fonoaudiólogo no CNES
  (CBO `2238xx`);
* **rede especializada** — municípios com estabelecimento que declara serviço
  fonoaudiológico ou auditivo (CNES, serviço 107 *Atenção à Saúde Auditiva* e serviço 135
  classificações *Reabilitação auditiva* e *Atenção fonoaudiológica*).

São publicados separadamente, com escalas próprias. Fundi-los num índice único exigiria
um peso arbitrário entre "tem profissional" e "tem serviço habilitado" — e peso arbitrário
é estimativa disfarçada.

**O que não foi possível medir:** a habilitação de Centro Especializado em Reabilitação
(CER) não é publicada na base do CNES. Os códigos existem na tabela de domínio
(`tbSubGruposHabilitacao`: 2208–2211, 8223–8225), mas nenhuma tabela-fato os relaciona a
estabelecimento ou município — `tbIncentivos` traz apenas cinco códigos de incentivo
financeiro, nenhum deles de reabilitação. Por isso o CER **não** vira indicador aqui, e
não é substituído por aproximação. Fica registrado como limitação conhecida.

## Rodar localmente

```bash
pip install -r requirements.txt
```

### Gerar o site

```bash
python site/build.py
```

O site sai em `site/dist/`.

### Portão de qualidade (GO)

```bash
python etl/indices.py --autoteste
```

### Testes

```bash
python -m pytest tests/ -v
```

## Atualizar os dados

```bash
python etl/pipeline.py --check-only     # só verifica se as fontes mudaram
python etl/pipeline.py --ano 2024       # extrai, calcula, valida, publica
```

O pipeline encadeia extração -> índices -> enriquecimento -> **conferência de riqueza** ->
validação, e só grava se tudo passar. A conferência de riqueza compara o número de campos
por UF com o que está em `git show HEAD` e aborta se o novo resultado for mais pobre —
guarda que existe porque, no projeto de Farmácia, republicar por um caminho parcial
derrubou 33 dos 51 campos com todos os testes verdes: nenhum teste checava *presença* de
campo.

## Princípio inegociável

Nenhum indicador é estimado, interpolado ou preenchido por analogia. Sem fonte oficial
para um recorte, o valor é `null` e aparece como **"sem dados"** — nunca zero, nunca média
plausível. Todo número carrega proveniência: fonte, ano e data de extração.

Isso pesa mais aqui do que no observatório de Farmácia: com 24 UFs e 74 cursos avaliados,
as lacunas são proporcionalmente maiores e a tentação de preencher por analogia é
constante.

## Licença e autoria

Ver [`SECURITY.md`](SECURITY.md), a página de aviso legal do site e o registro de
anterioridade autoral em `data/registro_autoral.json`.
