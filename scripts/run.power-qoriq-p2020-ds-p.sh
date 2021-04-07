#This script is made to be sourced by the run.sh script. Do not use it alone!

kmem_gen_config_setup(){
  t_data=${1:-}
  t_text=${2:-}
  c_data=${3:-}
  c_text=${4:-}

  sed -e "s/@CORUNNER_DATA@/$c_data/" \
      -e "s/@CORUNNER_TEXT@/$c_text/" \
      -e "s/@TASK_DATA@/$t_data/" \
      -e "s/@TASK_TEXT@/$t_text/" config/mem-place.json > /tmp/mem-place.json
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
  "$RUN_TRACE32_HOOK" "$build_dir/program.elf" "$core" "$out"
}

not_supported() {
  echo "*** $1 is not supported for $PRODUCT" > /dev/stderr
  exit 1
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
  #   Task Core  C0  C1  Local Out                        sram  memplace
  kmem_gen_config_setup '"region": "ddr"' '"region": "ddr"' '"address": 20447232' '"address": 33554432'
  run H    0     OFF OFF OFF   "$TRACES_DIR/c0-off.bin"         ON
  run H    0     OFF ON  OFF   "$TRACES_DIR/c0-on.bin"    1     ON
  run H    1     OFF OFF OFF   "$TRACES_DIR/c1-off.bin"         ON
  run H    1     ON  OFF OFF   "$TRACES_DIR/c1-on.bin"    0     ON
  #sym=""
}

run_Hsram() {
  not_supported "Hsram"
}
