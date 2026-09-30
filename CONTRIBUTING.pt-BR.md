# Guia de Contribuição

[English](CONTRIBUTING.md) | **Português**

## Fluxo de Trabalho

Toda alteração parte de uma *issue* e chega ao `main` por um *pull request*.

1. **Issue.** Descreva a tarefa com título no infinitivo (por exemplo, "Implementar ...", "Corrigir ...") e corpo nas seções `## Contexto`, `## Objetivo` e `## Critérios de aceite`, estes em forma de lista de tarefas. Associe a *issue* a um *milestone* de versão e aplique as *labels*:
   - tipo: `feature`, `bug`, `refactor`, `documentation`, `test`, `chore`, `security`, `dependencies` ou `technical-debt`;
   - área: `frontend` ou `backend`;
   - prioridade: `priority:high`, `priority:medium` ou `priority:low`.
2. **Branch.** Crie o *branch* a partir da própria *issue*, pelo botão *Create a branch* do GitHub ou com `gh issue develop <número> --base main --checkout`. O nome fica no formato `<número>-<título-da-issue>`, e a *issue* é fechada automaticamente quando o *pull request* for mesclado.
3. **Commits.** Siga o [Conventional Commits](https://www.conventionalcommits.org/pt-br/) em português, com uma linha curta e sem corpo:
   ```text
   feat: adiciona estratégia gulosa de atribuição
   fix: corrige consulta de ponto de acesso por identificador
   docs: atualiza guia de instalação
   ```
   Tipos usados: `feat`, `fix`, `refactor`, `docs`, `test` e `chore`.
4. **Pull request.** Abra para o `main`, com título no presente descrevendo o resultado (por exemplo, "Adiciona estratégia gulosa de atribuição"). A mesclagem é feita por *squash*, o que gera um único commit no `main` com o número do *pull request*.

## Versionamento

O projeto segue o [Versionamento Semântico](https://semver.org/lang/pt-BR/) (`MAJOR.MINOR.PATCH`), aplicado à interface pública: rotas HTTP, formato das respostas JSON e forma de executar o sistema (`docker-compose.yml`, portas e variáveis do `.env`).

- `PATCH` para correções que não alteram o comportamento esperado;
- `MINOR` para funcionalidades novas compatíveis com as anteriores;
- `MAJOR` para mudanças que quebram a compatibilidade.

Cada versão tem um *milestone* com as *issues* que a compõem. Ao concluí-lo, a versão é marcada com uma *tag* (`vX.Y.Z`) e um *release* no GitHub.

## Ambiente de Desenvolvimento

```bash
cp .env.example .env
docker compose up -d --build --remove-orphans
```

A interface fica em `http://localhost:3000`. No Windows, também é possível executar os serviços sem Docker Compose com `scripts/management/start-local.ps1` (ver [scripts/management/SCRIPTS.pt-BR.md](scripts/management/SCRIPTS.pt-BR.md)).

## Testes

Os testes usam `unittest` e ficam em `services/<serviço>/tests/`.

```bash
# access_point_service (requer as dependências do serviço instaladas)
python -m unittest services/access_point_service/tests/test_access_point.py

# analysis_service (constrói e sobe um contêiner, requer Docker)
python -m unittest services/analysis_service/tests/test_backtracking.py
```

Antes de abrir um *pull request*, rode os testes dos serviços alterados e inclua testes para o comportamento novo.

## Padrões de Código

- **Python:** siga a PEP 8.
- **C (`analysis_service`):** C11, compilando sem avisos com `-Wall -Wextra`, como no `Dockerfile` do serviço.
- **Comentários e mensagens:** em português.
- **Documentação:** atualize o `README.md`, os arquivos de `docs/` e o README do serviço quando a mudança alterar rotas, parâmetros ou a forma de executar o sistema.
- **Idiomas da documentação:** cada documento existe em inglês, no arquivo original (ex.: `README.md`), e em português, no arquivo com o sufixo `.pt-BR.md` (ex.: `README.pt-BR.md`). Toda mudança na documentação deve ser feita nas duas versões, e os links entre documentos devem apontar para os arquivos do mesmo idioma.
