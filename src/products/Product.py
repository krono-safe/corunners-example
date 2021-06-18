

from abc import ABC, abstractmethod
from typing import Dict, List, Union, Optional, Tuple

class Product(ABC):
  _name: str = ''
  #_last_addr: int = 0
  _timer: float = 0.0
  _harware: List[str] = ['']
  _core_number: int = 0
  _regions: Dict[str, Tuple[int, int] = {'': (0, 0)}

  @abstractmethod
  def build(self, **kwargs):
    pass

  def _placeMem(mem:Dict[str, Tuple[str, int]]) -> None:
    pass

  def _setL1Caches(caches:List[str]) -> None:
    pass

#  def setLastAddr(self, addr:int) -> None:
#    self._last_addr = addr

  def getName(self) -> str:
    return self._name

  def getTimer(self) -> float:
    return self._timer

  def getHardware(self) -> List[str]:
    return self._hardware

  def getHardware(self, key:str) -> bool:
    if key in self._hardware:
      return True
    else:
      return False

  def getCoreNumber(self) -> int:
    return self._core_number

  def getRegions(self) -> Dict[str, Tuple[int, int]:
    return self._regions

  def getRegion(self, key:str) -> Union[Tuple[int, int], None]:
    if key in self._regions:
      return self._regions[key]
    else:
      return None
