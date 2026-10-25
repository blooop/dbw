#!/bin/sh
# Initialize the host directories that devcontainer.json bind-mounts.
# This script runs on the HOST before the container is created.
# docker refuses a bind mount whose source does not exist, so a host that has
# never run `gh auth login` could not create the container without this.
# mkdir -p is idempotent - it only creates if missing, won't clobber existing.

mkdir -p "$HOME/.claude" "$HOME/.config/gh"
