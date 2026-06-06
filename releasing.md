# Release Process

Releases publish `jupyter-book-marimo` to PyPI from `X.Y.Z` tags. The local release
helper creates the version commit and tag, then `.github/workflows/publish.yml` builds,
publishes, and writes GitHub release notes after the tag is pushed.

## Create a Release

Cut the first final release from a clean `main` branch with an explicit target version:

```sh
./scripts/release.sh 0.1.0
```

After the package is on a final version, use `patch` for a backwards-compatible bug fix:

```sh
./scripts/release.sh patch
```

Use `minor` for a backwards-compatible feature release after a final version exists:

```sh
./scripts/release.sh minor
```

The helper accepts `patch`, `minor`, or an explicit final `X.Y.Z` version. Use an
explicit `X.Y.Z` target for the first release, a major release, or any release from a
prerelease version.

The script:

- verifies that `git`, `make`, and `uv` are available
- verifies that the checkout is on `main` and has no uncommitted changes
- fetches `origin/main` and tags, then fast-forwards `main`
- bumps `pyproject.toml` with `uv version --frozen` and refreshes `uv.lock`
- runs `make check`
- commits `pyproject.toml` and `uv.lock` as `release: X.Y.Z`
- creates an annotated `X.Y.Z` tag
- prompts before pushing `main` and the tag.

If a check fails after the version bump and before the release commit, the script
restores `pyproject.toml` and `uv.lock` to the previous version.

## Local Release Gate

`make check` is the release gate. It runs Python and Deno linting, Python and Deno
tests, the widget bundle build, the package build, and the strict docs build.

The package build leaves the wheel and source distribution in `dist/`. The publish
workflow uploads that directory as the package artifact before publishing it.

## Publish Workflow

Pushing the `X.Y.Z` tag starts `.github/workflows/publish.yml`.

The workflow has three jobs:

- `build`: checks out the tag, installs Python from `.python-version`, runs
  `make check`, and uploads `dist/`
- `publish`: downloads `dist/` and runs `uv publish --trusted-publishing always` in the
  `pypi` environment
- `release-notes`: runs `npx changelogithub@14.0.0` after PyPI publishing succeeds.

When the release helper leaves the release local, publish it with:

```sh
git push origin main X.Y.Z
```

Replace `X.Y.Z` with the tag created by the script.

## PyPI Setup

Configure PyPI Trusted Publishing for:

- PyPI project: `jupyter-book-marimo`
- GitHub owner: `marimo-team`
- GitHub repository: `jupyter-book-marimo`
- Workflow: `publish.yml`
- GitHub environment: `pypi`

No PyPI API token is required when Trusted Publishing is configured.

## Version Numbering

Use semantic versioning:

- `MINOR` for backwards-compatible functionality additions
- `PATCH` for backwards-compatible bug fixes.

The release helper does not compute major or prerelease versions. Pass an explicit final
`X.Y.Z` target for major releases or releases promoted from prerelease versions.
