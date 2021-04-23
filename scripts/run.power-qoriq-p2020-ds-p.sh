#This script is made to be sourced by the run.sh script. Do not use it alone!
timer="75e6"
STUBBORN_MAX_MEASURES=1024
CORUNNER_READ_0="0x20000000"
CORUNNER_READ_1="0x20000000"

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
      C0="OFF" C1="SRAM"
      core=$2
      ;;
    "1")
      C0="SRAM" C1="OFF"
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
#     Task/Core C0  C1  Local Out  memplace caches
  run $1 $core  $C0 $C1 OFF   "$5" ON       OFF
}


run_flash() {
  not_supported "flash"
}

run_flash2() {
  not_supported "flash2"
}

run_G() {
#     Task Core  C0   C1    Local Out                      memplace
  run G    0     OFF  OFF   OFF   "$TRACES_DIR/c0-off.bin"
  run G    0     OFF  SRAM  OFF   "$TRACES_DIR/c0-on.bin"
  run G    1     OFF  OFF   OFF   "$TRACES_DIR/c1-off.bin"
  run G    1     SRAM OFF   OFF   "$TRACES_DIR/c1-on.bin"
  #sym=""
}

run_U(){
#     Task Core  C0   C1    Local Out                      memplace
  run U    0     OFF  OFF   OFF   "$TRACES_DIR/c0-off.bin"
  run U    0     OFF  SRAM  OFF   "$TRACES_DIR/c0-on.bin"
  run U    1     OFF  OFF   OFF   "$TRACES_DIR/c1-off.bin"
  run U    1     SRAM OFF   OFF   "$TRACES_DIR/c1-on.bin"
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
#     Task Core  C0  C1     Local Out                          memplace  caches
  export EEBPCR="01000000"
  run H    $1     OFF OFF   OFF   "$TRACES_DIR/ref-noc.bin"    OFF       OFF
  export EEBPCR="03000000"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/low-low.bin"    OFF       OFF
  export EEBPCR="03000001"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/low-sec.bin"    OFF       OFF
  export EEBPCR="03000002"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/low-hight.bin"  OFF       OFF
  export EEBPCR="03000003"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/low-res.bin"    OFF       OFF
  export EEBPCR="03000010"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/sec-low.bin"    OFF       OFF
  export EEBPCR="03000011"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/sec-sec.bin"    OFF       OFF
  export EEBPCR="03000012"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/sec-hight.bin"  OFF       OFF
  export EEBPCR="03000013"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/sec-res.bin"    OFF       OFF
  export EEBPCR="03000020"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/high-low.bin"   OFF       OFF
  export EEBPCR="03000021"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/high-sec.bin"   OFF       OFF
  export EEBPCR="03000022"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/high-hight.bin" OFF       OFF
  export EEBPCR="03000023"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/high-res.bin"   OFF       OFF
  export EEBPCR="03000030"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/res-low.bin"    OFF       OFF
  export EEBPCR="03000031"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/res-sec.bin"    OFF       OFF
  export EEBPCR="03000032"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/res-hight.bin"  OFF       OFF
  export EEBPCR="03000033"
  run H    $1     OFF SRAM  OFF   "$TRACES_DIR/res-res.bin"    OFF       OFF
}

run_places_H(){
  t="H"
#         TASK/Core task_addr   cor_addr    Out
#  gen_run $t -$1    536870912   0           "$TRACES_DIR/H05-COFF.bin"
#  gen_run $t $1     536870912   536870912   "$TRACES_DIR/H05-C05.bin"
#  gen_run $t $1     536870912   1073741824  "$TRACES_DIR/H05-C1.bin"
#  gen_run $t $1     536870912   1610612736  "$TRACES_DIR/H05-C15.bin"
#  gen_run $t $1     536870912   2147083648  "$TRACES_DIR/H05-C2.bin"
#  gen_run $t -$1    1073741824  0           "$TRACES_DIR/H1-COFF.bin"
#  gen_run $t $1     1073741824  26843545    "$TRACES_DIR/H1-C0025.bin"
#  gen_run $t $1     1073741824  53687091    "$TRACES_DIR/H1-C005.bin"
#  gen_run $t $1     1073741824  80530637    "$TRACES_DIR/H1-C0075.bin"
#  gen_run $t $1     1073741824  107374182   "$TRACES_DIR/H1-C01.bin"
#  gen_run $t $1     1073741824  134217728   "$TRACES_DIR/H1-C0125.bin"
#  gen_run $t $1     1073741824  161061274   "$TRACES_DIR/H1-C015.bin"
#  gen_run $t $1     1073741824  187904819   "$TRACES_DIR/H1-C0175.bin"
#  gen_run $t $1     1073741824  214748365   "$TRACES_DIR/H1-C02.bin"
#  gen_run $t $1     1073741824  241591910   "$TRACES_DIR/H1-C0225.bin"
#  gen_run $t $1     1073741824  268435456   "$TRACES_DIR/H1-C025.bin"
#  gen_run $t $1     1073741824  295279002   "$TRACES_DIR/H1-C0275.bin"
#  gen_run $t $1     1073741824  322122547   "$TRACES_DIR/H1-C03.bin"
#  gen_run $t $1     1073741824  348966093   "$TRACES_DIR/H1-C0325.bin"
#  gen_run $t $1     1073741824  375809638   "$TRACES_DIR/H1-C035.bin"
#  gen_run $t $1     1073741824  402653184   "$TRACES_DIR/H1-C0375.bin"
#  gen_run $t $1     1073741824  429496730   "$TRACES_DIR/H1-C04.bin"
#  gen_run $t $1     1073741824  456340275   "$TRACES_DIR/H1-C0425.bin"
#  gen_run $t $1     1073741824  483183821   "$TRACES_DIR/H1-C045.bin"
#  gen_run $t $1     1073741824  510027366   "$TRACES_DIR/H1-C0475.bin"
#  gen_run $t $1     1073741824  536870912   "$TRACES_DIR/H1-C05.bin"
#  gen_run $t $1     1073741824  563714458   "$TRACES_DIR/H1-C0525.bin"
#  gen_run $t $1     1073741824  590558003   "$TRACES_DIR/H1-C055.bin"
#  gen_run $t $1     1073741824  617401549   "$TRACES_DIR/H1-C0575.bin"
#  gen_run $t $1     1073741824  644245094   "$TRACES_DIR/H1-C06.bin"
#  gen_run $t $1     1073741824  671088640   "$TRACES_DIR/H1-C0625.bin"
#  gen_run $t $1     1073741824  697932186   "$TRACES_DIR/H1-C065.bin"
#  gen_run $t $1     1073741824  724775731   "$TRACES_DIR/H1-C0675.bin"
#  gen_run $t $1     1073741824  751619277   "$TRACES_DIR/H1-C07.bin"
#  gen_run $t $1     1073741824  778462822   "$TRACES_DIR/H1-C0725.bin"
#  gen_run $t $1     1073741824  805306368   "$TRACES_DIR/H1-C075.bin"
#  gen_run $t $1     1073741824  832149914   "$TRACES_DIR/H1-C0775.bin"
#  gen_run $t $1     1073741824  858993459   "$TRACES_DIR/H1-C08.bin"
#  gen_run $t $1     1073741824  885837005   "$TRACES_DIR/H1-C0825.bin"
#  gen_run $t $1     1073741824  912680550   "$TRACES_DIR/H1-C085.bin"
#  gen_run $t $1     1073741824  939524096   "$TRACES_DIR/H1-C0875.bin"
#  gen_run $t $1     1073741824  966367642   "$TRACES_DIR/H1-C09.bin"
#  gen_run $t $1     1073741824  993211187   "$TRACES_DIR/H1-C0925.bin"
#  gen_run $t $1     1073741824  1020054733  "$TRACES_DIR/H1-C095.bin"
#  gen_run $t $1     1073741824  1046898278  "$TRACES_DIR/H1-C0975.bin"
#  gen_run $t $1     1073741824  1073741824  "$TRACES_DIR/H1-C1.bin"
#  gen_run $t $1     1073741824  1100585370  "$TRACES_DIR/H1-C1025.bin"
#  gen_run $t $1     1073741824  1127428915  "$TRACES_DIR/H1-C105.bin"
#  gen_run $t $1     1073741824  1154272461  "$TRACES_DIR/H1-C1075.bin"
#  gen_run $t $1     1073741824  1181116006  "$TRACES_DIR/H1-C11.bin"
#  gen_run $t $1     1073741824  1207959552  "$TRACES_DIR/H1-C1125.bin"
#  gen_run $t $1     1073741824  1234803098  "$TRACES_DIR/H1-C115.bin"
#  gen_run $t $1     1073741824  1261646643  "$TRACES_DIR/H1-C1175.bin"
#  gen_run $t $1     1073741824  1288490189  "$TRACES_DIR/H1-C12.bin"
#  gen_run $t $1     1073741824  1315333734  "$TRACES_DIR/H1-C1225.bin"
#  gen_run $t $1     1073741824  1342177280  "$TRACES_DIR/H1-C125.bin"
#  gen_run $t $1     1073741824  1369020826  "$TRACES_DIR/H1-C1275.bin"
#  gen_run $t $1     1073741824  1395864371  "$TRACES_DIR/H1-C13.bin"
#  gen_run $t $1     1073741824  1422707917  "$TRACES_DIR/H1-C1325.bin"
#  gen_run $t $1     1073741824  1449551462  "$TRACES_DIR/H1-C135.bin"
#  gen_run $t $1     1073741824  1476395008  "$TRACES_DIR/H1-C1375.bin"
#  gen_run $t $1     1073741824  1503238554  "$TRACES_DIR/H1-C14.bin"
#  gen_run $t $1     1073741824  1530082099  "$TRACES_DIR/H1-C1425.bin"
#  gen_run $t $1     1073741824  1556925645  "$TRACES_DIR/H1-C145.bin"
#  gen_run $t $1     1073741824  1583769190  "$TRACES_DIR/H1-C1475.bin"
#  gen_run $t $1     1073741824  1610612736  "$TRACES_DIR/H1-C15.bin"
#  gen_run $t $1     1073741824  1637456282  "$TRACES_DIR/H1-C1525.bin"
#  gen_run $t $1     1073741824  1664299827  "$TRACES_DIR/H1-C155.bin"
#  gen_run $t $1     1073741824  1691143373  "$TRACES_DIR/H1-C1575.bin"
#  gen_run $t $1     1073741824  1717986918  "$TRACES_DIR/H1-C16.bin"
#  gen_run $t $1     1073741824  1744830464  "$TRACES_DIR/H1-C1625.bin"
#  gen_run $t $1     1073741824  1771674010  "$TRACES_DIR/H1-C165.bin"
#  gen_run $t $1     1073741824  1798517555  "$TRACES_DIR/H1-C1675.bin"
#  gen_run $t $1     1073741824  1825361101  "$TRACES_DIR/H1-C17.bin"
#  gen_run $t $1     1073741824  1852204646  "$TRACES_DIR/H1-C1725.bin"
#  gen_run $t $1     1073741824  1879048192  "$TRACES_DIR/H1-C175.bin"
#  gen_run $t $1     1073741824  1905891738  "$TRACES_DIR/H1-C1775.bin"
#  gen_run $t $1     1073741824  1932735283  "$TRACES_DIR/H1-C18.bin"
#  gen_run $t $1     1073741824  1959578829  "$TRACES_DIR/H1-C1825.bin"
#  gen_run $t $1     1073741824  1986422374  "$TRACES_DIR/H1-C185.bin"
#  gen_run $t $1     1073741824  2013265920  "$TRACES_DIR/H1-C1875.bin"
#  gen_run $t $1     1073741824  2040109466  "$TRACES_DIR/H1-C19.bin"
#  gen_run $t $1     1073741824  2066953011  "$TRACES_DIR/H1-C1925.bin"
#  gen_run $t $1     1073741824  2093796557  "$TRACES_DIR/H1-C195.bin"
#  gen_run $t $1     1073741824  2120640102  "$TRACES_DIR/H1-C1975.bin"
#  gen_run $t $1     1073741824  2147083648  "$TRACES_DIR/H1-C2.bin"
#  gen_run $t -$1    1610612736  0           "$TRACES_DIR/H15-COFF.bin"
#  gen_run $t $1     1610612736  536870912   "$TRACES_DIR/H15-C05.bin"
#  gen_run $t $1     1610612736  1073741824  "$TRACES_DIR/H15-C1.bin"
#  gen_run $t $1     1610612736  1610612736  "$TRACES_DIR/H15-C15.bin"
#  gen_run $t $1     1610612736  2147083648  "$TRACES_DIR/H15-C2.bin"
#  gen_run $t -$1    2147083648  0           "$TRACES_DIR/H2-COFF.bin"
#  gen_run $t $1     2147083648  536870912   "$TRACES_DIR/H2-C05.bin"
#  gen_run $t $1     2147083648  1073741824  "$TRACES_DIR/H2-C1.bin"
#  gen_run $t $1     2147083648  1610612736  "$TRACES_DIR/H2-C15.bin"
#  gen_run $t $1     2147083648  2147083648  "$TRACES_DIR/H2-C2.bin"
}

run_Hsram() {
  not_supported "Hsram"
}
