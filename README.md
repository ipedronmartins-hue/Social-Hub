# Hub feed

Recolhe feeds públicos (notícias, Reddit, música, ciclismo, hacking…) e publica um único `hub.json`
com miniaturas já reduzidas, para uma app de telemóvel só de leitura. Sem contas, sem cookies, sem dados pessoais.

- `feeds.json`: as fontes, por secção. Editar e fazer commit; a próxima recolha já as usa.
- `build_feed.py`: recolhe, limpa e escreve `out/hub.json` e `out/img/`.
- `.github/workflows/build.yml`: corre de 30 em 30 minutos e publica no GitHub Pages.

Uma fonte que falha não estraga as outras: fica em `failures` dentro do `hub.json`.

Atenção: o GitHub desativa as tarefas agendadas de um repositório público ao fim de 60 dias sem atividade.
Um commit (por exemplo, acrescentar uma fonte) volta a ativá-las.

Correr no PC: `pip install -r requirements.txt` e `python build_feed.py`.
