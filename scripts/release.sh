#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

print_step() {
  printf '\n==> %s\n\n' "$1"
}

print_error() {
  printf 'ERROR: %s\n' "$1" >&2
}

confirm() {
  local prompt="$1"
  local response
  printf '%s (y/N) ' "$prompt"
  read -r response
  [[ "$response" == "y" ]]
}

usage() {
  cat <<'EOF'
Usage: ./scripts/release.sh <minor|patch>

Creates a release commit and semver tag. Pushing the tag publishes the package
to PyPI through GitHub Actions and Trusted Publishing.
EOF
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    print_error "Missing required command: $1"
    exit 1
  fi
}

current_version() {
  uv version --short
}

write_version() {
  local version="$1"
  uv version --frozen "$version" >/dev/null
}

bump_version() {
  local version="$1"
  local bump="$2"

  if [[ ! "$version" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    print_error "Unsupported version format: $version"
    exit 1
  fi

  local major="${BASH_REMATCH[1]}"
  local minor="${BASH_REMATCH[2]}"
  local patch="${BASH_REMATCH[3]}"

  case "$bump" in
    minor)
      printf '%s.%s.0\n' "$major" "$((minor + 1))"
      ;;
    patch)
      printf '%s.%s.%s\n' "$major" "$minor" "$((patch + 1))"
      ;;
    *)
      print_error "Invalid version bump: $bump"
      usage
      exit 1
      ;;
  esac
}

restore_version_on_failure() {
  local status=$?

  if [[ "$status" -ne 0 && "${VERSION_UPDATED:-0}" == "1" && "${COMMITTED:-0}" == "0" ]]; then
    write_version "$CURRENT_VERSION"
    uv lock
    printf '\nRestored pyproject.toml and uv.lock to %s.\n' "$CURRENT_VERSION"
  fi

  exit "$status"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${1:-}" ]]; then
  usage
  exit 1
fi

BUMP="$1"
if [[ ! "$BUMP" =~ ^(minor|patch)$ ]]; then
  print_error "Invalid version bump: $BUMP"
  usage
  exit 1
fi

require_command git
require_command make
require_command uv

print_step "Checking branch"
BRANCH="$(git branch --show-current)"
if [[ "$BRANCH" != "main" ]]; then
  print_error "Releases must be cut from main. Current branch is $BRANCH"
  exit 1
fi

print_step "Checking working tree"
if [[ -n "$(git status --porcelain)" ]]; then
  print_error "Git working directory is not clean"
  git status --short
  exit 1
fi

print_step "Updating from origin/main"
git fetch origin main --tags
git pull --ff-only origin main

CURRENT_VERSION="$(current_version)"
NEW_VERSION="$(bump_version "$CURRENT_VERSION" "$BUMP")"

if git rev-parse -q --verify "refs/tags/$NEW_VERSION" >/dev/null; then
  print_error "Tag already exists: $NEW_VERSION"
  exit 1
fi

cat <<EOF
Release summary:
  Current version: $CURRENT_VERSION
  New version:     $NEW_VERSION
  Commit:          release: $NEW_VERSION
  Tag:             $NEW_VERSION
  Checks:          make check
EOF

if ! confirm "Proceed with release"; then
  print_error "Release cancelled"
  exit 1
fi

VERSION_UPDATED=0
COMMITTED=0
trap restore_version_on_failure EXIT

print_step "Bumping version"
write_version "$NEW_VERSION"
VERSION_UPDATED=1
uv lock

print_step "Running release checks"
make check

print_step "Committing version"
git add pyproject.toml uv.lock
git commit -m "release: $NEW_VERSION"
COMMITTED=1

print_step "Creating tag"
git tag -a "$NEW_VERSION" -m "release: $NEW_VERSION"

cat <<EOF

Release commit and tag are ready locally.
Push both to publish:

  git push origin main "$NEW_VERSION"
EOF

if confirm "Push release commit and tag now"; then
  git push origin main "$NEW_VERSION"
  printf '\nRelease %s pushed. Watch the publish workflow in GitHub Actions.\n' "$NEW_VERSION"
else
  printf '\nRelease %s remains local and is not published until the tag is pushed.\n' "$NEW_VERSION"
fi
