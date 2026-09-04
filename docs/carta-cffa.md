# Carta de apresentação ao Conselho Federal de Fonoaudiologia

> **Antes de enviar — confira o destinatário.**
> A Dra. **Silvia Tavares de Oliveira** presidiu o **13º Colegiado (2019–2022)**.
> Quem preside o **15º Colegiado (2025–2028)**, em exercício em 2026, é a
> Profa. Dra. **Andréa Cintra Lopes**, reeleita para o período.
> A carta abaixo está endereçada à presidência atual. Se a informação estiver
> desatualizada ou se o contato pretendido for outro, basta trocar as duas
> primeiras linhas do cabeçalho.
>
> Fontes consultadas: [posse do 15º Colegiado](https://fonoaudiologia.org.br/posse-do-15o-colegiado-do-conselho-federal-de-fonoaudiologia/) ·
> [reeleição da presidência](https://www1.fob.usp.br/professora-andrea-cintra-lopes-e-reeleita-presidente-do-conselho-federal-de-fonoaudiologia/)

> **Versão para WhatsApp:** [`carta-cffa-whatsapp.md`](carta-cffa-whatsapp.md) —
> três mensagens curtas, com a formatação que o WhatsApp entende. Esta carta
> formal serve como anexo em PDF ou como e-mail, se a conversa avançar.

---

**À Presidência do Conselho Federal de Fonoaudiologia**
A/C Profa. Dra. Andréa Cintra Lopes — Presidente

**Assunto:** Apresentação do Observatório Nacional da Formação em Fonoaudiologia
e oferecimento de colaboração

---

Prezada Presidente,

Escrevo para apresentar ao Conselho Federal de Fonoaudiologia um trabalho que
desenvolvi de forma independente e que hoje está publicamente disponível:

**https://esidiao.github.io/observatorio-fonoaudiologia/**

Antes de descrevê-lo, uma declaração que me parece devida: **não sou
fonoaudiólogo.** Sou farmacêutico, doutor em Medicina Tropical pela UFG, e há
mais de quinze anos atuo como avaliador *ad hoc* do INEP/MEC em avaliações
*in loco* de cursos de graduação da área da saúde. É dessa experiência — a de
quem lida com o Censo da Educação Superior, com o SINAES e com as Diretrizes
Curriculares Nacionais — que vem a competência aplicada aqui. Ela é sobre
*como se mede a formação*, e não substitui a leitura de quem exerce a
profissão. É precisamente por isso que escrevo ao Conselho.

## O que o observatório reúne

Trata-se de um sítio estático que lê fontes públicas oficiais, calcula
indicadores e publica o resultado **junto com os dados brutos que o
originaram**. O ciclo atual traz:

| | |
|---|---|
| Registros de curso no Censo 2024 | 939 |
| UFs com oferta **presencial** | **24** de 27 |
| Municípios com curso presencial | 83 de 5.571 |
| Vagas anuais | 17.028 presenciais + 12.876 EaD |
| Polos de EaD | 793 registros em 618 municípios |
| Matrículas / concluintes | 22.996 / 2.027 |
| Cursos avaliados no CPC 2023 | 74, em 23 UFs |
| Municípios com fonoaudiólogo no SUS | 4.207 |
| Municípios com serviço fonoaudiológico ou auditivo | 2.230 |
| Fonoaudiólogos com vínculo no SUS | 23.760 |

O sítio oferece páginas para cada uma das 27 unidades da federação e para os
629 municípios com curso ou polo, mapas com detalhamento municipal, comparação
entre estados, correlações com significância declarada, um índice sintético de
pesos ajustáveis pelo leitor, série histórica entre as edições do Censo e
glossário de todos os 60 indicadores. Os dados são baixáveis em CSV, JSON e
planilha Excel.

## Três achados que talvez interessem ao Conselho

**A oferta presencial não cobre o país.** Amapá, Mato Grosso do Sul e Roraima
não têm um único curso presencial de Fonoaudiologia. Optei por mantê-los
visíveis no observatório, com os dados de EaD e de cobertura assistencial que
lhes cabem, em vez de omiti-los — um estado em cinza no mapa é informação sobre
política pública, não falha de apuração.

**A capacidade formativa é hoje 43% a distância**, e essas vagas ficam
registradas na sede da mantenedora, não onde o aluno está. Quando a
concentração de mercado é medida sobre a capacidade total, São Paulo passa de
0,07 para 0,18 no índice de Herfindahl-Hirschman por mantenedora, e o Paraná de
0,16 para 0,49. A leitura muda de "mercado pulverizado" para "mercado
concentrado em poucos grupos".

**Formação e assistência não coincidem no território.** Há fonoaudiólogo
vinculado ao SUS em 4.207 municípios, mas serviço fonoaudiológico ou auditivo
declarado em apenas 2.230 — e curso presencial em 83. Publiquei os dois
indicadores de cobertura separadamente, porque fundi-los exigiria arbitrar um
peso entre "há profissional" e "há serviço", e peso arbitrário é estimativa
disfarçada.

## O compromisso metodológico

Nenhum indicador é estimado, interpolado ou preenchido por analogia. Onde não
existe fonte oficial para um recorte, o valor aparece como **"sem dados"** —
nunca como zero, nunca como média plausível. Tocantins, por exemplo, tem curso
presencial e nenhum curso avaliado no ciclo do CPC 2023: sua página exibe a
seção de qualidade inteira em branco, com a explicação do porquê.

Pelo mesmo princípio, **não há indicador de Centro Especializado em
Reabilitação**. Os códigos de habilitação existem na tabela de domínio do CNES,
mas nenhuma tabela-fato os relaciona a estabelecimento ou município. Registrei a
ausência como limitação declarada, em vez de substituí-la por aproximação.

Todo o código é aberto, o pipeline roda sem credenciais a partir de fontes
públicas, e cada número carrega fonte, ano e data de extração.

## O que ofereço

Coloco-me à disposição do Conselho, sem qualquer contrapartida financeira, para:

1. **Submeter a metodologia à crítica técnica do CFFa.** Os índices que formulei
   — concentração territorial, adequação formativa, cobertura assistencial —
   refletem a perspectiva de quem avalia cursos, não a de quem exerce a
   Fonoaudiologia. Se a Comissão de Ensino ou o corpo de conselheiros
   identificar recortes mais pertinentes à profissão, reformulo.

2. **Incorporar indicadores que o Conselho considere relevantes** e que tenham
   fonte oficial verificável — inclusive dados do próprio Sistema
   CFFa/CREFONOs, se houver interesse em publicá-los.

3. **Adaptar o observatório às necessidades do Conselho**: recortes regionais
   por CREFONO, relatórios periódicos, séries específicas, ou uma versão
   hospedada em domínio do CFFa.

4. **Transferir a manutenção**, se o Conselho preferir assumir o projeto. O
   código está documentado e o pipeline é reproduzível por qualquer equipe
   técnica.

5. **Corrigir o que estiver errado.** É o item mais importante. Se houver
   divergência entre o observatório e a realidade da profissão, quero saber — e
   a correção será publicada com o devido crédito a quem a apontar.

Um observatório sobre uma profissão construído por alguém de fora dela só se
justifica se estiver aberto à correção de dentro. É com esse espírito que o
apresento.

Permaneço à disposição para uma conversa, presencial ou remota, no momento que
for conveniente ao Conselho.

Respeitosamente,

**Edson Sidião de Souza Júnior**
Farmacêutico · CRF/GO 3686
Mestre e Doutor em Medicina Tropical (UFG)
Avaliador *ad hoc* INEP/MEC
I9 Educar — Consultoria em Gestão Educacional
sidiao@i9educar.com
[Currículo Lattes](http://lattes.cnpq.br/9464330669014306)

---

*Observatório: https://esidiao.github.io/observatorio-fonoaudiologia/*
*Código e dados: https://github.com/esidiao/observatorio-fonoaudiologia*
