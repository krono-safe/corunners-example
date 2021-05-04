#This script is made to be sourced by the run.sh script. Do not use it alone!
timer="75e6"
STUBBORN_MAX_MEASURES=1024
CORUNNER_READ_0="0x20000000"
CORUNNER_READ_1="0x20000000"
DDR_SIZE=2147483648
LAST_ADDR=2147083648

bcq(){
  ar=${2:-}
  echo "$1" | bc -q $ar
}

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
  memplace=${7:-}
  caches=${8:-}
  build_dir=$(basename -- "$out")
  build_dir="$BUILD_DIR/${task}/${build_dir%.*}"
  extra_opts=

  if [ "$local_corunners" = "ON" ]; then
    extra_opts="--local-corunners $extra_opts"
  fi
  if [ "$co_0" = "SRAM" ]; then
    extra_opts="--corunner=0,$CORUNNER_READ_0 $extra_opts"
  elif [ "$co_0" = "ON" ]; then
    extra_opts="--corunner=0 $extra_opts"
  fi
  if [ "$co_1" = "SRAM" ]; then
    extra_opts="--corunner=1,$CORUNNER_READ_1 $extra_opts"
  elif [ "$co_1" = "ON" ]; then
    extra_opts="--corunner=1 $extra_opts"
  fi

  echo "####################################################################"


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

#   And now, call a hook script to control the execution of trace32
#   It shall dump the binary buffer in '$out'.
  "$RUN_TRACE32_HOOK" "$build_dir/program.elf" "$core" "$out" "$TRACES_DIR/times.log"
}

wrong_core() {
  echo "*** Only cores 0 and 1 are valid for $PRODUCT, not $1" > /dev/stderr
  exit 1
}

get_co(){
  core=$1
  case $1 in
    "0")
      C0="OFF" C1="SRAM"
      ;;
    "1")
      C0="SRAM" C1="OFF"
      ;;
    "-"*)
      C0="OFF" C1="OFF"
      core=${1#-}
      ;;
    *)
      wrong_core $1
  esac
}

gen_pri(){
  get_co $2
  export EEBPCR="$3"
#     Task/Core C0  C1  Local Out                     memplace caches
  run $1 $core  $C0 $C1 OFF   "$TRACES_DIR/$4.bin"    OFF      OFF
}

gen_place(){
  get_co $2
#                       Task               Corunner
  kmem_gen_config_setup "\"address\": $3" "\"address\": $4"
#     Task/Core C0  C1  Local Out  memplace caches
  run $1 $core  $C0 $C1 OFF   "$5" ON       OFF
}

place_str(){
  frac=$(bcq "scale=$SCALE;a=$2/1024^3;b=$1/1024^3/a;scale=0;b=(b+0.5)/1;scale=$SCALE;a*b" | sed 's/0*$//')
  int=${frac%%.*}
  fl=${frac##*.}
  [ -z "$int" ] && int=0
  printf "$int"
  if [ -n "$fl" ]; then
    printf "$fl"
  fi
}

STEP_START=1
SCALE=3
gen_places(){
  t="$1"
  c="$2"
  step="$3"
  t_pl="${4:-$LAST_ADDR}"

  nb=$(bcq "$DDR_SIZE/$step - 1")
  t_str=$(place_str "$t_pl" "$step")

  [ "$STEP_START" = 1 ] && \
    gen_place "$t" "-$c" "$t_pl" 0 "$TRACES_DIR/$t$t_str-COFF.bin"

  for i in $(seq $STEP_START $nb); do
    place=$(bcq "$i*$step")
    place_round=$(bcq "($place+0.5)/1")
    cor_str=$(place_str "$place" "$step")
    gen_place "$t" "$c" "$t_pl" "$place_round" "$TRACES_DIR/$t$t_str-C$cor_str.bin"
  done

  cor_str=$(place_str "$LAST_ADDR" "$step")
  gen_place "$t" "$c" "$t_pl" "$LAST_ADDR" "$TRACES_DIR/$t$t_str-C$cor_str.bin"
  STEP_START=1
}


run_flash() {
  not_supported "flash"
}

run_flash2() {
  not_supported "flash2"
}

run_G() {
#     Task Core  C0   C1    Local Out                      memplace
  run G    0     OFF  OFF   OFF   "$TRACES_DIR/c0-off.bin" OFF
  run G    0     OFF  SRAM  OFF   "$TRACES_DIR/c0-on.bin"  OFF
  run G    1     OFF  OFF   OFF   "$TRACES_DIR/c1-off.bin" OFF
  run G    1     SRAM OFF   OFF   "$TRACES_DIR/c1-on.bin"  OFF
  #sym=""
}

run_U(){
#     Task Core  C0   C1    Local Out                      memplace
  run U    0     OFF  OFF   OFF   "$TRACES_DIR/c0-off.bin" OFF
  run U    0     OFF  SRAM  OFF   "$TRACES_DIR/c0-on.bin"  OFF
  run U    1     OFF  OFF   OFF   "$TRACES_DIR/c1-off.bin" OFF
  run U    1     SRAM OFF   OFF   "$TRACES_DIR/c1-on.bin"  OFF
  #sym=""
}

run_H() {
#                       Task               Corunner
#  kmem_gen_config_setup '"region": "ddr"' '"address": 20447232'
  activate_caches
#     Task Core  C0   C1    Local Out                      memplace
  run H    0     OFF  OFF   OFF   "$TRACES_DIR/c0-off.bin" OFF
  run H    0     OFF  SRAM  OFF   "$TRACES_DIR/c0-on.bin"  OFF
  activate_caches i0 d0 i1 d1
  run H    1     OFF  OFF   OFF   "$TRACES_DIR/c1-off.bin" OFF
  run H    1     SRAM OFF   OFF   "$TRACES_DIR/c1-on.bin"  OFF
  #sym=""
}

run_cpu_pri_H(){
  t="H"
#         Task/Core EEBPCR      Out
  gen_pri $t -$1    "01000000"  "ref-coff"
  gen_pri $t $1     "03000000"  "low-low"
  gen_pri $t $1     "03000001"  "low-sec"
  gen_pri $t $1     "03000002"  "low-hight"
  gen_pri $t $1     "03000003"  "low-res"
  gen_pri $t $1     "03000010"  "sec-low"
  gen_pri $t $1     "03000011"  "sec-sec"
  gen_pri $t $1     "03000012"  "sec-hight"
  gen_pri $t $1     "03000013"  "sec-res"
  gen_pri $t $1     "03000020"  "high-low"
  gen_pri $t $1     "03000021"  "high-sec"
  gen_pri $t $1     "03000022"  "high-hight"
  gen_pri $t $1     "03000023"  "high-res"
  gen_pri $t $1     "03000030"  "res-low"
  gen_pri $t $1     "03000031"  "res-sec"
  gen_pri $t $1     "03000032"  "res-hight"
  gen_pri $t $1     "03000033"  "res-res"
}

run_places(){
  t="$2"
# For RDB
#  DDR_SIZE=1073741824
#  LAST_ADDR=1053741824
#             TASK/Core co_step     task_addr
#  gen_all     $t $1     26843545.6  536870912
#  gen_all     $t $1     26843545.6
# For DS
  STEP_START=74
  gen_places  $t $1     26843545.6  536870912
  gen_places  $t $1     26843545.6  1073741824
  gen_places  $t $1     26843545.6  1610612736
  gen_places  $t $1     26843545.6
}

run_Hsram() {
  not_supported "Hsram"
}
