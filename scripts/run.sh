#! /usr/bin/env bash

set -e
set -u

###############################################################################
# Collect all input parameters via getopt
###############################################################################

PSYKO="${PSYKO:-}"
RTK_DIR="${RTK:-}"
RUN_TRACE32_HOOK="${HOOK:-}"
KDBV="${KDBV:-}"
TYPE="${TYPE:-}"
PRODUCT="${PRODUCT:-}"
P2020="${P2020:-power-qoriq-p2020-ds-p}"
MPC5777M="${MPC5777M:-power-mpc5777m-evb}"
ROOT=${ROOT:-`pwd`}

usage() {
  echo "Usage: $0 -T H|G|U|flash|flash2|Hsram|Hplaces|cpuPri -P <psyko> -k <rtk_dir> -t <runner> -d <kdbv> -p <$P2020|$MPC5777M> [-h]

  -P <psyko>    Path to the PsyC compiler
  -T H|U|G|flash|flash2|Hsram|Hplaces|cpuPri
                Type of run (required choice)
  -d <kdbv>     Path to the kdbv program
  -k <rtk_dir>  Path to the ASTERIOS RTK
  -t <runner>   Path to the executable to control Trace32
  -p <product>  Target product
  -h            Display this message
Alternatively you can use the following environment variables to set the required arguments:
  PSYKO
  TYPE
  KDBV
  RTK
  HOOK
  PRODUCT
"
}


while getopts "P:k:c:t:d:T:p:h" opt; do
  case $opt in
    h)
      usage
      exit 0
      ;;
    P)
      PSYKO="$OPTARG"
      ;;
    k)
      RTK_DIR="$OPTARG"
      ;;
    t)
      RUN_TRACE32_HOOK="$OPTARG"
      ;;
    d)
      KDBV="$OPTARG"
      ;;
    T)
      TYPE="$OPTARG"
      ;;
    p)
      [ "$OPTARG" != "$P2020" ] && [ "$OPTARG" != "$MPC5777M" ] && \
        echo "Product error: currently, only power-mpc5777m-evb and power-qoriq-p2020-ds are supported"  && exit 1
      PRODUCT="$OPTARG"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
done

if [ -z "$PSYKO" ]; then
  echo "-P <psyko> is required"
  exit 1
elif [ -z "$RTK_DIR" ]; then
  echo "-k <rtk_dir> is required"
  exit 1
elif [ -z "$RUN_TRACE32_HOOK" ]; then
  echo "-t <runner> is required"
  exit 1
elif [ -z "$KDBV" ]; then
  echo "-d <kdbv> is required"
  exit 1
elif [ -z "$PRODUCT" ]; then
  echo "-p <$P2020|$MPC5777M> is required"
fi

source "$(pwd)/scripts/run.$PRODUCT.sh"

TRACES_DIR="$(pwd)/traces/${TYPE}"
BUILD_DIR="$(pwd)/build/${TYPE}"
OUTDIR="$ROOT/out_$PRODUCT"
sym="--symetric"
rm "$TRACES_DIR/times.log" || true

###############################################################################

echo "Make sure you have a Trace32 instance ready"

generate_R() {
  extra_args=
  script="mkdata.py"
  if [ "${TYPE%%.*}" = "places" ] || [ "$TYPE" = "cpuPri" ]; then
    bins="
                  --traces-dir '$TRACES_DIR' \\
    "
    extra_args="
                  --core $2
    "
    script="mkplaces.py"
    ref="$3"
    sym=
  else
    bins="
                  --c0-off '$TRACES_DIR/c0-off.bin' \\
                  --c0-on '$TRACES_DIR/c0-on.bin' \\
                  --c1-off '$TRACES_DIR/c1-off.bin' \\
                  --c1-on '$TRACES_DIR/c1-on.bin' \\
                  --stats \\
    "
    ref="c0-off"
    case "$1" in
      "FLASH")
        extra_args="
                      --c0-on-local '$TRACES_DIR/c0-on-local.bin' \\
                      --c1-on-local '$TRACES_DIR/c1-on-local.bin'
        "
        script="mkcontrol.py"
        ;;
      "H")
        extra_args="
                      --output-json '$TRACES_DIR/$TYPE.json'
        "
        ;;
    esac
  fi
  eval "
  './scripts/$script' \\
        \\$bins \\
        --kdbv '$KDBV' \\
        --kcfg '$BUILD_DIR/$1/$ref/gen/app/partos/0/dbs/task_$1_kcfg.ks' \\
        --kapp '$BUILD_DIR/$1/$ref/gen/app/config/kapp.ks' \\
        --output-dir '$OUTDIR/$TYPE' --task=$1 \\
        --product '$PRODUCT'\\
        --timer '$timer' \\
        $sym \\
        \\$extra_args
  "
   cd "$OUTDIR/$TYPE"
   R --no-save < plot.R
}

if [ "x$TYPE" = x"flash" ]; then
  run_flash
  generate_R "FLASH"
elif [ "x$TYPE" = x"flash2" ]; then
  run_flash2
  generate_R "FLASH"
elif [ "x$TYPE" = x"G" ]; then
  run_G
  generate_R "G"
elif [ "x$TYPE" = x"U" ]; then
  STUBBORN_MAX_MEASURES=512
  run_U
  generate_R "U"
elif [ "x$TYPE" = x"H" ]; then
  run_H
  generate_R "H"
elif [ "x$TYPE" = x"Hsram" ]; then
  STUBBORN_MAX_MEASURES=512
  run_Hsram
  generate_R "H"
elif [ "x${TYPE%%.*}" = x"places" ]; then
  t=${TYPE##*.}
  STUBBORN_MAX_MEASURES=512
  run_places 0 $t
  ref="${t}05-COFF"
  generate_R "$t" 0 $ref
elif [ "x$TYPE" = x"cpuPri" ]; then
  STUBBORN_MAX_MEASURES=512
  run_cpu_pri_H 0
  ref=ref-noc
  generate_R "H" 0 $ref
else
  echo "*** Unknown argument '$TYPE'"
  exit 1
fi
