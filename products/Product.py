from abc import ABC, abstractmethod
from typing import Dict, List, Union, Optional, Tuple
from pathlib import Path
from utils.types import ProdConf


class Product(ABC):
    _name: str = ''
    #_last_addr: int = 0
    _timer: float = 0.0
    _harware: List[str] = []
    _core_number: int = 0
    _regions: Dict[str, Dict[str, int]] = {}
    _rtk_src_dir: Path = Path()

    @abstractmethod
    def build(self, task_name: str, out_dir: Path, task_core: int,
              agents: List[str] = [], max_mes: int = 1024, **kwargs) -> str:
        pass

    @abstractmethod
    def genCmm(self, **kwargs):
        pass

#   def setLastAddr(self, addr:int) -> None:
#       self._last_addr = addr

    def _readProd(self, product: ProdConf):
        self._name = product['name']
        self._timer = product['timer']
        self._hardware = product['hardware']
        self._core_number = product['core_number']

        reg = product['regions']
        self._regions = {r['name']: (r['start'],
                                     r['size']) for r in reg}
        self._rtk_src_dir = Path(product['rtk_src_dir'])

    def getName(self) -> str:
        return self._name

    def getTimer(self) -> float:
        return self._timer

    def getHardware(self) -> List[str]:
        return self._hardware

    def getHardware(self, key: str) -> bool:
        if key in self._hardware:
            return True
        else:
            return False

    def getCoreNumber(self) -> int:
        return self._core_number

    def getRegions(self) -> Dict[str, Tuple[int, int]]:
        return self._regions

    def getRegion(self, key: str) -> Union[Tuple[int, int], None]:
        if key in self._regions:
            return self._regions[key]
        else:
            return None
