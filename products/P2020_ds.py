from products.Product import Product
from pathlib import Path
from typing import List, Dict, Tuple, Union
from tempfile import NamedTemporaryFile
from utils.types import ProdConf, MemJson
from utils.scriptutil import load_json, substi_temp, dump_json
from utils.buildutils import doBuild, object_of, get_corunner
from utils.jinja_templating import gen_cmm_from_template
from utils.templates import CFG_DIR, AGENT_CONFIG_JSON_TEMPLATE, TOP_DIR, \
                            CO_TYPES
import utils.templates as globs


class P2020_ds(Product):

    def __init__(self, product: ProdConf = load_json(
                                                      CFG_DIR / 'products.json'
                                                    )['p2020']['ds']):
        self._readProd(product)

        #self._last_addr = 2147083648

    # Special args:
    # memplace: Dict[str, Union[str, int]]
    # l1caches: bin (ic: 0001; it: 0010; dc: 0100; dt: 1000)
    def build(
                self,
                task_name: str,
                out_dir: Path,
                task_core: int,
                agents: List[str] = [],
                max_mes: int = 1024,
                corunner: Dict[str, Union[str, int, None]] = {
                                                                'type': None
                                                             },
                memplace: MemJson = {},
                l1caches: bin = 0b0
             ) -> str:
        app = {'cores': []}
        corunner_lst = []
        corunner_app = {}
        kbuildgen = load_json(globs.KBG_JSON)
        build_dir = TOP_DIR / 'build' / task_name / out_dir
        app_file = build_dir / 'app.json'
        co_part = kbuildgen['partitions'][0]
        if agents == []:
            agents.append(task_name)
        cfg = kbuildgen['app_config']
        if not isinstance(cfg, list):
            kbuildgen['app_config'] = [cfg]
        cfg = kbuildgen['app_config']
        if not build_dir.exists():
            build_dir.mkdir(parents=True)
        else:
            def empty_dir(d):
                for el in d.iterdir():
                    if el.is_dir():
                        empty_dir(el)
                        el.rmdir()
                    else:
                        el.unlink()
            empty_dir(build_dir)

        if 'type' in corunner and corunner['type']:
            assert 'type' in corunner and corunner['type'] in CO_TYPES, \
                f"corunner_type must be specified (one of \
                [{', '.join(CO_TYPES)}])"
            corunner['core'] = abs(task_core - 1)
            corunner_lst = [corunner['core']]
            if corunner['type'] == 'read':
                assert 'read' in corunner and corunner['read'], \
                    "if corruner type is read, you must specify a read address"
                corunner_lst.append(corunner['read'])
                if 'size' in corunner and corunner['size']:
                    corunner_lst.append(corunner['size'])
                else:
                    corunner_lst.append(None)
            else:
                corunner_lst.append(None)
                if (corunner['type'] == 'jump' and
                        'size' in corunner and corunner['size']):
                    corunner_lst.append(corunner['size'])
                else:
                    corunner_lst.append(None)
            symb, co_file = get_corunner(corunner['core'], corunner['type'])
            co_file = Path(co_file)
            obj = str(object_of(co_file, build_dir / 'build' / 'objects'))
            asm_file = str(object_of(co_file, build_dir, extension='.asm'))
            corunner_app = {'symbol': symb, 'object': obj}
            if 'as_sources' not in co_part:
                co_part['as_sources'] = []
            co_part['as_sources'].append({
                                            'input_file': asm_file,
                                            'output_file': obj
                                          })

        if memplace:
            for el in memplace['elements']:
                if el['type'] == 'corunner' and corunner_app:
                    el['name'], _ = get_corunner_symbol(corunner['core'],
                                                        corunner['type'])
            kbuildgen['gen_mem_conf_output'] = build_dir / 'kmem_app.json'

        flags = {
                        'inst_co': 1,
                        'inst_task': 1 << 1,
                        'data_co': 1 << 2,
                        'data_task': 1 << 3
                      }
        cores = [None for i in range(self._core_number)]
        cores[task_core] = 'task'
        if corunner_app:
            cores[corunner['core']] = 'co'
        app['cores'] = []
        for c in cores:
            if c:
                core = {
                        'id': cores.index(c),
                        'l1_cache_instruction': bool(l1caches &
                                                     flags[f"inst_{c}"]),
                        'l1_cache_data': bool(l1caches &
                                              flags[f"data_{c}"])
                        }
                if c == 'co':
                    core['co_runner'] = corunner_app
                app['cores'].append(core)

        app['agents'] = []
        for ag in agents:
            temp = substi_temp(AGENT_CONFIG_JSON_TEMPLATE,
                               {
                                   'agent_name': f"{ag}",
                                   'agent_core': task_core
                               })
            app['agents'].append(load_json(temp, o=False))
        dump_json({'app': app}, f=app_file)
        cfg.append(str(app_file))

        rtk_dir = self._rtk_src_dir / 'build' / self._name / '_bsp'
        kbuildgen['psyko'] = str(self._rtk_src_dir / 'build_core' / 'sdk' /
                                 'bin' / 'psyko')

        psyko_opts = kbuildgen['psyko_options'] \
            if 'psyko_options' in kbuildgen else {}
        psyko_opts['product'] = self._name
        psyko_opts['kernel_dir'] = str(rtk_dir)
        psyko_opts['gen_dir'] = str(build_dir / 'gen')
        kbuildgen['psyko_options'] = psyko_opts

        kmem = str(build_dir / 'kmemconf.json')
        kbuildgen['gen_mem_conf_output'] = kmem
        kbuildgen['overwrite_memory_configuration'] = True
        kbuildgen['kmemory'] = kmem
        out_bin = str(build_dir / 'program.elf')
        kbuildgen['output_binary'] = out_bin

        dump_json(kbuildgen, f=build_dir / 'kbuildgen.json')
        kbuildgen_bin = self._rtk_src_dir / 'build_core' / 'obj' / \
            'pyutils' / 'kbuildgen' / '__main__.py'

        if corunner_lst:
            corunner_lst = [corunner_lst]

        doBuild(task_name, task_core, build_dir, max_mes, kbuildgen_bin,
                corunner_list=corunner_lst, mem_conf=memplace)
        return out_bin

    def genCmm(
               self, context: Dict[str, Union[List[str], bool, str, int]],
               template: Path = 'config/p2020-ds-p.cmm.j2'
              ) -> NamedTemporaryFile:
        prod = self._name
        build = self._rtk_src_dir / 'build' / prod
        context['product'] = prod
        context['load_all'] = build / '_bsp' / prod / 'debug' / 'load_all.cmm'
        context['k2_elf'] = build / 'build' / 'dev-k2.elf'
        if 'l2sram' not in context:
            context['l2sram'] = False
        if 'break_delete' not in context:
            context['break_delete'] = True
        if 'full_debug' not in context:
            context['full_debug'] = True
        return gen_cmm_from_template(template, context)
