# Guia de Contribuição

[English](CONTRIBUTING.md) | **Português**

## Branches

- **`main`**: branch padrão e protegida. Recebe apenas as versões prontas e não aceita *push* direto, *force push* nem exclusão; quem clona ou visita o repositório cai na última versão estável.
- **`develop`**: branch de integração. Recebe os *pull requests* das *issues* e acumula a versão em andamento.
- **Branches de *issue***: partem da `develop` e voltam para ela.

## Fluxo de Trabalho

Toda alteração parte de uma *issue* e chega à `develop` por um *pull request*.

1. **Issue.** Descreva a tarefa com título no infinitivo (por exemplo, "Implementar ...", "Corrigir ...") e corpo nas seções `## Contexto`, `## Objetivo` e `## Critérios de aceite`, estes em forma de lista de tarefas. Associe a *issue* a um *milestone* de versão e aplique as *labels*:
   - tipo: `feature`, `bug`, `refactor`, `documentation`, `test`, `chore`, `security`, `dependencies` ou `technical-debt`;
   - área: `frontend` ou `backend`;
   - prioridade: `priority:high`, `priority:medium` ou `priority:low`.
2. **Branch.** Crie o *branch* pela própria *issue*, com base na `develop`: `gh issue develop <número> --base develop --checkout`. Informe sempre a base, já que a branch padrão é a `main`. O nome fica no formato `<número>-<título-da-issue>`.
3. **Commits.** Siga o [Conventional Commits](https://www.conventionalcommits.org/pt-br/) em português, com uma linha curta e sem corpo:
   ```text
   feat: adiciona estratégia gulosa de atribuição
   fix: corrige consulta de ponto de acesso por identificador
   docs: atualiza guia de instalação
   ```
   Tipos usados: `feat`, `fix`, `refactor`, `docs`, `test` e `chore`.
4. **Pull request.** Abra para a `develop`, informando a base (`gh pr create --base develop`), com título no presente descrevendo o resultado (por exemplo, "Adiciona estratégia gulosa de atribuição") e corpo com `Closes #<issue>`, que vincula a *issue* ao *pull request*. A mesclagem é feita por *squash*, o que gera um único commit na `develop` com o número do *pull request*.
5. **Fechamento da issue.** O GitHub só fecha *issues* automaticamente em mesclagens na branch padrão; como os *pull requests* vão para a `develop`, feche a *issue* após a mesclagem. Antes, confira cada critério de aceite e marque os cumpridos na descrição (`- [ ]` → `- [x]`); um critério não cumprido fica desmarcado, com um comentário explicando o que falta. Depois, feche como concluída, citando o *pull request*: `gh issue close <número> --reason completed --comment "Concluída no #<pull request>."`.

## Versionamento

O projeto segue o [Versionamento Semântico](https://semver.org/lang/pt-BR/) (`MAJOR.MINOR.PATCH`), aplicado à interface pública.

**Interface pública** é o que outros programas e scripts usam do PowerTrackZ:

- as rotas HTTP dos serviços e os campos das requisições e respostas JSON, como documentados em [`docs/api`](docs/api/README.pt-BR.md), incluindo os valores padrão que mudam o resultado (como o critério de otimização ou o raio padrão dos APs);
- a forma de executar o sistema: `docker-compose.yml`, portas e variáveis do `.env`.

Não fazem parte dela a aparência e os textos das telas nem o texto das mensagens de erro (os códigos de status e os campos da resposta, sim).

| Parte | Quando sobe | Exemplos |
|---|---|---|
| `PATCH` | Correções que não alteram o comportamento esperado nem a compatibilidade | v1.2.1: padronização visual e revisão dos textos, sem mudar rotas nem campos |
| `MINOR` | Funcionalidades novas compatíveis com as anteriores: rotas, campos ou parâmetros novos e opcionais | v1.3.0: novas estratégias e critério de otimização configurável, com o padrão atual mantido |
| `MAJOR` | Mudanças que quebram a compatibilidade: remover ou renomear uma rota ou campo, mudar o formato de uma resposta ou um valor padrão que altera os resultados | remover os campos `cor` e `proposed_cor` da resposta da análise |

**Descontinuação.** Para renomear ou substituir um campo, parâmetro ou rota sem quebrar a compatibilidade, a versão MINOR aceita os dois nomes e a *release* registra o antigo como descontinuado; o nome antigo só é removido na próxima versão MAJOR. Foi o que aconteceu com `clique_factor`, que continua aceito como alternativa a `min_degree`.

A v1.2.0 é uma exceção registrada: publicada como MINOR, ela renomeou campos de `execution.comparison` sem manter os nomes antigos e mudou valores padrão, e pelo SemVer deveria ter sido a v2.0.0. Versões publicadas não são renumeradas; o desvio está anotado nas notas da *release*.

Cada versão tem um *milestone* com as *issues* que a compõem. Quando todas estão concluídas na `develop`:

1. abra um *pull request* da `develop` para a `main` e mescle-o por *merge commit* (não por *squash*, para que as duas branches não divirjam e a versão seguinte não repita as mudanças já mescladas);
2. marque a versão com uma *tag* (`vX.Y.Z`) no commit resultante da `main`;
3. publique um *release* no GitHub a partir da *tag*.

## Correção de Versões Publicadas (*hotfix*)

Um erro encontrado em uma versão já publicada é corrigido em uma versão PATCH (por exemplo, a v1.3.1 corrige a v1.3.0). Ela só pode conter correções que não alterem o comportamento esperado nem a compatibilidade: um cálculo errado, um erro na interface ou uma dependência com falha de segurança. Funcionalidades novas e mudanças na interface pública ficam para a próxima versão MINOR ou MAJOR.

Como a `develop` pode conter trabalho ainda não publicado, a correção parte da `main`:

1. **Issue.** Abra a *issue* no *milestone* da versão de correção (por exemplo, `v1.3.1`), criando o *milestone* se preciso.
2. **Branch.** Crie o *branch* a partir da `main`: `gh issue develop <número> --base main --checkout`.
3. **Pull request.** Abra para a `main` (`gh pr create --base main`), com corpo `Closes #<issue>`, e mescle por *squash*. Como a `main` é a branch padrão, a *issue* é fechada automaticamente; antes disso, marque os critérios de aceite cumpridos.
4. **Versão.** Marque a *tag* (`vX.Y.Z`) no commit resultante da `main` e publique o *release*.
5. **Volta para a `develop`.** Abra um *pull request* da `main` para a `develop` e mescle-o por *merge commit*, para que a correção não se perca na próxima versão e as duas branches não divirjam. Se houver conflito com o trabalho em andamento, resolva-o nesse *pull request*.

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
python -m unittest discover -s services/access_point_service/tests

# analysis_service (constrói e sobe um contêiner, requer Docker; inclui os testes em C da base das metaheurísticas)
python -m unittest discover -s services/analysis_service/tests

# frontend_service (requer as dependências do serviço; os outros serviços são simulados, sem Docker, rede nem navegador)
python -m unittest discover -s services/frontend_service/tests
```

Para rodar um único arquivo, informe o caminho, por exemplo `python -m unittest services/frontend_service/tests/test_routes.py`.

### Testes da interface no navegador

Os testes em `services/frontend_service/browser_tests/` abrem as páginas no Chrome headless, pelo protocolo DevTools, com os serviços do `docker compose` no ar. Eles conferem que nenhuma página gera erro de JavaScript, os fluxos principais (os modais da infraestrutura, gerar uma topologia até a revisão, executar uma estratégia na Análise até o resumo e abrir o teste de escalabilidade), o contraste AA do texto visível a 1280 e 600 px e a ausência de rolagem horizontal a 600 px. As requisições que gravariam dados (POST, PUT e DELETE fora das rotas de análise e da geração de topologia) são bloqueadas no navegador, então os testes não alteram o banco.

```bash
pip install -r services/frontend_service/requirements-dev.txt   # websocket-client, só para desenvolvimento
docker compose up -d
python -m unittest discover -s services/frontend_service/browser_tests
```

Sem o Chrome, o `websocket-client` ou os serviços no ar, os testes são pulados, com um aviso. O Chrome é procurado nos caminhos padrão; informe outro em `CHROME_PATH`, e outro endereço do frontend em `PTZ_FRONTEND_URL` (padrão `http://localhost:3000`). As dependências de teste ficam em `requirements-dev.txt`, fora da imagem do serviço (o `.dockerignore` exclui os testes).

Antes de abrir um *pull request*, rode os testes dos serviços alterados e inclua testes para o comportamento novo.

## Padrões de Código

- **Python:** siga a PEP 8.
- **C (`analysis_service`):** C11, compilando sem avisos com `-Wall -Wextra`, como no `Dockerfile` do serviço.
- **Comentários e mensagens:** em português.
- **Documentação:** atualize o `README.md`, os arquivos de `docs/` e o README do serviço quando a mudança alterar rotas, parâmetros ou a forma de executar o sistema.
- **Idiomas da documentação:** cada documento existe em inglês, no arquivo original (ex.: `README.md`), e em português, no arquivo com o sufixo `.pt-BR.md` (ex.: `README.pt-BR.md`). Toda mudança na documentação deve ser feita nas duas versões, e os links entre documentos devem apontar para os arquivos do mesmo idioma.
