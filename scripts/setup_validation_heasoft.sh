#!/usr/bin/env bash
# NASA-supported isolated Conda installation; does not touch the project Python environment.
set -euo pipefail
BHNS_CONDA="${BHNS_CONDA:-conda}"
: "${BHNS_HEASOFT_PREFIX:?Set an external installation prefix}"
"$BHNS_CONDA" create --prefix "$BHNS_HEASOFT_PREFIX" --override-channels \
  -c https://heasarc.gsfc.nasa.gov/FTP/software/conda/ -c conda-forge heasoft=6.37.1 --yes
printf '%s\n' 'Initialize with conda activate, then run scripts/setup_validation_caldb.py using project Python.'
