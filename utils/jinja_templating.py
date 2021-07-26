from jinja2 import Template, FileSystemLoader, Environment
from pathlib import Path
from typing import Optional, Dict, Union, List
from tempfile import NamedTemporaryFile
from utils.templates import TOP_DIR

SEP = '################################################'


def gen_cmm_from_template(template: Path,
                          context: Dict[str, Union[List[str], bool, str]],
                          parent: Optional[Path] = None) -> NamedTemporaryFile:
    loader = FileSystemLoader(searchpath=TOP_DIR)
    env = Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
    template = env.get_template(template, parent=parent)

    f = NamedTemporaryFile(suffix='.cmm', mode='w')

    render = template.render(context)
    print('',SEP, render, SEP,'', sep='\n')
    f.write(render)
    f.flush()
    return f
