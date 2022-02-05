#!/usr/bin/env python3
import os
import sys
import plumbum as pb
from plumbum import cli

DEV_NULL = open(os.devnull, "w")
SELF_DIR = pb.local.path(__file__).dirname


def get_wasm2c_cmd(quiet: bool = False):
    output = sys.stdout if not quiet else DEV_NULL
    wabt_dir: pb.Path = SELF_DIR / 'wabt'
    build_dir: pb.Path = wabt_dir / 'build'

    if not (wabt_dir / 'Makefile').exists():
        if not quiet:
            print('[*] checking out WABT submodule...', file=output)
        with pb.local.cwd(SELF_DIR):
            (pb.local['git']['submodule', 'update', '--init', '--recursive'] > output)()

    if not build_dir.exists():
        if not quiet:
            print('[*] building wasm2c...', file=output)
        build_dir.mkdir()
        with pb.local.cwd(build_dir):
            (pb.local['cmake']['..'] > output)()
            (pb.local['cmake']['--build', '.', '-j32'] > output)()

    return pb.local[build_dir / 'wasm2c']


class Wasm2Ida(cli.Application):
    quiet = cli.Flag(['q', 'quiet'], help='supress all output')

    def main(self, wasm_path: cli.ExistingFile, result_path: str):
        result_path = pb.local.path(result_path)
        if result_path.is_dir():
            raise ValueError(f'result path {result_path} is existing directory')
        result_dir = result_path.dirname
        if not result_dir.exists():
            raise ValueError(f'result directory {result_dir} does not exist')

        wasm2c = get_wasm2c_cmd(self.quiet)

        with pb.local.tempdir() as tmp:
            pass

        raise NotImplementedError


if __name__ == '__main__':
    Wasm2Ida.run()
