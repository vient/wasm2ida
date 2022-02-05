#!/usr/bin/env python3
import os
import sys

import plumbum as pb
from plumbum import cli

DEV_NULL = open(os.devnull, "w")
SELF_DIR = pb.local.path(__file__).dirname
WABT_DIR = SELF_DIR / 'wabt'


def get_wasm2c_cmd(force_rebuild, output=sys.stdout):
    wabt_build_dir: pb.LocalPath = WABT_DIR / 'build'
    wasm2c_path: pb.LocalPath = wabt_build_dir / 'wasm2c'

    if not wasm2c_path.exists():
        print('[*] checking out WABT submodule...', file=output)
        with pb.local.cwd(SELF_DIR):
            (pb.local['git']['submodule', 'update', '--init', '--recursive'] > output)()

    if force_rebuild or not wasm2c_path.exists():
        print('[*] building wasm2c...', file=output)
        with pb.local.cwd(WABT_DIR):
            (pb.local['make']['update-wasm2c'] > output)()  # just in case
        wabt_build_dir.mkdir()
        with pb.local.cwd(wabt_build_dir):
            (pb.local['cmake']['..'] > output)()
            (pb.local['cmake']['--build', '.', '-j32'] > output)()

    return pb.local[wasm2c_path]


class Wasm2Ida(cli.Application):
    quiet = cli.Flag(['q', 'quiet'], help='supress all output')
    keep_wasm_checks = cli.Flag(['keep-wasm-checks'], help='to not remove checks like call stack depth')
    force_wabt_rebuild = cli.Flag(['force-wabt-rebuild'], help='rebuild WABT submodule even if wasm2c already exists')

    def main(self, wasm_path: cli.ExistingFile, result_path: pb.LocalPath):
        if result_path.is_dir():
            raise ValueError(f'result path {result_path} is existing directory')
        result_dir = result_path.dirname
        if not result_dir.exists():
            raise ValueError(f'result directory {result_dir} does not exist')

        output = sys.stdout if not self.quiet else DEV_NULL
        wasm2c = get_wasm2c_cmd(self.force_wabt_rebuild, output)
        gcc = pb.local['gcc']
        ld = pb.local['ld']

        with pb.local.tempdir() as tmp:
            data_c: pb.LocalPath = tmp / 'data.c'
            imports_c: pb.LocalPath = tmp / 'data.imports.c'
            data_o: pb.LocalPath = tmp / 'data.o'
            imports_o: pb.LocalPath = tmp / 'imports.so'

            (wasm2c[wasm_path, data_c] > output)()
            assert data_c.exists()
            assert imports_c.exists()

            (WABT_DIR / 'wasm2c' / 'wasm-rt.h').copy(tmp)
            (WABT_DIR / 'wasm2c' / 'wasm-rt-impl.c').copy(tmp)
            (WABT_DIR / 'wasm2c' / 'wasm-rt-impl.h').copy(tmp)

            defines = []
            if self.keep_wasm_checks:
                defines.append('-DWASM2IDA_KEEP_CHECKS')

            (gcc['-m32', '-shared', imports_c, tmp / 'wasm-rt-impl.c', '-o', imports_o] > output)()
            (gcc.__getitem__([*defines, '-m32', '-O2', '-fno-stack-protector', '-c', data_c, '-o', data_o]) > output)()
            (ld['--no-dynamic-linker', '-T', (SELF_DIR / 'build' / 'script.ld'), data_o, '-L' + tmp,
                '-l:' + imports_o.name, '-o', result_path] > output)()


if __name__ == '__main__':
    Wasm2Ida.run()
