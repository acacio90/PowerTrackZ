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

The project follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`), applied to the public interface.

The **public interface** is what other programs and scripts use from PowerTrackZ:

- the services' HTTP routes and the fields of the JSON requests and responses, as documented in [`docs/api`](docs/api/README.md), including default values that change the results (such as the optimization criterion or the APs' default radius);
- the way the system is run: `docker-compose.yml`, ports and `.env` variables.

The look and the text of the screens and the text of error messages are not part of it (status codes and response fields are).

| Part | When it goes up | Examples |
|---|---|---|
| `PATCH` | Fixes that change neither the expected behavior nor compatibility | v1.2.1: visual standardization and text review, with no route or field changes |
| `MINOR` | New backward-compatible features: new, optional routes, fields or parameters | v1.3.0: new strategies and a configurable optimization criterion, keeping the current default |
| `MAJOR` | Changes that break compatibility: removing or renaming a route or field, changing a response format or a default value that changes the results | removing the `cor` and `proposed_cor` fields from the analysis response |

**Deprecation.** To rename or replace a field, parameter or route without breaking compatibility, the MINOR version accepts both names and the *release* marks the old one as deprecated; the old name is only removed in the next MAJOR version. That is what happened to `clique_factor`, which is still accepted as an alternative to `min_degree`.

v1.2.0 is a recorded exception: published as a MINOR, it renamed `execution.comparison` fields without keeping the old names and changed default values, and under SemVer it should have been v2.0.0. Published versions are not renumbered; the deviation is noted in the *release* notes.

Each version has a *milestone* with the *issues* that make it up. When all of them are completed on `develop`:

1. open a *pull request* from `develop` to `main` and merge it with a *merge commit* (not a *squash*, so the two branches do not diverge and the next version does not repeat the changes already merged);
2. mark the version with a *tag* (`vX.Y.Z`) on the resulting `main` commit;
3. publish a GitHub *release* from the *tag*.

## Fixing Published Versions (*hotfix*)

A bug found in an already published version is fixed in a PATCH version (for example, v1.3.1 fixes v1.3.0). It can only contain fixes that change neither the expected behavior nor the compatibility: a wrong calculation, an interface error or a dependency with a security flaw. New features and changes to the public interface go to the next MINOR or MAJOR version.

Since `develop` may contain work not yet published, the fix starts from `main`:

1. **Issue.** Open the *issue* in the fix version's *milestone* (for example, `v1.3.1`), creating the *milestone* if needed.
2. **Branch.** Create the *branch* from `main`: `gh issue develop <number> --base main --checkout`.
3. **Pull request.** Open it against `main` (`gh pr create --base main`), with the body `Closes #<issue>`, and merge it by *squash*. Since `main` is the default branch, the *issue* is closed automatically; before that, tick the acceptance criteria that were met.
4. **Version.** Mark the *tag* (`vX.Y.Z`) on the resulting `main` commit and publish the *release*.
5. **Back to `develop`.** Open a *pull request* from `main` to `develop` and merge it with a *merge commit*, so the fix is not lost in the next version and the two branches do not diverge. If it conflicts with the work in progress, resolve the conflict in that *pull request*.

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
python -m unittest discover -s services/access_point_service/tests

# analysis_service (builds and starts a container, requires Docker; includes the C tests of the metaheuristic base)
python -m unittest discover -s services/analysis_service/tests

# frontend_service (requires the service dependencies; the other services are mocked, with no Docker, network or browser)
python -m unittest discover -s services/frontend_service/tests
```

To run a single file, give its path, for example `python -m unittest services/frontend_service/tests/test_routes.py`.

### Browser interface tests

The tests in `services/frontend_service/browser_tests/` open the pages in headless Chrome, through the DevTools protocol, with the `docker compose` services running. They check that no page raises a JavaScript error, the main flows (the infrastructure modals, generating a topology up to the review, running a strategy on the Analysis page up to the summary and opening the scalability test), the AA contrast of the visible text at 1280 and 600 px and the absence of horizontal scrolling at 600 px. Requests that would write data (POST, PUT and DELETE outside the analysis routes and topology generation) are blocked in the browser, so the tests do not change the database.

```bash
pip install -r services/frontend_service/requirements-dev.txt   # websocket-client, development only
docker compose up -d
python -m unittest discover -s services/frontend_service/browser_tests
```

Without Chrome, `websocket-client` or the services running, the tests are skipped with a warning. Chrome is looked up in the default paths; set another one in `CHROME_PATH`, and another frontend address in `PTZ_FRONTEND_URL` (default `http://localhost:3000`). The test dependencies live in `requirements-dev.txt`, outside the service image (`.dockerignore` excludes the tests).

Before opening a *pull request*, run the tests of the changed services and add tests for the new behavior.

## Code Standards

- **Python:** follow PEP 8.
- **C (`analysis_service`):** C11, compiling without warnings with `-Wall -Wextra`, as in the service `Dockerfile`.
- **Comments and messages:** in Portuguese.
- **Documentation:** update `README.md`, the files in `docs/` and the service README when the change affects routes, parameters or the way the system is run.
- **Documentation languages:** each document exists in English, in the original file (e.g. `README.md`), and in Portuguese, in the file with the `.pt-BR.md` suffix (e.g. `README.pt-BR.md`). Every documentation change must be made in both versions, and links between documents must point to files in the same language.
