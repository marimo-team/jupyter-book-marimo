# Release Process

This project publishes `jupyter-book-marimo` to PyPI from semver tags through
GitHub Actions and PyPI Trusted Publishing.

## Creating a Release

Cut releases from a clean, up-to-date `main` branch:

```sh
./scripts/release.sh patch
```

Use `minor` instead of `patch` for backwards-compatible feature releases.

The script:

- verifies that the checkout is on `main` and clean;
- pulls the latest `origin/main`;
- bumps `version` in `pyproject.toml`;
- runs `make check` and `make book-build`;
- commits `release: X.Y.Z`;
- creates an annotated `X.Y.Z` tag;
- optionally pushes `main` and the tag.

Pushing the tag starts the publish workflow. The workflow builds the package,
uploads the build artifact, publishes with `uv publish`, and creates GitHub
release notes.

## PyPI Setup

Configure PyPI Trusted Publishing for:

- PyPI project: `jupyter-book-marimo`
- GitHub owner: `marimo-team`
- GitHub repository: `jupyter-book-marimo`
- Workflow: `publish.yml`

No PyPI API token is required when Trusted Publishing is configured.

## Version Numbering

Use semantic versioning:

- `MAJOR` for incompatible API changes;
- `MINOR` for backwards-compatible functionality additions;
- `PATCH` for backwards-compatible bug fixes.
