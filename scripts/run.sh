#! /usr/bin/env bash

set -e
set -u

###############################################################################
# Collect all input parameters via getopt
###############################################################################

PSYKO=
RTK_DIR=
CMM=
RUN_TRACE32_HOOK=
KDBV=
TYPE=

usage() {
  echo "Usage: $0 -T H|G|flash -p <psyko> -k <rtk_dir> -t <runner> -d <kdbv> [-h]

  -p <psyko>    Path to the PsyC compiler
  -T H|G|flash  Type of run (required choice)
  -d <kdbv>     Path to the kdbv program
  -k <rtk_dir>  Path to the ASTERIOS RTK
  -t <runner>   Path to the executable to control Trace32
  -h            Display this message
"
}


while getopts "p:k:c:t:d:T:h" opt; do
  case $opt in
    h)
      usage
      exit 0
      ;;
    p)
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
    *)
      usage
      exit 1
      ;;
  esac
done

if [ -z "$PSYKO" ]; then
  echo "-p <psyko> is required"
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
fi

TRACES_DIR="$(pwd)/traces"
OUTDIR=out

###############################################################################

echo "Make sure you have a Trace32 instance ready"

run() {
  task="$1"
  core="$2"
  co_1="$3"
  co_2="$4"
  local_corunners="$5"
  out="$6"
  build_dir=$(basename -- "$out")
  build_dir="$(pwd)/build/${task}/${build_dir%.*}"
  extra_opts=
  if [ "$local_corunners" = "ON" ]; then
    extra_opts="--local-corunners $extra_opts"
  fi
  if [ "$co_1" = "ON" ]; then
    extra_opts="--corunner-id=1 $extra_opts"
  fi
  if [ "$co_2" = "ON" ]; then
    extra_opts="--corunner-id=2 $extra_opts"
  fi

  # Compile
  rm -rf "$build_dir"
  ./build.py \
    --psyko "$PSYKO" \
    --rtk-dir "$RTK_DIR" \
    --task "$task" \
    --core "$core" \
    --build-dir "$build_dir" \
    $extra_opts

  # And now, call a hook script to control the execution of trace32
  # It shall dump the binary buffer in '$out'.
  "$RUN_TRACE32_HOOK" "$build_dir/program.elf" "$core" "$out"
}



if [ "x$TYPE" = x"flash" ]; then
  #   Task  Core C0  C1  Local
  run FLASH 1    OFF OFF OFF "$TRACES_DIR/flash/c0-off.bin"
  run FLASH 2    OFF OFF OFF "$TRACES_DIR/flash/c1-off.bin"
  run FLASH 1    OFF ON  ON  "$TRACES_DIR/flash/c0-on-local.bin"
  run FLASH 2    ON  OFF ON  "$TRACES_DIR/flash/c1-on-local.bin"
  run FLASH 1    OFF ON  OFF "$TRACES_DIR/flash/c0-on.bin"
  run FLASH 2    ON  OFF OFF "$TRACES_DIR/flash/c1-on.bin"

  echo "
  ========= To generate the images ==========
  '$(pwd)/scripts/mkcontrol.py' \
                  --c0-off '$TRACES_DIR/flash/c0-off.bin' \
                  --c0-on-local '$TRACES_DIR/flash/c0-on-local.bin' \
                  --c0-on '$TRACES_DIR/flash/c0-on.bin' \
                  --c1-off '$TRACES_DIR/flash/c1-off.bin' \
                  --c1-on-local '$TRACES_DIR/flash/c1-on-local.bin' \
                  --c1-on '$TRACES_DIR/flash/c1-on.bin' \
                  --kdbv '$KDBV' \
                  --kcfg '$(pwd)/build/FLASH/c0-off/gen/app/partos/0/dbs/task_FLASH_kcfg.ks' \
                  --kapp '$(pwd)/build/FLASH/c0-off/gen/app/config/kapp.ks' \
                  --output-dir '$OUTDIR/flash' --task=FLASH --stats
   cd '$OUTDIR/flash'
   R --no-save < plot.R
  ===========================================
  "
elif [ "x$TYPE" = x"G" ]; then
  #   Task Core C1  C2  Local
  run G    1    OFF OFF OFF "$TRACES_DIR/task_G/c0-off.bin"
  run G    1    OFF ON  OFF "$TRACES_DIR/task_G/c0-on.bin"
  run G    2    OFF OFF OFF "$TRACES_DIR/task_G/c1-off.bin"
  run G    2    ON  OFF OFF "$TRACES_DIR/task_G/c1-on.bin"

  echo "
  ========= To generate the images ==========
   '$(pwd)/scripts/mkdata.py' \
                  --c0-off '$TRACES_DIR/task_G/c0-off.bin' \
                  --c0-on '$TRACES_DIR/task_G/c0-on.bin' \
                  --c1-off '$TRACES_DIR/task_G/c1-off.bin' \
                  --c1-on '$TRACES_DIR/task_G/c1-on.bin' \
                  --kdbv '$KDBV' \
                  --kcfg '$(pwd)/build/G/c0-off/gen/app/partos/0/dbs/task_G_kcfg.ks' \
                  --kapp '$(pwd)/build/G/c0-off/gen/app/config/kapp.ks' \
                  --output-dir '$OUTDIR/G' --task=G --stats
   cd '$OUTDIR/G'
   R --no-save < plot.R
  ===========================================
  "
elif [ "x$TYPE" = x"H" ]; then
  #   Task Core C1  C2  Local
  run H    1    OFF OFF OFF "$TRACES_DIR/task_H/c0-off.bin"
  run H    1    OFF ON  OFF "$TRACES_DIR/task_H/c0-on.bin"
  run H    2    OFF OFF OFF "$TRACES_DIR/task_H/c1-off.bin"
  run H    2    ON  OFF OFF "$TRACES_DIR/task_H/c1-on.bin"

  echo "
  ========= To generate the images ==========
   '$(pwd)/scripts/mkdata.py' \
                  --c0-off '$TRACES_DIR/task_H/c0-off.bin' \
                  --c0-on '$TRACES_DIR/task_H/c0-on.bin' \
                  --c1-off '$TRACES_DIR/task_H/c1-off.bin' \
                  --c1-on '$TRACES_DIR/task_H/c1-on.bin' \
                  --kdbv '$KDBV' \
                  --kcfg '$(pwd)/build/H/c0-off/gen/app/partos/0/dbs/task_H_kcfg.ks' \
                  --kapp '$(pwd)/build/H/c0-off/gen/app/config/kapp.ks' \
                  --output-dir '$OUTDIR/H' --task=H --stats
   cd '$OUTDIR/H'
   R --no-save < plot.R
  ===========================================
  "
else
  echo "*** Unknown argument '$TYPE'"
  exit 1
fi
