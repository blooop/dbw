#!/usr/bin/env bash
set -e
cd /tmp

# #rockerc is set up in this repo

echo "Running: dbw blooop/test_dbw \"bash -c 'git status; pwd; ls -l'\"" to confirm that multi step commands work as expected
dbw blooop/test_dbw "bash -c 'git status; pwd; ls -l'"



