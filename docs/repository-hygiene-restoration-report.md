# Repository Hygiene Restoration Report

## 1. Executive Summary

Repository hygiene restoration is complete.

The original warnings were caused by stale generated pytest and test-runtime directories under `tests/.artifacts/tmp` whose ownership and access-control lists belonged to the Codex sandbox security context rather than the normal Windows user account. Git could not inspect these ignored directories and therefore emitted repeated `Permission denied` warnings.

The repository also contained four generated artifact files that had been accidentally committed even though the documented repository policy was to track only `.gitkeep` placeholders under `tests/.artifacts`.

A separate pytest configuration issue used current-working-directory-sensitive paths such as `../tests/.artifacts/...`. This caused artifact locations to vary depending on where pytest was invoked and had previously produced a failed JUnit report under an incorrect nested path.

The remediation completed the following:

* repaired ownership and permissions for the inaccessible generated directories;
* deleted the stale legacy pytest artifact tree;
* removed four generated files from Git tracking;
* simplified the artifact ignore policy;
* standardized pytest cache, temp, report, and log paths relative to the repository root;
* updated backend and smoke test scripts to invoke pytest from the repository root;
* verified both normal and ignored Git status without permission warnings;
* verified the new pytest artifact paths with a safe offline test.

Completion decision: **COMPLETE**.

## 2. Initial State

The initial repository state included repeated permission warnings for generated directories under:

```text
tests/.artifacts/tmp/
tests/.artifacts/tmp/legacy/
```

Affected paths included pytest caches, backend test temp directories, beta dry-run artifacts, deployment-readiness artifacts, observability artifacts, usage-policy artifacts, and Codex-generated diagnostic directories.

Representative affected paths included:

```text
tests/.artifacts/tmp/.pytest_cache/
tests/.artifacts/tmp/legacy/.pytest_cache/
tests/.artifacts/tmp/legacy/.pytest_tmp_codex/
tests/.artifacts/tmp/legacy/.pytest_tmp_codex_diag/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_auth/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_beta_dry_run/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_beta_verify/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_codex/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_codex_batch4/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_codex_focus/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_codex_preflight/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_codex_seed/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_deployment_readiness/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_deployment_readiness_seed/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_full/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_observability/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_observability_full/
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_usage/
```

The initial Git state also contained four generated files that were tracked despite the repository artifact policy:

```text
tests/.artifacts/reports/junit.xml
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_beta_dry_run_7160-moved/test_local_json_vector_store_p0/vectors.json
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_beta_dry_run_8712-moved/test_local_json_vector_store_p0/vectors.json
tests/.artifacts/tmp/legacy/backend_tests_.artifacts_failed_validation/reports/junit.xml
```

Git history showed that these generated files had been committed alongside the intended `.gitkeep` placeholders.

The original `pytest.ini` configuration used:

```text
../tests/.artifacts/...
```

Those paths depended on pytest being launched from a particular working directory and were therefore not stable across direct commands and helper scripts.

## 3. Path Classification

| Path or pattern                                      | Tracked before cleanup? | Classification                                   | Final action                                                                       |
| ---------------------------------------------------- | ----------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------- |
| `tests/.artifacts/.gitkeep`                          | Yes                     | Artifact-layout placeholder                      | Preserved                                                                          |
| `tests/.artifacts/coverage/.gitkeep`                 | Yes                     | Artifact-layout placeholder                      | Preserved                                                                          |
| `tests/.artifacts/logs/.gitkeep`                     | Yes                     | Artifact-layout placeholder                      | Preserved                                                                          |
| `tests/.artifacts/reports/.gitkeep`                  | Yes                     | Artifact-layout placeholder                      | Preserved                                                                          |
| `tests/.artifacts/tmp/.gitkeep`                      | Yes                     | Artifact-layout placeholder                      | Preserved                                                                          |
| `tests/.artifacts/reports/junit.xml`                 | Yes                     | Generated pytest report                          | Staged for removal from Git tracking; regenerated working copy remains ignored     |
| Legacy `vectors.json` files                          | Yes                     | Generated fake vector-store test output          | Staged for removal from Git tracking; stale legacy copies deleted                  |
| Legacy failed-validation `junit.xml`                 | Yes                     | Generated failed pytest report                   | Staged for removal from Git tracking; stale legacy copy deleted                    |
| `tests/.artifacts/tmp/.pytest_cache/`                | No                      | Generated pytest cache                           | Stale inaccessible copy repaired and deleted; current regenerated cache is ignored |
| `tests/.artifacts/tmp/legacy/`                       | Partially               | Generated legacy pytest and deployment artifacts | Ownership and permissions repaired; entire stale tree deleted                      |
| `tests/.artifacts/logs/pytest.log`                   | No                      | Generated pytest log                             | Preserved as ignored runtime output                                                |
| `tests/.artifacts/logs/legacy/`                      | No                      | Generated or locally retained log output         | Preserved as ignored local output                                                  |
| `tests/.artifacts/tmp/pytest-deployment-readiness-*` | No                      | Generated deployment-readiness test temp output  | Preserved as ignored runtime output                                                |
| `docs/litinerary-development-status-report.md`       | No                      | Human-readable project status document           | Preserved as an intentional untracked document                                     |
| `docs/repository-hygiene-restoration-report.md`      | No                      | Human-readable hygiene evidence document         | Updated by this task                                                               |

## 4. Root Cause Analysis

### Confirmed causes

1. **Generated directories had sandbox-owned ACLs**

   The inaccessible directories were owned by:

   ```text
   LOGOS\CodexSandboxOffline
   ```

   Their ACLs granted access to `SYSTEM`, `Administrators`, and owner rights, but did not grant the normal user account sufficient access.

   The parent directories were healthy and granted `LOGOS\syahn` full control. The access issue was confined to generated child directories created under a different security context.

2. **Generated files had been committed**

   Four generated files under `tests/.artifacts` were tracked even though the repository policy stated that generated artifact contents should be ignored and only `.gitkeep` placeholders should remain tracked.

3. **Pytest paths depended on the current working directory**

   The previous `pytest.ini` paths used `../tests/.artifacts/...`. These paths behaved differently depending on whether pytest was launched from the repository root, the backend directory, or another script working directory.

4. **Helper scripts launched pytest from the backend directory**

   `scripts/test_backend.ps1` and `scripts/test_smoke.ps1` changed the current location to `backend` before invoking pytest. This reinforced the dependency on parent-relative artifact paths.

### Contributing factors

* Repeated test and deployment-readiness runs created many differently named temp directories.
* Some test runs were performed through Codex or another sandboxed security context.
* Previous ignore exceptions caused Git to descend into artifact subdirectories while evaluating ignored files.
* Generated runtime evidence was stored in the same tree as tracked placeholder files.

## 5. Changes Made

### `.gitignore`

The previous artifact rules reopened multiple nested directories:

```gitignore
tests/.artifacts/*
!tests/.artifacts/.gitkeep
!tests/.artifacts/logs/
!tests/.artifacts/logs/.gitkeep
!tests/.artifacts/reports/
!tests/.artifacts/reports/.gitkeep
!tests/.artifacts/coverage/
!tests/.artifacts/coverage/.gitkeep
!tests/.artifacts/tmp/
!tests/.artifacts/tmp/.gitkeep
```

They were simplified to:

```gitignore
tests/.artifacts/*
!tests/.artifacts/.gitkeep
```

The existing nested `.gitkeep` files remain tracked because they are already present in Git. Generated files and directories below `tests/.artifacts` remain ignored without requiring Git to enumerate nested temp trees.

### `pytest.ini`

The artifact paths were changed from current-working-directory-sensitive parent paths:

```ini
--basetemp=../tests/.artifacts/tmp/pytest
--junitxml=../tests/.artifacts/reports/junit.xml
log_file = ../tests/.artifacts/logs/pytest.log
```

to repository-root-relative paths:

```ini
--basetemp=tests/.artifacts/tmp/pytest
--junitxml=tests/.artifacts/reports/junit.xml
log_file = tests/.artifacts/logs/pytest.log
```

The pytest cache remains:

```ini
cache_dir = tests/.artifacts/tmp/.pytest_cache
```

### `scripts/test_backend.ps1`

The backend test script now resolves the virtual-environment Python executable explicitly and invokes pytest from the repository root:

```powershell
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "venv\Scripts\python.exe"

Push-Location $root
try {
  & $python -m pytest backend\tests
}
finally {
  Pop-Location
}
```

### `scripts/test_smoke.ps1`

The backend smoke test now runs from the repository root:

```powershell
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "venv\Scripts\python.exe"

Push-Location $root
try {
  & $python -m pytest backend\tests\test_smoke_happy_path.py
}
finally {
  Pop-Location
}
```

The frontend portion of the smoke script was not changed.

### Git index cleanup

The following generated files were removed from Git tracking with `git rm --cached`:

```text
tests/.artifacts/reports/junit.xml
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_beta_dry_run_7160-moved/test_local_json_vector_store_p0/vectors.json
tests/.artifacts/tmp/legacy/backend_.pytest_tmp_beta_dry_run_8712-moved/test_local_json_vector_store_p0/vectors.json
tests/.artifacts/tmp/legacy/backend_tests_.artifacts_failed_validation/reports/junit.xml
```

Their staged deletion is intentional.

The current generated `tests/.artifacts/reports/junit.xml` working copy is ignored and may be regenerated by pytest without returning to Git tracking.

### ACL repair and stale-directory deletion

Administrator PowerShell was used to:

1. inspect ownership and ACLs;
2. take ownership of inaccessible generated directories;
3. grant `LOGOS\syahn` full control over those directories and their contents;
4. return to a normal PowerShell session;
5. delete only confirmed generated pytest and deployment artifact directories.

The ownership repair used narrowly scoped commands equivalent to:

```powershell
takeown /F "<generated-directory>" /R /D Y
icacls "<generated-directory>" /grant "LOGOS\syahn:(OI)(CI)F" /T /C
```

After permissions were repaired, the generated directories were deleted using:

```powershell
Remove-Item "<generated-directory>" -Recurse -Force
```

The complete stale directory was ultimately removed:

```text
tests/.artifacts/tmp/legacy/
```

No application source code, test source, fixtures, documentation, environment files, or retained `.gitkeep` placeholders were deleted.

## 6. Pytest Temporary-Directory Policy

The canonical pytest artifact locations are now:

| Artifact                | Canonical path                       |
| ----------------------- | ------------------------------------ |
| Pytest cache            | `tests/.artifacts/tmp/.pytest_cache` |
| Default pytest basetemp | `tests/.artifacts/tmp/pytest`        |
| JUnit XML               | `tests/.artifacts/reports/junit.xml` |
| Pytest log              | `tests/.artifacts/logs/pytest.log`   |

Policy:

* Backend pytest commands should be launched from the repository root.
* Helper scripts should resolve paths relative to the repository root.
* Generated test output remains below `tests/.artifacts`.
* Generated artifact contents are ignored by Git.
* Only `.gitkeep` placeholders are tracked under `tests/.artifacts`.
* Durable human-readable test and rehearsal evidence belongs under `docs/`, not in generated pytest temp directories.
* Live-provider, paid, destructive, cloud, and production tests must remain opt-in and are not part of routine repository-hygiene verification.

## 7. Verification Results

### Git status verification

The following commands were run after ACL repair and stale-directory deletion:

```powershell
git status --short
git status --ignored --short
```

Both commands completed without permission warnings.

The final plain status contained only intentional changes:

```text
 M .gitignore
 M pytest.ini
 M scripts/test_backend.ps1
 M scripts/test_smoke.ps1
D  tests/.artifacts/reports/junit.xml
D  tests/.artifacts/tmp/legacy/backend_.pytest_tmp_beta_dry_run_7160-moved/test_local_json_vector_store_p0/vectors.json
D  tests/.artifacts/tmp/legacy/backend_.pytest_tmp_beta_dry_run_8712-moved/test_local_json_vector_store_p0/vectors.json
D  tests/.artifacts/tmp/legacy/backend_tests_.artifacts_failed_validation/reports/junit.xml
?? docs/litinerary-development-status-report.md
?? docs/repository-hygiene-restoration-report.md
```

### Tracked artifact verification

The following command was run:

```powershell
git ls-files tests/.artifacts
```

Result:

```text
tests/.artifacts/.gitkeep
tests/.artifacts/coverage/.gitkeep
tests/.artifacts/logs/.gitkeep
tests/.artifacts/reports/.gitkeep
tests/.artifacts/tmp/.gitkeep
```

This confirms that only the intended placeholder files remain tracked under the artifact tree.

### Diff validation

The following commands were run:

```powershell
git diff --check
git diff --cached --check
```

Neither command reported whitespace errors.

Git emitted informational Windows line-ending notices indicating that LF may be replaced by CRLF when Git next writes the modified files. These notices are not repository-hygiene failures.

### Pytest verification

The following safe offline test was run from the repository root:

```powershell
venv\Scripts\python.exe -m pytest backend\tests\test_vector_service.py::test_fake_embedding_generation_is_deterministic
```

Result:

```text
1 passed, 1 warning
```

The run confirmed:

* pytest root directory was the Litinerary repository root;

* pytest loaded `pytest.ini`;

* cache output used:

  ```text
  tests\.artifacts\tmp\.pytest_cache
  ```

* JUnit XML was generated at:

  ```text
  tests\.artifacts\reports\junit.xml
  ```

* generated output was ignored by Git;

* no stale legacy temp directory was recreated;

* no live provider was contacted;

* deterministic fake embedding behavior passed.

The warning was:

```text
StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.
```

This is a dependency deprecation warning and does not invalidate the hygiene verification. It should be addressed separately during dependency maintenance.

### Full Backend Verification

The complete backend test script was run from the repository root:

```powershell
.\scripts\test_backend.ps1
```

Result:

```text
289 passed, 3 skipped, 10 warnings in 33.09s
```

The verification confirmed:

* 292 tests were collected.
* 289 tests passed.
* 3 live-provider tests were skipped as expected.
* No tests failed.
* Pytest used the repository-root configuration and canonical artifact paths.
* No live providers were contacted.

The warnings were dependency and API deprecation warnings:

* Starlette `TestClient` and `httpx` deprecation.
* Deprecated `HTTP_413_REQUEST_ENTITY_TOO_LARGE` constant.

These warnings do not invalidate the test result, but they should be addressed during dependency maintenance.

### Backend and Frontend Smoke Verification

The combined smoke script was run:

```powershell
.\scripts\test_smoke.ps1
```

Results:

```text
Backend smoke: 2 passed, 0 failed, 1 warning
Frontend smoke: 1 test file passed, 1 test passed, 0 failed
```

The smoke suite covered:

* the backend mock/offline happy path;
* frontend itinerary planning;
* generated itinerary display;
* repository detail flow;
* account actions.

No live providers were contacted.

### Full Frontend Verification

The complete frontend verification script was run:

```powershell
.\scripts\test_frontend.ps1
```

Results:

```text
13 test files passed
65 tests passed
0 failed
TypeScript validation passed
Production build passed
```

The Vite production build completed successfully:

```text
97 modules transformed
Build completed in 2.07 seconds
```

Generated frontend build output remained ignored by Git.

### Post-Verification Repository Status

After the backend, smoke, frontend, type-check, and production-build verification completed, the following command was run:

```powershell
git status --short
```

The result contained only the previously reviewed and staged repository-hygiene changes:

```text
M  .gitignore
A  docs/litinerary-development-status-report.md
A  docs/repository-hygiene-restoration-report.md
M  pytest.ini
M  scripts/test_backend.ps1
M  scripts/test_smoke.ps1
D  tests/.artifacts/reports/junit.xml
D  tests/.artifacts/tmp/legacy/backend_.pytest_tmp_beta_dry_run_7160-moved/test_local_json_vector_store_p0/vectors.json
D  tests/.artifacts/tmp/legacy/backend_.pytest_tmp_beta_dry_run_8712-moved/test_local_json_vector_store_p0/vectors.json
D  tests/.artifacts/tmp/legacy/backend_tests_.artifacts_failed_validation/reports/junit.xml
```

No additional tracked files were modified by the verification runs. Generated pytest reports, caches, logs, temporary directories, frontend dependencies, and frontend build output remained ignored.


## 8. Remaining Risks and Follow-Up Work

No manual ACL cleanup remains.

The following items remain as normal follow-up work and do not block repository-hygiene completion:

1. **Review and stage the two documentation files intentionally**

   ```text
   docs/litinerary-development-status-report.md
   docs/repository-hygiene-restoration-report.md
   ```

2. **Review the staged generated-file deletions before committing**

   Confirm that the four staged deletions remain intentional.

3. **Run the full safe local verification suite**

   The repository-hygiene task used one representative offline pytest test. The complete backend and frontend verification suites should be run as the next release-readiness step.

4. **Triage the Starlette/httpx deprecation warning**

   Determine whether the project should upgrade Starlette/FastAPI test dependencies or adopt the replacement package recommended by the installed dependency.

5. **Review ignored runtime output periodically**

   Ignored logs, caches, local databases, frontend dependencies, build output, and deployment-readiness temp directories may remain in the local workspace. They do not affect Git status unless they develop another ownership or ACL problem.

6. **Commit only after reviewing the final diff**

   No commit or push was performed during this task.

## 9. Acceptance Criteria

| Criterion                                                               | Result |
| ----------------------------------------------------------------------- | ------ |
| `git status --short` runs without permission warnings                   | Passed |
| `git status --ignored --short` runs without permission warnings         | Passed |
| Affected artifact paths were classified                                 | Passed |
| No legitimate source, fixture, or retained evidence was lost            | Passed |
| Disposable pytest temp paths are ignored or removed                     | Passed |
| Pytest uses a consistent writable repository-root artifact path         | Passed |
| Safe offline pytest verification passes                                 | Passed |
| Only intended placeholder files remain tracked under `tests/.artifacts` | Passed |
| Remaining Git changes are intentional and documented                    | Passed |
| No live providers were contacted                                        | Passed |

## 10. Completion Decision

**COMPLETE**

The inaccessible sandbox-owned pytest directories were repaired and removed. Both Git status commands now run without permission warnings. Generated artifact files are staged to stop being tracked, only `.gitkeep` placeholders remain tracked under `tests/.artifacts`, root-relative pytest paths are standardized, helper scripts invoke pytest from the repository root, diff checks pass, and a safe offline pytest test successfully generated ignored artifacts in the intended locations.

The repository is ready to proceed to fresh backend and frontend verification.
