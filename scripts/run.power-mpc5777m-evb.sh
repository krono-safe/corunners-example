#This script is made to be sourced by the run.sh script. Do not use it alone!

run() {
  task="$1"
  core="$2"
  co_0="$3"
  co_1="$4"
  co_2="$5"
  local_corunners="$6"
  out="$7"
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
  if [ "$co_2" = "ON" ]; then
    extra_opts="--corunner-id=2 $extra_opts"
  fi

  echo "####################################################################"

  # Compile
  rm -rf "$build_dir"
  ./build.py \
    --psyko "$PSYKO" \
    --rtk-dir "$RTK_DIR" \
    --task "$task" \
    --core "$core" \
    --build-dir "$build_dir" \
    --product "$PRODUCT" \
    $extra_opts

  # And now, call a hook script to control the execution of trace32
  # It shall dump the binary buffer in '$out'.
  "$RUN_TRACE32_HOOK" "$build_dir/program.elf" "$core" "$out"
}

run_flash() {
  #   Task  Core C0  C1  C2  Local Out
  run FLASH 1    OFF OFF OFF OFF   "$TRACES_DIR/c0-off.bin"
  run FLASH 1    OFF OFF ON  ON    "$TRACES_DIR/c0-on-local.bin"
  run FLASH 1    OFF OFF ON  OFF   "$TRACES_DIR/c0-on.bin"
  run FLASH 2    OFF OFF OFF OFF   "$TRACES_DIR/c1-off.bin"
  run FLASH 2    OFF ON  OFF ON    "$TRACES_DIR/c1-on-local.bin"
  run FLASH 2    OFF ON  OFF OFF   "$TRACES_DIR/c1-on.bin"
}

run_flash2() {
  #   Task  Core C0  C1  C2  Local Out
  run FLASH 1    OFF OFF OFF OFF   "$TRACES_DIR/c0-off.bin"
  run FLASH 1    ON  OFF ON  ON    "$TRACES_DIR/c0-on-local.bin"
  run FLASH 1    ON  OFF ON  OFF   "$TRACES_DIR/c0-on.bin"
  run FLASH 2    OFF OFF OFF OFF   "$TRACES_DIR/c1-off.bin"
  run FLASH 2    ON  ON  OFF ON    "$TRACES_DIR/c1-on-local.bin"
  run FLASH 2    ON  ON  OFF OFF   "$TRACES_DIR/c1-on.bin"
}

run_G() {
  #   Task Core  C0  C1  C2  Local Out
  run G    1     OFF OFF OFF OFF   "$TRACES_DIR/c0-off.bin"
  run G    1     OFF OFF ON  OFF   "$TRACES_DIR/c0-on.bin"
  run G    2     OFF OFF OFF OFF   "$TRACES_DIR/c1-off.bin"
  run G    2     OFF ON  OFF OFF   "$TRACES_DIR/c1-on.bin"
}

run_H() {
  #   Task Core  C0  C1  C2  Local Out
  run H    1     OFF OFF OFF OFF   "$TRACES_DIR/c0-off.bin"
  run H    1     OFF OFF ON  OFF   "$TRACES_DIR/c0-on.bin"
  run H    2     OFF OFF OFF OFF   "$TRACES_DIR/c1-off.bin"
  run H    2     OFF ON  OFF OFF   "$TRACES_DIR/c1-on.bin"
}

run_Hsram() {
  #   Task Core  C0  C1  C2  Local Out
  run H    1     OFF OFF OFF OFF   "$TRACES_DIR/c0-off.bin"
  run H    1     ON  OFF ON  OFF   "$TRACES_DIR/c0-on.bin"
  run H    2     OFF OFF OFF OFF   "$TRACES_DIR/c1-off.bin"
  run H    2     ON  ON  OFF OFF   "$TRACES_DIR/c1-on.bin"
}
