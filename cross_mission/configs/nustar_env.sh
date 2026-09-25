#!/usr/bin/env bash
# Activate an author-installed HEASoft/NuSTARDAS environment in a child shell.
if [[ -n "${BHNS_CONDA_SH:-}" ]]; then
  : "${BHNS_HEASOFT_PREFIX:?Set the HEASoft installation prefix}"
  source "$BHNS_CONDA_SH"
  conda activate "$BHNS_HEASOFT_PREFIX"
fi
: "${HEADAS:?Activate HEASoft first or configure BHNS_CONDA_SH/BHNS_HEASOFT_PREFIX}"
: "${PHASE2_CALDB:=${CALDB:-}}"
: "${PHASE2_CALDB:?Set the official NuSTAR CALDB tree}"
: "${PHASE2_PFILES:?Set an isolated PFILES directory for this task}"
export CALDB="$PHASE2_CALDB"
export CALDBCONFIG="${CALDBCONFIG:-$CALDB/software/tools/caldb.config}"
export CALDBALIAS="${CALDBALIAS:-$CALDB/software/tools/alias_config.fits}"
export HEADASNOQUERY=
export HEADASPROMPT=/dev/null
mkdir -p "$PHASE2_PFILES"
export PFILES="$PHASE2_PFILES;$HEADAS/syspfiles"
