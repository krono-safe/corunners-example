#! /usr/bin/env python3
#
# This script generates the json files for the memory placement. It allows to control the placement of two parts:
# * the task;
# * the co_runners;
#
# Usage:
#   python3 gen-corunner.py --jumps 1024 > code.asm
#
# both the data and the text can be set.


import argparse
import sys
import json
from scriptutil import load_db, load_json, dump_json
from copy import deepcopy
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--config', nargs='?', type=argparse.FileType('r'), default='-')
parser.add_argument('--memreport', type=Path, required=True)
parser.add_argument('--default_kmem', type=Path, nargs='+')
parser.add_argument("--kdbv", type=Path, required=True)
args = parser.parse_args(sys.argv[1:])

def del_all_list(l):
  n = range(0, len(l))
  for i in n:
    del l[i]

memreport = load_db(args.kdbv, args.memreport)
kmem = load_json(args.default_kmem)
config = load_json(args.config)

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
  del_dom = []
  if el['type'] == 'corunner':
    for reg in kmem['kmemory']['region']:
      for dom in reg['domains']:
        if dom['identifier'] in el['names']:
          d = set()
          for sec in dom['output_sections']:
            d.add(sec['name'])
          secs.append([d, deepcopy(dom), reg['name']])
          del_dom.append(dom)
  else:
    sec_sat2 = deepcopy(sec_sat)
    for sec in sec_sat.keys():
      if sec_sat[sec][3] not in el['names']:
        del sec_sat2[sec]

    for reg in kmem['kmemory']['region']:
      for dom in reg['domains']:
        d = set()
        for sec in dom['output_sections']:
          if sec['name'] in sec_sat2.keys():
            d.add(sec['name'])
        if d:
          secs.append([d, deepcopy(dom), reg['name']])
          del_dom.append(dom)
  del_all_list(del_dom)

  for sec in el['sections']:
    assert set(sec.keys()).intersection({'region','address'}), \
      "A least one of 'region', 'address' must be present in placement configuration"
    d = set()
    comp = False
    secs_2 = deep_copy(secs)
    del_s = []
    for s in secs_2:
      for n in s[0]:
        if sec_sat[n][2] in sec['types']:
          d.add(n)
        else:
          for os in s[1]['output_sections']:
            if os['name'] == n:
              del os
      inter = d.intersection(s[0])
      if not inter:
        del_s.append(s)
    del_all_list(del_s)

    def find_reg_name():
      for reg in kmem['kmemory']['region']:
        addr = reg['physical_address']
        if addr <= sec['address'] < addr+reg['size']:
          return reg['name']
    reg_name = sec['region'] if 'region' in sec.keys() else find_reg_name()
    for reg in kmem['kmemory']['region']:
      if reg['name'] == reg_name:
        if 'address' not in sec.keys():
          for s in secs_2:
            if not reg['domains']:
              s[1]['output_sections'][0]['physical_address'] = reg['physical_address']
            reg['domains'].append(s[1])
        else:
          addr1 = reg['physical_address']
          addr2 = 0
          place_size = 0
          for s in secs_2:
            for name in s[0]:
              place_size += sec_sat[name][0]
          dom_ind = 0
          reg2 = deepcopy(reg['domains'])
          placed = False
          dec = False
          for i in range(0, len(reg2)):
            l = 0
            if placed:
              l = len(secs_2)
            osi = reg['domains'][i+l]['output_sections']
            for j in range(0, len(reg2[i]['output_sections'])):
              os = osi[j]
              if not placed:
                addr2 = sec_sat[os['name']][1]
                if addr1 < sec['address'] < addr2+sec_sat[os['name']][0]:
                  os0 = reg['domains'][i]['output_sections'][0]
                  os0['physical_address'] = sec_sat[os0['name']][1]
                  secs_2[0]['output_sections'][0]['physical_address'] = sec['address']
                  placed = True
                  for s in secs_2[::-1]:
                    reg['domains'].insert(i, s[1])
                  if sec['address'] > addr2 or place_size >= addr2-sec['address']:
                    dec = True
                    os['physical_address'] = sec['address']+place_size
                  else:
                    break
              elif 'physical_address' in os.keys():
                os['physical_adress'] = os['physical_address']+place_size
            if placed and not dec:
              break
            addr1 = addr2
