# PyPI Publishing

This repository publishes the public package `marcopolo-sdk` to PyPI using
GitHub Actions trusted publishing.

## Recommended model

- Source repository: `immersa-co/marcopolo-python-sdk`
- Distribution name on PyPI: `marcopolo-sdk`
- Import package in user code: `marcopolo`
- Release trigger: publish a GitHub release from a version tag such as
  `v0.1.2`

## One-time PyPI setup

1. Create or log in to the PyPI account that will administer the project.
2. Create a pending trusted publisher for this repository on PyPI.

Use these values:

- PyPI project name: `marcopolo-sdk`
- Owner: `immersa-co`
- Repository name: `marcopolo-python-sdk`
- Workflow filename: `publish-pypi.yml`
- Environment name: `pypi`

If the project does not exist yet on PyPI, create it through the trusted
publisher flow rather than performing a manual first upload.

## GitHub workflow files

- `.github/workflows/package-check.yml`
  Runs lint, builds distributions, and validates metadata on push and PR.
- `.github/workflows/publish-pypi.yml`
  Builds and publishes to PyPI using GitHub OIDC trusted publishing.

## Release process

1. Update the version in `pyproject.toml` and `src/marcopolo/_version.py`.
2. Commit the version change and push it to `main`.
3. Create and push a version tag:

```bash
git tag -a v0.1.2 -m "v0.1.2"
git push origin v0.1.2
```

4. Create a GitHub release for that tag and mark it published.
5. Confirm the `Publish to PyPI` workflow succeeds.
6. Verify the release on PyPI:

```bash
python3 -m pip install --upgrade marcopolo-sdk
python3 - <<'PY'
import marcopolo
print(marcopolo.__version__)
PY
```

## Local validation before release

```bash
python3 -m pip install -e ".[dev]"
python3 -m build
python3 -m twine check dist/*
```

## Notes

- PyPI publishes the distribution name `marcopolo-sdk`, while application code
  imports `marcopolo`.
- The publish workflow does not store a long-lived PyPI API token in GitHub.
- The `pypi` environment can be protected with required reviewers if you want
  human approval before a release is published.
