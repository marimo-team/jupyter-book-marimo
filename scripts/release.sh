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
Usage: ./scripts/release.sh <minor|patch|X.Y.Z>

Creates a release commit and final semver tag. Use an explicit X.Y.Z target for
the first release, major releases, or any release from a prerelease version.
Use patch or minor only when the current version is already a final X.Y.Z version.
Pushing the tag publishes the package to PyPI through GitHub Actions and Trusted
Publishing.
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
    print_error "Pass an explicit final X.Y.Z target when releasing from a prerelease"
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

require_newer_explicit_target() {
  local current="$1"
  local target="$2"

  if [[ ! "$current" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)(.*)$ ]]; then
    print_error "Unsupported current version format: $current"
    exit 1
  fi

  local current_major="${BASH_REMATCH[1]}"
  local current_minor="${BASH_REMATCH[2]}"
  local current_patch="${BASH_REMATCH[3]}"
  local current_suffix="${BASH_REMATCH[4]}"

  if [[ ! "$target" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    print_error "Invalid version target: $target"
    usage
    exit 1
  fi

  local target_major="${BASH_REMATCH[1]}"
  local target_minor="${BASH_REMATCH[2]}"
  local target_patch="${BASH_REMATCH[3]}"

  if ((target_major > current_major)); then
    return
  fi
  if ((target_major == current_major && target_minor > current_minor)); then
    return
  fi
  if ((
    target_major == current_major
    && target_minor == current_minor
    && target_patch > current_patch
  )); then
    return
  fi
  if ((
    target_major == current_major
    && target_minor == current_minor
    && target_patch == current_patch
  )) && [[ -n "$current_suffix" ]]; then
    return
  fi

  print_error "Version target must be greater than current version: $target <= $current"
  exit 1
}

target_version() {
  local version="$1"
  local request="$2"

  case "$request" in
    minor | patch)
      bump_version "$version" "$request"
      ;;
    *)
      if [[ ! "$request" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        print_error "Invalid version target: $request"
        usage
        exit 1
      fi
      require_newer_explicit_target "$version" "$request"
      printf '%s\n' "$request"
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

VERSION_REQUEST="$1"

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
NEW_VERSION="$(target_version "$CURRENT_VERSION" "$VERSION_REQUEST")"

if [[ "$NEW_VERSION" == "$CURRENT_VERSION" ]]; then
  print_error "New version matches current version: $NEW_VERSION"
  exit 1
fi

if git rev-parse -q --verify "refs/tags/$NEW_VERSION" >/dev/null; then
  print_error "Tag already exists: $NEW_VERSION"
  exit 1
fi

cat <<EOF
Release summary:
  Current version: $CURRENT_VERSION
  New version:     $NEW_VERSION
  Request:         $VERSION_REQUEST
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
