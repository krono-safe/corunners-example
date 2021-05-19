#! /usr/bin/env python3
#
# This script generates the json files for the memory placement. It allows to control the placement of two parts:
#  * the task;
#  * the co_runners;
#
# Usage:
#   python3 gen-kmem.py --config {json config file} --memreport {ks memreport file} --default_kmemory {default kmemory json file}
#
# Notes:
#   * The default kmemory will be overwritten. To avoid that, add --out_kmem to specify an other output file.
#   * An exemple template for the json config file is available at /exemples/mem-place.json. In each sections, at least of address or region must be present. The names of the elements must be the task names for agents and the identifiers in the default kmem for the corunners.
#  * Except the config file arguments, all options can be put in the config json. options specified as arguments will overwrite options specified in the config.
#
# Both the data and the text can be set separatly.


import argparse
import sys
import json
from scriptutil import load_db, load_json, dump_json
from copy import deepcopy
from pathlib import Path

def del_all_list(l, rem):
  for el in l:
    rem.remove(el)

parser = argparse.ArgumentParser()
parser.add_argument('--config', nargs='?', type=argparse.FileType('r'), default='-')
parser.add_argument('--memreport', type=Path)
parser.add_argument('--default_kmemory', type=Path)
parser.add_argument('--out_kmemory', type=Path)
parser.add_argument("--kdbv", type=Path)
args = parser.parse_args(sys.argv[1:])

config = load_json(args.config, o=False)

try:
  if not args.default_kmemory:
    args.default_kmemory = config['default_kmemory']
  if not args.memreport:
    args.memreport = config['memreport']
  if not args.kdbv:
    args.kdbv = config['kdbv']
except KeyError as e:
  print(f"{e.args[0]} must be pased either in the config json or in program parameters!", file=stderr)

if not args.out_kmemory:
  args.out_kmemory = config.get('out_kmemory', args.default_kmemory)

memreport = load_db(args.kdbv, args.memreport)
kmem = load_json(args.default_kmemory)

sec_sat = dict()
for sec in memreport['sections']:
  if 'id_name' in sec.keys():
    id_name = sec['id_name']
  else:
    id_name = ''
  sec_sat[sec['name']] = [sec['size'], sec['address'], sec['type'], id_name]
  del sec

for el in config['elements']:
  assert el['type'] in ['corunner', 'task']
  secs = []
  if el['type'] == 'corunner':
    for reg in kmem['kmemory']['regions']:
      if 'domains' in reg.keys():
        del_dom = []
        for dom in reg['domains']:
          if 'identifier' in dom.keys() and dom['identifier'] in el['names']:
            d = set()
            for sec in dom['output_sections']:
              d.add(sec['name'])
            secs.append([d, deepcopy(dom), reg['name']])
            del_dom.append(dom)
        del_all_list(del_dom, reg['domains'])
  else:
    sec_sat2 = deepcopy(sec_sat)
    for sec in sec_sat.keys():
      if sec_sat[sec][3] not in el['names']:
        del sec_sat2[sec]

    for reg in kmem['kmemory']['regions']:
      if 'domains' in reg.keys():
        del_dom = []
        for dom in reg['domains']:
          d = set()
          for sec in dom['output_sections']:
            if sec['name'] in sec_sat2.keys():
              d.add(sec['name'])
          if d:
            secs.append([d, deepcopy(dom), reg['name']])
            del_dom.append(dom)
        del_all_list(del_dom, reg['domains'])
  if not secs:
    continue

  for sec in el['sections']:
    assert set(sec.keys()).intersection({'region','address'}), \
      "A least one of 'region', 'address' must be present in placement configuration"
    d = set()
    comp = False
    secs_2 = deepcopy(secs)
    del_s = []
    for s in secs_2:
      for n in s[0]:
        if sec_sat[n][2] in sec['names']:
          d.add(n)
#        else:
#          for os in s[1]['output_sections']:
#            if os['name'] == n:
#              del os
      inter = d.intersection(s[0])
      if not inter:
        del_s.append(s)
    del_all_list(del_s, secs_2)

    def find_reg_name():
      for reg in kmem['kmemory']['regions']:
        addr = reg['physical_address']
        if addr <= sec['address'] < addr+reg['size']:
          return reg['name']
    reg_name = sec['region'] if 'region' in sec.keys() else find_reg_name()
    for reg in kmem['kmemory']['regions']:
      if reg['name'] == reg_name:
        if 'domains' not in reg.keys():
          reg['domains'] = list()
        if 'address' not in sec.keys():
          if not reg['domains']:
            secs_2[0][1]['output_sections'][0]['physical_address'] = reg['physical_address']
          for s in secs_2:
            reg['domains'].append(s[1])
        else:
          addr1 = reg['physical_address']
          addr2 = 0
          place_size = []
          for s in secs_2:
            dom_size=0
            for name in s[0]:
              dom_size += sec_sat[name][0]
            place_size.append(dom_size)
          dom_ind = 0
          reg2 = deepcopy(reg['domains'])
          placed = False
          dec = False
          def al(os, j):
            align=0
            if 'alignment' in os.keys():
              align = os['alignment']**3
            elif j == 0:
              align = 4096
            if align and os['physical_address']%align:
              off = align-os['physical_address']%align
            else:
              off = 0
            os['physical_address'] += off
            return off
          for i in range(0, len(reg2)):
            l = 0
            if placed:
              l = len(secs_2)
            osi = reg['domains'][i+l]['output_sections']
            for j in range(0, len(reg2[i]['output_sections'])):
              os = osi[j]
              if not placed:
                addr2 = os['physical_address'] if 'physical_address' in os.keys() else sec_sat[os['name']][1]
                if addr1 < sec['address'] < addr2+sec_sat[os['name']][0]:
                  os0 = osi[0]
                  #os0['physical_address'] = sec_sat[os0['name']][1]
                  #al(os0, 0)
                  placed = True
                  off = 0
                  align = 0
                  for s in secs_2[::-1]:
                    s[1]['output_sections'][0]['physical_address'] = sec['address']+off
                    align_tmp = al(s[1]['output_sections'][0], 0)
                    reg['domains'].insert(i, s[1])
                    off += place_size[secs_2.index(s)] + align_tmp
                    align += align_tmp
                  if sec['address'] > addr2 or sum(place_size)+align >= addr2-sec['address']:
                    dec = True
                    os['physical_address'] = sec['address']+sum(place_size)+align
                    al(os, j)
                    place_size.append(align)
                  else:
                    break
              elif 'physical_address' in os.keys():
                os['physical_address'] = os['physical_address']+sum(place_size)
                al(os, j)
            if placed and not dec:
              break
            addr1 = addr2
          if not placed:
            placed = True
            align = 0
            off = 0
            for s in secs_2:
              s[1]['output_sections'][0]['physical_address'] = sec['address'] + off
              align_tmp = al(s[1]['output_sections'][0], 0)
              if 'domains' not in reg.keys():
                reg['domains'] = list()
              reg['domains'].append(s[1])
              off += place_size[secs_2.index(s)] + align_tmp
              align += align_tmp

dump_json(kmem, args.out_kmemory)
