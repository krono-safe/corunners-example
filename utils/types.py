from typing import Dict, List, Union, NewType
from pathlib import Path

ProdConf = NewType(
    'ProdConf',
    Dict[
      str,
      Union[
        str,
        float,
        List[str],
        int,
        Dict[
          str,
          Dict[str, int]
        ],
        Path
      ]
    ]
)

MemJson = NewType(
    'MemJson',
    Dict[
      str,
      List[
        Dict[
          str,
          Union[
            List[str],
            str,
            Dict[
              str,
              Union[
                str,
                List[str]
              ]
            ]
          ]
        ]
      ]
    ]
)
