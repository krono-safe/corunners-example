#This script is made to be sourced by the run.sh script. Do not use it alone!

run() {
  task="$1"
  core="$2"
  co_0="$3"
  co_1="$4"
  local_corunners="$5"
  out="$6"
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
  #   Task Core  C0  C1  Local Out
  run G    0     OFF OFF OFF   "$TRACES_DIR/c0-off.bin"
  run G    0     OFF ON  OFF   "$TRACES_DIR/c0-on.bin"
}

run_H() {
  #   Task Core  C0  C1  Local Out
  run H    0     OFF OFF OFF   "$TRACES_DIR/c0-off.bin"
  run H    0     OFF ON  OFF   "$TRACES_DIR/c0-on.bin"
}

run_Hsram() {
  not_supported "Hsram"
}
