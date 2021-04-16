#This script is made to be sourced by the run.sh script. Do not use it alone!
timer="75e6"
kmem_gen_config_setup(){
  t_place=${1:-}
  c_place=${2:-}

  sed -e "s/@CORUNNER_PLACE@/$c_place/" \
      -e "s/@TASK_PLACE@/$t_place/" \
      -e "s|@KDBV@|$KDBV|" config/mem-place.json > /tmp/mem-place.json
}

run() {
  task="$1"
  core="$2"
  co_0="$3"
  co_1="$4"
  local_corunners="$5"
  out="$6"
  sram="${7:-}"
  build_dir=$(basename -- "$out")
  build_dir="$BUILD_DIR/${task}/${build_dir%.*}"
  extra_opts=

  if [ "$local_corunners" = "ON" ]; then
    extra_opts="--local-corunners $extra_opts"
  fi
  if [ "$co_0" = "ON" ]; then
    extra_opts="--corunner-id=0 $extra_opts"
  fi
  if [ "$co_1" = "ON" ]; then
    extra_opts="--corunner-id=1 $extra_opts"
  fi
  if [ -n "$sram" ]; then
    for c in $sram; do
      extra_opts="--use-sram=$c $extra_opts"
    done
    memplace=${8:-}
  else
    memplace=${7:-}
  fi

  echo "####################################################################"

  # Compile
  [ ! -d "$build_dir" ] && mkdir "$build_dir"
  rm -rf "$build_dir"/*
  if [ "$memplace" = "ON" ]; then
    cp /tmp/mem-place.json "$build_dir"/mem-place.json
    extra_opts="--mem-conf "$build_dir"/mem-place.json $extra_opts"
  fi
  ./build.py \
    --psyko "$PSYKO" \
    --kdbv "$KDBV" \
    --rtk-dir "$RTK_DIR" \
    --task "$task" \
    --core "$core" \
    --build-dir "$build_dir" \
    --product "$PRODUCT" \
    $extra_opts

  #return
  # And now, call a hook script to control the execution of trace32
  # It shall dump the binary buffer in '$out'.
  "$RUN_TRACE32_HOOK" "$build_dir/program.elf" "$core" "$out" "$TRACES_DIR/times.log"
}

not_supported() {
  echo "*** $1 is not supported for $PRODUCT" > /dev/stderr
  exit 1
}

wrong_core() {
  echo "*** Only cores 0 and 1 are valid for $PRODUCT, not $1" > /dev/stderr
  exit 1
}

gen_run(){
  case $2 in
    "0")
      C0="OFF" C1="ON"
      core=$2
      ;;
    "1")
      C0="ON" C1="OFF"
      core=$2
      ;;
    "-"*)
      C0="OFF" C1="OFF"
      core=$((-$2))
      ;;
    *)
      wrong_core $2
  esac
  #                     Task               Corunner
  kmem_gen_config_setup "\"address\": $3" "\"address\": $4"
  #   Task/Core C0  C1  Local Out  sram  memplace
  run $1 $core  $C0 $C1 OFF   "$5" 1     ON
}


run_flash() {
  not_supported "flash"
}

run_flash2() {
  not_supported "flash2"
}

run_G() {
  #   Task Core  C0  C1  Local Out                        sram  memplace
  run G    0     OFF OFF OFF   "$TRACES_DIR/c0-off.bin"
  run G    0     OFF ON  OFF   "$TRACES_DIR/c0-on.bin"    1
  run G    1     OFF OFF OFF   "$TRACES_DIR/c1-off.bin"
  run G    1     ON  OFF OFF   "$TRACES_DIR/c1-on.bin"    0
  #sym=""
}

run_H() {
  #                     Task               Corunner
  kmem_gen_config_setup '"region": "ddr"' '"address": 20447232'
  #   Task Core  C0  C1  Local Out                        sram  memplace
  run H    0     OFF OFF OFF   "$TRACES_DIR/c0-off.bin"         ON
  run H    0     OFF ON  OFF   "$TRACES_DIR/c0-on.bin"    1     ON
  run H    1     OFF OFF OFF   "$TRACES_DIR/c1-off.bin"         ON
  run H    1     ON  OFF OFF   "$TRACES_DIR/c1-on.bin"    0     ON
  #sym=""
}



run_places_H(){
  #TRACES_DIR="$TRACES_DIR/Hplaces"

  #       TASK/Core task_addr   cor_addr    Out
  gen_run H -$1     536870912   0           "$TRACES_DIR/H05-COFF.bin"
  gen_run H $1      536870912   536870912   "$TRACES_DIR/H05-C05.bin"
  gen_run H $1      536870912   1073741824  "$TRACES_DIR/H05-C1.bin"
  gen_run H $1      536870912   1610612736  "$TRACES_DIR/H05-C15.bin"
  gen_run H $1      536870912   2147083648  "$TRACES_DIR/H05-C2.bin"
  gen_run H -$1     1073741824  0           "$TRACES_DIR/H1-COFF.bin"
  gen_run H $1      1073741824  536870912   "$TRACES_DIR/H1-C05.bin"
  gen_run H $1      1073741824  1073741824  "$TRACES_DIR/H1-C1.bin"
  gen_run H $1      1073741824  1610612736  "$TRACES_DIR/H1-C15.bin"
  gen_run H $1      1073741824  2147083648  "$TRACES_DIR/H1-C2.bin"
  gen_run H -$1     1610612736  0           "$TRACES_DIR/H15-COFF.bin"
  gen_run H $1      1610612736  536870912   "$TRACES_DIR/H15-C05.bin"
  gen_run H $1      1610612736  1073741824  "$TRACES_DIR/H15-C1.bin"
  gen_run H $1      1610612736  1610612736  "$TRACES_DIR/H15-C15.bin"
  gen_run H $1      1610612736  2147083648  "$TRACES_DIR/H15-C2.bin"
  gen_run H -$1     2147083648  0           "$TRACES_DIR/H2-COFF.bin"
  gen_run H $1      2147083648  536870912   "$TRACES_DIR/H2-C05.bin"
  gen_run H $1      2147083648  1073741824  "$TRACES_DIR/H2-C1.bin"
  gen_run H $1      2147083648  1610612736  "$TRACES_DIR/H2-C15.bin"
  gen_run H $1      2147083648  2147083648  "$TRACES_DIR/H2-C2.bin"
}

run_Hsram() {
  not_supported "Hsram"
}
