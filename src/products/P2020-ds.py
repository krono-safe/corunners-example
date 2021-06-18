
from Product import Product
from pathlib import Path
from typing import List, Dict, Tuple
from typeguard import check_type

class P2020_ds(Product):

  def __init__(self):
    self._name = P2020['ds']
    #self._last_addr = 2147083648
    self._timer = 75e6
    self._hardware = ['l2sram']
    self._core_number = 2
    self._regions = {
      'ddr': (0, 2147483648),
      'l2sram': (2147483648, 524288)
    }
  # args:
  # core: int
  # corunner_core: int
  # corunner_type: str
  # kbuildgen_json: Path
  # out: Path
  # memplace: List[str]
  # l1caches: List[str]
  def build(self, **kwargs) -> bool:
    args = {
        'core': (int, True, None)
        'corunner_core': (int, False, None),
        'corunner_type': (str, False, None),
        'kbuilgen_json': (Path, True, None),
        'out': (Path, True, None),
        'memplace': (Dict[str, Tuple[str, int]], False, lambda x: self.placeMem(x)),
        'l1caches': (List[str], False, lambda x: self.setL1Caches(x))
        }
    for key in args:
      if key in kwargs:
        check_type(key, kwargs[key], args[key][0])
        if args[key][2]:
          args[key][2](kwargs[key])
      elif args[key][1]:
        return False
  @override
  def _placeMem(mem:Dict[str, Tuple[str, int]]) -> None:




