# Contributing Guide

**English** | [Português](CONTRIBUTING.pt-BR.md)

## Branches

- **`main`**: default and protected branch. It only receives finished versions and accepts no direct *push*, *force push* or deletion; whoever clones or visits the repository lands on the latest stable version.
- **`develop`**: integration branch. It receives the *pull requests* of the *issues* and accumulates the version in progress.
- ***Issue* branches**: start from `develop` and go back to it.

## Workflow

Every change starts from an *issue* and reaches `develop` through a *pull request*. Issues, commits and pull requests are written in Portuguese.

1. **Issue.** Describe the task with a title in the infinitive (for example, "Implementar ...", "Corrigir ...") and a body with the sections `## Contexto`, `## Objetivo` and `## Critérios de aceite`, the latter as a task list. Assign the *issue* to a version *milestone* and apply the *labels*:
   - type: `feature`, `bug`, `refactor`, `documentation`, `test`, `chore`, `security`, `dependencies` or `technical-debt`;
   - area: `frontend` or `backend`;
   - priority: `priority:high`, `priority:medium` or `priority:low`.
2. **Branch.** Create the *branch* from the *issue* itself, based on `develop`: `gh issue develop <number> --base develop --checkout`. Always give the base, since the default branch is `main`. The name follows the format `<number>-<issue-title>`.
3. **Commits.** Follow [Conventional Commits](https://www.conventionalcommits.org/) in Portuguese, with a short single line and no body:
   ```text
   feat: adiciona estratégia gulosa de atribuição
   fix: corrige consulta de ponto de acesso por identificador
   docs: atualiza guia de instalação
   ```
   Types used: `feat`, `fix`, `refactor`, `docs`, `test` and `chore`.
4. **Pull request.** Open it against `develop`, giving the base (`gh pr create --base develop`), with a title in the present tense describing the result (for example, "Adiciona estratégia gulosa de atribuição") and a body with `Closes #<issue>`, which links the *issue* to the *pull request*. Merging is done by *squash*, which produces a single commit on `develop` with the *pull request* number.
5. **Closing the issue.** GitHub only closes *issues* automatically on merges into the default branch; since *pull requests* go to `develop`, close the *issue* after the merge. Before that, check each acceptance criterion and tick the ones met in the description (`- [ ]` → `- [x]`); a criterion not met stays unticked, with a comment explaining what is missing. Then close it as completed, citing the *pull request*: `gh issue close <number> --reason completed --comment "Concluída no #<pull request>."`.

## Versioning

The project follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`), applied to the public interface: HTTP routes, the format of JSON responses and the way the system is run (`docker-compose.yml`, ports and `.env` variables).

- `PATCH` for fixes that do not change the expected behavior;
- `MINOR` for new backward-compatible features;
- `MAJOR` for changes that break compatibility.

Each version has a *milestone* with the *issues* that make it up. When all of them are completed on `develop`:

1. open a *pull request* from `develop` to `main` and merge it with a *merge commit* (not a *squash*, so the two branches do not diverge and the next version does not repeat the changes already merged);
2. mark the version with a *tag* (`vX.Y.Z`) on the resulting `main` commit;
3. publish a GitHub *release* from the *tag*.

## Development Environment

```bash
cp .env.example .env
docker compose up -d --build --remove-orphans
```

The interface runs at `http://localhost:3000`. On Windows, the services can also be run without Docker Compose with `scripts/management/start-local.ps1` (see [scripts/management/SCRIPTS.md](scripts/management/SCRIPTS.md)).

## Tests

Tests use `unittest` and live in `services/<service>/tests/`.

```bash
# access_point_service (requires the service dependencies installed)
python -m unittest services/access_point_service/tests/test_access_point.py

# analysis_service (builds and starts a container, requires Docker)
python -m unittest services/analysis_service/tests/test_backtracking.py
```

Before opening a *pull request*, run the tests of the changed services and add tests for the new behavior.

## Code Standards

- **Python:** follow PEP 8.
- **C (`analysis_service`):** C11, compiling without warnings with `-Wall -Wextra`, as in the service `Dockerfile`.
- **Comments and messages:** in Portuguese.
- **Documentation:** update `README.md`, the files in `docs/` and the service README when the change affects routes, parameters or the way the system is run.
- **Documentation languages:** each document exists in English, in the original file (e.g. `README.md`), and in Portuguese, in the file with the `.pt-BR.md` suffix (e.g. `README.pt-BR.md`). Every documentation change must be made in both versions, and links between documents must point to files in the same language.
