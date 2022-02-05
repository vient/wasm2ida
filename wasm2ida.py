#!/usr/bin/env python3
import plumbum as pb
from plumbum import cli


class Wasm2Ida(cli.Application):
    verbose = cli.Flag(['v', 'verbose'], help='verbose output')

    def main(self, wasm_path: cli.ExistingFile, result_path: str):
        result_path = pb.local.path(result_path)
        if result_path.is_dir():
            raise ValueError(f'result path {result_path} is existing directory')
        result_dir = result_path.dirname
        if not result_dir.exists():
            raise ValueError(f'result directory {result_dir} does not exist')

        raise NotImplementedError


if __name__ == '__main__':
    Wasm2Ida.run()
