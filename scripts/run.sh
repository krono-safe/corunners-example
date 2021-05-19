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
GENONLY=${GENONLY:-}

usage() {
  echo "Usage: $0 -T H|G|U|flash|flash2|Hsram|Hplaces|cpuPri -P <psyko> -k <rtk_dir> -t <runner> -d <kdbv> -p <$P2020|$MPC5777M> [-g] [-h]

  -P <psyko>    Path to the PsyC compiler
  -T H|U|G|flash|flash2|Hsram|Hplaces|cpuPri
                Type of run (required choice)
  -d <kdbv>     Path to the kdbv program
  -k <rtk_dir>  Path to the ASTERIOS RTK
  -t <runner>   Path to the executable to control Trace32
  -p <product>  Target product
  -g            Do not run tests, generate results graphs only
  -h            Display this message
Alternatively you can use the following environment variables to set the required arguments:
  PSYKO
  TYPE
  KDBV
  RTK
  HOOK
  PRODUCT
  GENONLY
"
}


while getopts "P:k:c:t:d:T:p:gh" opt; do
  case $opt in
    h)
      usage
      exit 0
      ;;
    g)
      GENONLY=1
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

not_supported() {
  echo "*** $1 is not supported for $PRODUCT" > /dev/stderr
  exit 1
}

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
  cmd='run_flash'
  r_args='FLASH'
elif [ "x$TYPE" = x"flash2" ]; then
  cmd='run_flash2'
  r_args='FLASH'
elif [ "x$TYPE" = x"G" ]; then
  cmd='run_G'
  r_args='G'
elif [ "x$TYPE" = x"U" ]; then
  STUBBORN_MAX_MEASURES=512
  cmd='run_U'
  r_args='U'
elif [ "x$TYPE" = x"H" ]; then
  cmd='run_H'
  r_args='H'
elif [ "x$TYPE" = x"Hsram" ]; then
  STUBBORN_MAX_MEASURES=512
  cmd='run_Hsram'
  r_args='H'
elif [ "x${TYPE%%.*}" = x"places" ]; then
  STUBBORN_MAX_MEASURES=256
  t=${TYPE#*.}
  spec=${t#*.}
  t=${t%.*}
  case $spec in
    "R05")
      #Default value
      #CORUNNER_READ_0="0x20000000"
      #CORUNNER_READ_1="0x20000000"
      ;;
    "R15")
      CORUNNER_READ_0="0x60000000"
      CORUNNER_READ_1="0x60000000"
      ;;
    "LH")
      EEBPCR="03000002"
      export EEBPCR
      ;;
    "HL")
      EEBPCR="03000020"
      export EEBPCR
      ;;
    "S001")
      DDR_SIZE=268435456
      STEP_START=125
      LAST_ADDR=268435456
      step=1073741.824
      ;;
    "S005")
      DDR_SIZE=268435456
      STEP_START=25
      LAST_ADDR=268435456
      step=5368709.12
      ;;
esac

  step=${step:-}
  ref="${t}05-COFF"
  cmd="run_places 0 $t $step"
  r_args="$t 0 $ref"
elif [ "x$TYPE" = x"cpuPri" ]; then
  STUBBORN_MAX_MEASURES=256
  ref="ref-coff"
  cmd="run_cpu_pri_H 0"
  r_args="H 0 $ref"
else
  echo "*** Unknown argument '$TYPE'"
  exit 1
fi

export STUBBORN_MAX_MEASURES
[ -z "$GENONLY" ] && eval "$cmd"
generate_R $r_args
