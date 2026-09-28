#!/usr/bin/env bash
# Source in a child shell after installing HEASoft and CALDB separately.
: "${BHNS_HEASOFT_PREFIX:?Set BHNS_HEASOFT_PREFIX to the installed HEASoft environment}"
: "${CALDB:?Set CALDB to the official local calibration tree}"
if [[ -n "${BHNS_CONDA_SH:-}" ]]; then
  source "$BHNS_CONDA_SH"
  conda activate "$BHNS_HEASOFT_PREFIX"
elif [[ -z "${HEADAS:-}" ]]; then
  echo 'Activate HEASoft first or set BHNS_CONDA_SH to conda.sh' >&2
  return 1
fi
export CALDB
export CALDBCONFIG="${CALDBCONFIG:-$CALDB/software/tools/caldb.config}"
export CALDBALIAS="${CALDBALIAS:-$CALDB/software/tools/alias_config.fits}"
export HEADASNOQUERY=
export HEADASPROMPT=/dev/null
