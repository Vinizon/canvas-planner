# Canvas Planner (PUC Minas)

Gera um cronograma diário de estudos a partir das entregas pendentes no Canvas
(pucminas.instructure.com), respeitando sua rotina fixa (aula, trabalho remoto,
sono, leitura, atividade física) e recalculando o ritmo necessário por atividade
todo dia.

## O que ele faz

- Busca no Canvas (via API) todas as tarefas/provas/quizzes pendentes.
- Estima o esforço necessário por tipo de atividade (lista, prova, projeto, etc).
- Calcula, pra cada uma, quantos minutos/dia você precisa dedicar a partir de
  hoje pra terminar com 1 dia de folga antes do prazo.
- Encaixa isso nos blocos de estudo livres da sua rotina (ver `config.json`),
  sem invadir aula, trabalho, sono, leitura ou atividade física.
- Avisa quando um dia está sobrecarregado (mais trabalho do que capacidade).
- Só some entregas menos de 3 semanas — o resto fica numa lista "mais pra
  frente", sem poluir o dia a dia.
- Mostra avisos/comunicados recentes das matérias.
- Lista arquivos recentes (PDFs, slides) de cada matéria, com link direto —
  sem resumo automático, propositalmente: resumo de IA em conteúdo técnico
  (ex: provas de lógica) tem risco real de simplificar ou errar detalhe.
- Mostra nota atual por matéria, quando o Canvas já tiver lançado.
- Baixa os PDFs/arquivos recentes de cada matéria para `materials/<matéria>/`,
  local na máquina. Isso é o que permite eu (ou qualquer sessão do Claude Code
  rodando aqui) ler e explicar o conteúdo dos arquivos quando você pedir —
  sem precisar de acesso à internet nem ao Canvas de novo. Roda todo dia
  junto com o resto; só rebaixa o que mudou (compara tamanho do arquivo).
- Gera uma página HTML (`index.html`) publicável como Artifact, e roda
  sozinho todo dia via uma tarefa agendada local (veja "Automação" abaixo).

## O que ele **não** faz

- Não existe grade de horário de aulas no Canvas desta instituição (isso fica
  no sistema acadêmico da PUC, não na API do Canvas). Por isso os horários de
  aula em `config.json` foram digitados a partir do que você descreveu, não
  puxados automaticamente. Se sua grade mudar por semestre, edite o arquivo.
- Não entrega nada por você, só organiza o tempo.

## Configuração

Tudo em `config.json`:

- `week`: qual "tipo de dia" cada dia da semana usa.
- `day_templates`: os horários fixos de cada tipo de dia (aula, trabalho,
  exercício, leitura, sono, estudo). Ajuste os `blocks` se sua rotina mudar.
- `effort_rules`: quanto tempo estimar por tipo de atividade, baseado em
  palavras-chave no título (prova, lista, atividade, projeto...). Ajuste os
  minutos se achar que uma categoria está sub/superestimada — o script vai
  aprendendo com o seu feedback informal (você edita o número).
- `planning.active_window_days`: a partir de quantos dias antes do prazo uma
  atividade entra no ritmo diário (padrão: 21 dias).

## Uso

```bash
cd canvas-planner
python3 plan.py                  # mostra o plano de hoje + próximos dias
python3 plan.py --days 21        # muda o horizonte da visão "próximos dias"
python3 plan.py --save hoje.md   # também salva em arquivo
```

Não precisa instalar nada — só usa a biblioteca padrão do Python 3.9+.

## Sobre o token (`.env`)

O arquivo `.env` guarda seu token de acesso pessoal do Canvas
(`CANVAS_TOKEN`). Esse token equivale à sua senha para fins de API — dá acesso
de leitura a tudo que você vê no Canvas.

- O arquivo está com permissão `600` (só você lê) e listado no `.gitignore`.
- **Nunca** cole esse token em código que vá pra um repositório público, print
  de tela compartilhado, ou qualquer lugar fora deste `.env`.
- Se em algum momento achar que ele vazou, revogue e gere um novo em
  `pucminas.instructure.com/profile/settings` → "Novo Token de Acesso" → apague
  o antigo.

## Atualização automática (GitHub Actions)

O workflow `.github/workflows/cronograma.yml` roda todo dia às 06:00 (horário de Brasília),
busca os dados no Canvas, gera a página, protege com senha (StatiCrypt) e publica no GitHub Pages.

Secrets necessários (Settings → Secrets and variables → Actions):
- `CANVAS_TOKEN`: token do Canvas
- `PAGE_PASSWORD`: senha para abrir a página

O `.staticrypt.json` guarda o "salt" da criptografia (não é segredo). Mantenha ele no repositório
para que o "Lembrar neste aparelho" continue valendo entre as atualizações.
Localmente, `SKIP_MATERIALS=1` pula o download dos arquivos das matérias.
