# Estratégia de postagens — @diretonaquestao

Objetivo: ganhar seguidores que estudam para concursos no RS, sendo o perfil mais
confiável e mais rápido para saber **o que abriu, até quando dá para se inscrever e
como treinar**. Cada post leva a pessoa para o app grátis (link na bio).

## Para quem a gente fala

Quem procura os concursos **tradicionais**: prefeituras, câmaras, institutos federais,
hospitais públicos e tribunais do RS, principalmente cargos de nível fundamental e médio
(agente administrativo, serviços gerais, motorista, professor, técnico em enfermagem).
Salário alto pode aparecer, mas não é o foco: a arte mostra a faixa inteira de salários
e destaca o cargo com mais vagas ou o de nível médio.

## Os 4 tipos de post

| Tipo | Para que serve | Quando |
|---|---|---|
| **Notícia** (edital publicado / inscrições abertas) | Atrair quem pesquisa o concurso da sua cidade. É o que mais é compartilhado em grupos. | 1 por dia, no almoço ou à noite |
| **Últimos dias** | Gera urgência verdadeira e muito envio para amigos. | 2 dias antes do fim das inscrições |
| **Agenda da semana** | O post mais **salvo**: lista os prazos de vários concursos de uma vez. | Sábado, 11h |
| **Questão do dia** | Gera **comentários** e mostra o app. Carrossel: questão no slide 1, gabarito comentado no slide 2. | 2 a 3 por semana |

## Horários

- **08:00** (café da manhã), **12:15** (hora do almoço) e **19:00** (depois do trabalho), todos os dias.
- **Sábado 11:00**: agenda da semana. Domingo de manhã pode ser **09:00**.
- Até 3 posts por dia (pedido do dono em 23/11/2026). O robô nunca solta dois posts com menos de 2 horas de diferença.

## Regras que não mudam

1. Toda notícia com a **fonte** na arte e na legenda (edital, Diário Oficial, site da banca ou do órgão).
2. "EDITAL PUBLICADO" só quando o edital saiu. Antes disso é "CONCURSO PREVISTO".
3. "ÚLTIMOS DIAS" só quando for verdade. O robô não publica notícia depois do prazo (`expira_em`).
4. Posts da rotina automática (a cada 3 dias: notícias, agendas e questões do dia) entram já aprovados, por decisão do dono em 26/11/2026. Posts pausados continuam precisando de aprovação.
5. Questão do dia é sempre identificada como inédita, "no estilo da banca". Nunca dizer que é de prova oficial.

## O que cada legenda tem

1. Primeira linha com o fato (aparece antes do "ver mais").
2. Lista curta: vagas, cargos, salários, prazo, taxa, data da prova.
3. Fonte.
4. Um pedido só: **salvar**, **mandar para alguém** ou **comentar a cidade**.
5. Convite para o app (link na bio).
6. De 5 a 6 hashtags: a cidade, a banca, `#concursosrs` e `#concursopublico`.

## O que fazer à mão (o robô não faz)

- Responder todos os comentários no mesmo dia, principalmente nas questões.
- Fixar no topo do perfil a agenda da semana mais recente.
- Repostar no story o post do dia com a figurinha de **link** apontando para o app.
- Guardar os stories nos destaques: Abertas, Previstos, RS, Nacionais, Resultados, Grátis.
- Ajustar a bio para os horários reais: "Notícias todo dia às 12h15 e às 19h".

## Como medir (olhar toda segunda-feira nos Insights)

- **Seguidores novos na semana.**
- **Salvamentos e compartilhamentos por post**: mostram que tipo de post repetir.
- **Cliques no link da bio**: mostram se o app está recebendo visitas.

Depois de 3 a 4 semanas, manter os tipos que mais trazem seguidores e reduzir os outros.

## Como preparar novos posts

1. Escrever os dados em `modelo/conteudo.json` (sempre conferidos na fonte).
2. `python modelo/gerar_posts.py` cria as artes, o story e o Reels em `posts/<ID>/`.
3. `python modelo/atualizar_fila.py "Nome de quem aprovou"` coloca na `fila.json`.
4. O robô publica sozinho na data e hora de cada post.
