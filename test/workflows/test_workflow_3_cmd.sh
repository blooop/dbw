#!/usr/bin/env bash
set -e
cd /tmp

# #rockerc is set up in this repo

echo "Running: dbw launch blooop/test_dbw launch \"bash -c 'git status; pwd; ls -l'\"" to confirm that multi step commands work as expected
dbw launch blooop/test_dbw launch "bash -c 'git status; pwd; ls -l'"



