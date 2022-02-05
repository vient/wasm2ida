# wasm2ida

Transpile WebAssembly executable to i386 ELF which is impossible to run but which looks nice in decompiler.

As you can guess from name, this was made with IDA Hex-Rays in mind, WebAssembly decompilers already exist (JEB).

Based on modified wasm2c tool from [WABT](https://github.com/WebAssembly/wabt).

## Usage

```sh
git clone https://github.com/vient/wasm2ida
./wasm2ida/wasm2ida.py -h
```

## TODO

* Check that module does not import memory blocks
* Merge memory sections in compile time to one array in `.wasm_data` section
* Interpet memory offsets as raw pointers, `.wasm_data` is mapped to 0
* Do something with `w2c_g0` register, all local variables need to be allocated on x86 stack
* It would be nice if IDA somehow detected automatically that `wasm_rt_trap` itself is noreturn and not rely on `__builtin_trap`
* Use C++ mangling instead of WebAssembly one so IDA will set correct function types automatically
