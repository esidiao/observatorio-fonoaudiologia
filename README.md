# Observatório Nacional da Formação em Fonoaudiologia

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
| Polos EaD | 793 registros em 618 municípios |
| Cursos avaliados no CPC 2023 | 74, em 23 UFs |
| Municípios com fonoaudiólogo no SUS | 4.207 de 5.571 |
| Municípios com serviço fonoaudiológico **ofertado ao SUS** | 2.118 |
| Municípios com o mesmo serviço declarado (SUS ou privado) | 2.230 |
| Fonoaudiólogos vinculados ao SUS | 23.760 |

A especificação deste projeto trazia 616 municípios com polo. A apuração dá
**618**, e o número foi conferido de forma independente contra outro
levantamento do mesmo Censo. Vale 618.

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
* **rede especializada** — municípios com estabelecimento que oferta **ao SUS** serviço
  fonoaudiológico ou auditivo (CNES, serviço 107 *Atenção à Saúde Auditiva* e serviço 135
  classificações *Reabilitação auditiva* e *Atenção fonoaudiológica*).

São publicados separadamente, com escalas próprias. Fundi-los num índice único exigiria
um peso arbitrário entre "tem profissional" e "tem serviço habilitado" — e peso arbitrário
é estimativa disfarçada.

### Serviço declarado não é serviço público

`rlEstabServClass` traz `CO_AMBULATORIAL_SUS` e `CO_HOSPITALAR_SUS`, e sem olhá-las o
indicador conta clínica privada como rede pública. Medida a diferença: o serviço é
**declarado** em 2.230 municípios por 9.159 estabelecimentos, e **ofertado ao SUS** em
2.118 municípios por 5.471. Quarenta por cento do que se contava como rede especializada
pública não atende pelo SUS.

A cobertura pública é o que vira índice; o total declarado sai ao lado, nos campos
terminados em `_total`, porque a distância entre os dois diz quanto da rede do município
é acessível pelo SUS.

Na mesma tabela, a coluna `ST_ATIVO_SN` vem **vazia em todas as linhas** deste export. O
filtro de serviço inativo que existia no extrator lia coluna sempre em branco e nunca
excluiu nada — agora a ausência é contada e declarada, em vez de disfarçada de filtro.

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

### Portões de qualidade (GO)

```bash
python etl/indices.py --autoteste
python site/estatistica.py
python site/catalogo.py
```

Conferem, respectivamente: as fórmulas dos índices contra um estado sintético
calculado à mão; Spearman, valor de p e regressão múltipla contra casos de
resultado conhecido; e a coerência interna do catálogo de indicadores.

### Testes

```bash
python tests/test_catalogo.py
python tests/test_validacao.py
python tests/test_check_fontes.py
```

Rodam como script ou sob `pytest`, se você o tiver instalado.

## Atualizar os dados

```bash
python etl/pipeline.py --check-only     # só verifica se as fontes mudaram
python etl/pipeline.py --ano 2024       # extrai, calcula, valida, publica
python etl/pipeline.py --so-riqueza     # só a guarda de riqueza
python etl/serie.py --anos 2023 2024    # série histórica
```

A extração do CNES leva perto de uma hora, porque o FTP do DATASUS derruba a
maior parte das conexões que usam `REST`. Ela guarda as fatias já filtradas em
`etl/dados/cnes_<competência>/`, então reprocessar a agregação depois é
instantâneo. Use `--pular-cnes` quando estiver mexendo em outra parte.

O pipeline encadeia extração -> índices -> enriquecimento -> **conferência de riqueza** ->
validação, e só grava se tudo passar. A conferência de riqueza compara o número de campos
por UF com o que está em `git show HEAD` e aborta se o novo resultado for mais pobre —
guarda que existe porque, no projeto de Farmácia, republicar por um caminho parcial
derrubou 33 dos 51 campos com todos os testes verdes: nenhum teste checava *presença* de
campo.

## Publicação

O deploy é **manual**. Um push na `main` roda os portões, os testes e o build,
mas não publica nada: publicar é um ato deliberado.

Para colocar no ar, em **Actions → CI → Run workflow**, escolha a ação:

| Ação | O que faz |
|---|---|
| `publicar` | valida e publica no GitHub Pages |
| `so-validar` | roda portões, testes e build; não publica |
| `verificar-fontes` | só checa se INEP ou CNES publicaram edição nova |

A verificação de fontes também roda sozinha toda segunda-feira e abre issue
quando encontra edição nova — ou quando a verificação fica **indeterminada**,
que é diferente de não ter novidade.

## Princípio inegociável

Nenhum indicador é estimado, interpolado ou preenchido por analogia. Sem fonte oficial
para um recorte, o valor é `null` e aparece como **"sem dados"** — nunca zero, nunca média
plausível. Todo número carrega proveniência: fonte, ano e data de extração.

Isso pesa mais aqui do que no observatório de Farmácia: com 24 UFs e 74 cursos avaliados,
as lacunas são proporcionalmente maiores e a tentação de preencher por analogia é
constante.

## Autoria e direitos

**Edson Sidião de Souza Júnior** — sidiao@i9educar.com ·
[Lattes](http://lattes.cnpq.br/9464330669014306)
Farmacêutico, Mestre e Doutor em Medicina Tropical (UFG), avaliador *ad hoc*
INEP/MEC há mais de quinze anos.

© 2026, todos os direitos reservados sobre a obra autoral (Leis 9.610/1998 e
9.609/1998). Os **dados primários** são públicos e pertencem ao INEP, ao
Ministério da Saúde e ao IBGE; os **indicadores calculados** são liberados para
reúso com citação.

Termos completos, forma de citação e registro de anterioridade em
[`DIREITOS.md`](DIREITOS.md). Ver também [`SECURITY.md`](SECURITY.md) e a
página de aviso legal do site.
