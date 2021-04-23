#This script is made to be sourced by the run.sh script. Do not use it alone!
timer="75e6"
STUBBORN_MAX_MEASURES=1024

kmem_gen_config_setup(){
  t_place=${1:-}
  c_place=${2:-}

  sed -e "s/@CORUNNER_PLACE@/$c_place/" \
      -e "s/@TASK_PLACE@/$t_place/" \
      -e "s|@KDBV@|$KDBV|" config/mem-place.json > /tmp/mem-place.json
}

activate_caches(){
  for arg in $*; do
    eval "$arg='true'"
    eval "echo \$$arg"
  done
  i0=${i0:-false}
  d0=${d0:-false}
  i1=${i1:-false}
  d1=${d1:-false}

  sed -e "s/@ICACHE0@/$i0/" \
      -e "s/@DCACHE0@/$d0/" \
      -e "s/@ICACHE1@/$i1/" \
      -e "s/@DCACHE1@/$d1/" "config/app.$P2020.hjson" > "/tmp/app.$P2020.hjson"
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
    caches=${9:-}
  else
    memplace=${7:-}
    caches=${8:-}
  fi

  echo "####################################################################"
  export STUBBORN_MAX_MEASURES


#   Compile
  [ ! -d "$build_dir" ] && mkdir -p "$build_dir"
  rm -rf "$build_dir"/*
  if [ "$memplace" = "ON" ]; then
    cp /tmp/mem-place.json "$build_dir"/mem-place.json
    extra_opts="--mem-conf "$build_dir"/mem-place.json $extra_opts"
  fi
  if [ "$caches" = "OFF" ]; then
    activate_caches
  fi
  cp "/tmp/app.$P2020.hjson" "$build_dir"/app.hjson
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
#   And now, call a hook script to control the execution of trace32
#   It shall dump the binary buffer in '$out'.
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
#                       Task               Corunner
  kmem_gen_config_setup "\"address\": $3" "\"address\": $4"
#     Task/Core C0  C1  Local Out  sram  memplace caches
  run $1 $core  $C0 $C1 OFF   "$5" 1     ON       OFF
}


run_flash() {
  not_supported "flash"
}

run_flash2() {
  not_supported "flash2"
}

run_G() {
#     Task Core  C0  C1  Local Out                        sram  memplace
  run G    0     OFF OFF OFF   "$TRACES_DIR/c0-off.bin"
  run G    0     OFF ON  OFF   "$TRACES_DIR/c0-on.bin"    1
  run G    1     OFF OFF OFF   "$TRACES_DIR/c1-off.bin"
  run G    1     ON  OFF OFF   "$TRACES_DIR/c1-on.bin"    0
  #sym=""
}

run_U(){
#     Task Core  C0  C1  Local Out                        sram  memplace
  run U    0     OFF OFF OFF   "$TRACES_DIR/c0-off.bin"
  run U    0     OFF ON  OFF   "$TRACES_DIR/c0-on.bin"    1
  run U    1     OFF OFF OFF   "$TRACES_DIR/c1-off.bin"
  run U    1     ON  OFF OFF   "$TRACES_DIR/c1-on.bin"    0
  #sym=""
}

run_H() {
#                       Task               Corunner
#  kmem_gen_config_setup '"region": "ddr"' '"address": 20447232'
  activate_caches
#     Task Core  C0  C1  Local Out                        sram  memplace
  run H    0     OFF OFF OFF   "$TRACES_DIR/c0-off.bin"         OFF
  run H    0     OFF ON  OFF   "$TRACES_DIR/c0-on.bin"    1     OFF
  activate_caches i0 d0 i1 d1
  run H    0     OFF OFF OFF   "$TRACES_DIR/c1-off.bin"         OFF
  run H    0     OFF ON  OFF   "$TRACES_DIR/c1-on.bin"    1     OFF
  #sym=""
}

run_cpu_pri_H(){
#     Task Core  C0  C1  Local Out                          sram  memplace  caches
  export EEBPCR="01000000"
  run H    $1     OFF OFF OFF   "$TRACES_DIR/ref-noc.bin"   1     OFF       OFF
  export EEBPCR="03000000"
  run H    $1     OFF ON OFF   "$TRACES_DIR/low-low.bin"    1     OFF       OFF
  export EEBPCR="03000001"
  run H    $1     OFF ON OFF   "$TRACES_DIR/low-sec.bin"    1     OFF       OFF
  export EEBPCR="03000002"
  run H    $1     OFF ON OFF   "$TRACES_DIR/low-hight.bin"  1     OFF       OFF
  export EEBPCR="03000003"
  run H    $1     OFF ON OFF   "$TRACES_DIR/low-res.bin"    1     OFF       OFF
  export EEBPCR="03000010"
  run H    $1     OFF ON OFF   "$TRACES_DIR/sec-low.bin"    1     OFF       OFF
  export EEBPCR="03000011"
  run H    $1     OFF ON OFF   "$TRACES_DIR/sec-sec.bin"    1     OFF       OFF
  export EEBPCR="03000012"
  run H    $1     OFF ON OFF   "$TRACES_DIR/sec-hight.bin"  1     OFF       OFF
  export EEBPCR="03000013"
  run H    $1     OFF ON OFF   "$TRACES_DIR/sec-res.bin"    1     OFF       OFF
  export EEBPCR="03000020"
  run H    $1     OFF ON OFF   "$TRACES_DIR/high-low.bin"   1     OFF       OFF
  export EEBPCR="03000021"
  run H    $1     OFF ON OFF   "$TRACES_DIR/high-sec.bin"   1     OFF       OFF
  export EEBPCR="03000022"
  run H    $1     OFF ON OFF   "$TRACES_DIR/high-hight.bin" 1     OFF       OFF
  export EEBPCR="03000023"
  run H    $1     OFF ON OFF   "$TRACES_DIR/high-res.bin"   1     OFF       OFF
  export EEBPCR="03000030"
  run H    $1     OFF ON OFF   "$TRACES_DIR/res-low.bin"    1     OFF       OFF
  export EEBPCR="03000031"
  run H    $1     OFF ON OFF   "$TRACES_DIR/res-sec.bin"    1     OFF       OFF
  export EEBPCR="03000032"
  run H    $1     OFF ON OFF   "$TRACES_DIR/res-hight.bin"  1     OFF       OFF
  export EEBPCR="03000033"
  run H    $1     OFF ON OFF   "$TRACES_DIR/res-res.bin"    1     OFF       OFF
}

run_places_H(){
  t="H"
#         TASK/Core task_addr   cor_addr    Out
  gen_run $t -$1    536870912   0           "$TRACES_DIR/H05-COFF.bin"
  gen_run $t $1     536870912   536870912   "$TRACES_DIR/H05-C05.bin"
  gen_run $t $1     536870912   1073741824  "$TRACES_DIR/H05-C1.bin"
  gen_run $t $1     536870912   1610612736  "$TRACES_DIR/H05-C15.bin"
  gen_run $t $1     536870912   2147083648  "$TRACES_DIR/H05-C2.bin"
  gen_run $t -$1    1073741824  0           "$TRACES_DIR/H1-COFF.bin"
  gen_run $t $1     1073741824  536870912   "$TRACES_DIR/H1-C05.bin"
  gen_run $t $1     1073741824  1073741824  "$TRACES_DIR/H1-C1.bin"
  gen_run $t $1     1073741824  1610612736  "$TRACES_DIR/H1-C15.bin"
  gen_run $t $1     1073741824  2147083648  "$TRACES_DIR/H1-C2.bin"
  gen_run $t -$1    1610612736  0           "$TRACES_DIR/H15-COFF.bin"
  gen_run $t $1     1610612736  536870912   "$TRACES_DIR/H15-C05.bin"
  gen_run $t $1     1610612736  1073741824  "$TRACES_DIR/H15-C1.bin"
  gen_run $t $1     1610612736  1610612736  "$TRACES_DIR/H15-C15.bin"
  gen_run $t $1     1610612736  2147083648  "$TRACES_DIR/H15-C2.bin"
  gen_run $t -$1    2147083648  0           "$TRACES_DIR/H2-COFF.bin"
  gen_run $t $1     2147083648  536870912   "$TRACES_DIR/H2-C05.bin"
  gen_run $t $1     2147083648  1073741824  "$TRACES_DIR/H2-C1.bin"
  gen_run $t $1     2147083648  1610612736  "$TRACES_DIR/H2-C15.bin"
  gen_run $t $1     2147083648  2147083648  "$TRACES_DIR/H2-C2.bin"
}

run_Hsram() {
  not_supported "Hsram"
}
