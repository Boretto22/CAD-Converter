#!/bin/sh
set -eu
# Only this dedicated container data directory is prepared, never a host source directory.
mkdir -p /tmp/engcad/jobs
chown cad:cad /tmp/engcad/jobs
exec gosu cad:cad engcad-web
