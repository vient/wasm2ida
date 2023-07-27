#!/usr/bin/env python3
import contextlib
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
        wabt_build_dir.mkdir()
        with pb.local.cwd(wabt_build_dir):
            (pb.local['cmake']['..'] > output)()
            (pb.local['cmake']['--build', '.', '-j32'] > output)()
        with pb.local.cwd(WABT_DIR):
            (pb.local['make']['update-wasm2c'] > output)()  # just in case
        with pb.local.cwd(wabt_build_dir):
            (pb.local['cmake']['..'] > output)()
            (pb.local['cmake']['--build', '.', '-j32'] > output)()

    return pb.local[wasm2c_path]


class Wasm2Ida(cli.Application):
    quiet = cli.Flag(['q', 'quiet'], help='supress all output')
    keep_wasm_checks = cli.Flag(['keep-wasm-checks'], help='to not remove checks like call stack depth')
    force_wabt_rebuild = cli.Flag(['force-wabt-rebuild'], help='rebuild WABT submodule even if wasm2c already exists')

    build_dir = None

    @cli.switch(['b', 'build-dir'], pb.LocalPath, help='build directory, default is temporary directory')
    def _set_build_dir(self, build_dir):
        self.build_dir = build_dir

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

        with contextlib.ExitStack() as stack:
            if self.build_dir is not None:
                build_dir: pb.LocalPath = self.build_dir
                build_dir.mkdir()
                if not build_dir.exists():
                    raise ValueError(f'failed to create build directory {build_dir}')
                if not build_dir.is_dir():
                    raise ValueError(f'build path {build_dir} is not a directory')
            else:
                build_dir = stack.enter_context(pb.local.tempdir())
            data_c: pb.LocalPath = build_dir / 'data.c'
            imports_c: pb.LocalPath = build_dir / 'data.imports.c'
            data_o: pb.LocalPath = build_dir / 'data.o'
            imports_o: pb.LocalPath = build_dir / 'imports.so'

            (wasm2c[wasm_path, '-o', data_c] > output)()
            assert data_c.exists()
            assert imports_c.exists()

            (WABT_DIR / 'wasm2c' / 'wasm-rt.h').copy(build_dir)
            (WABT_DIR / 'wasm2c' / 'wasm-rt-impl.c').copy(build_dir)
            (WABT_DIR / 'wasm2c' / 'wasm-rt-impl.h').copy(build_dir)

            defines = []
            if self.keep_wasm_checks:
                defines.append('-DWASM2IDA_KEEP_CHECKS')


            _, _, stderr = (gcc['-v', '-m32', '-shared', imports_c, build_dir / 'wasm-rt-impl.c', '-o', imports_o] > output).run()
            library_path = next(s for s in stderr.splitlines() if s.startswith('LIBRARY_PATH=')).split('=')[1].split(':')
            (gcc.__getitem__([*defines, '-m32', '-O2', '-fno-stack-protector', '-fno-plt', '-fno-pic', '-c', data_c, imports_o, '-o', data_o]) > output)()
            library_path.append(build_dir)
            library_path = [f'-L{s}' for s in library_path]
            (ld['--no-dynamic-linker', '-m', 'elf_i386', '-T', (SELF_DIR / 'build' / 'script.ld'), data_o,
                library_path, '-l:' + imports_o.name, '-lgcc', '-lgcc_s', '-lc', '-o', result_path] > output)()


if __name__ == '__main__':
    Wasm2Ida.run()
