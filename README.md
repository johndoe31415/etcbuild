# etcbuild
Embedded toolchain builder is a set of scripts that allows building a
customized gcc build for ARM, AVR, Blackfin systems, including binutils, gcc,
newlib and gdb. It is written in a flexible manner to allow for easy adaption
of new packages or architectures.

## Usage
```
usage: etcbuild [-h] [-e filename] [-p filename] [-d dirname]
                [--concurrency processes] [--disable-verification]
                [--no-cleanup] [--no-install] [-v]
                target [target ...]

Embedded toolchain build script.

positional arguments:
  target                Target(s) to build.

optional arguments:
  -h, --help            show this help message and exit
  -e filename, --envfile filename
                        Specifies an environment file; can be specified
                        multiple times (order matters, later options supersede
                        previous ones). Set of JSON files which define build
                        environment parameters such as the target or
                        installation directory.
  -p filename, --packages filename
                        Specifies package configuration file. Defaults to
                        packages.json.
  -d dirname, --package-dir dirname
                        Specifies subdirectory in which to store downloaded
                        package sources. Defaults to packages.
  --concurrency processes
                        Specifies number of concurrent processes to use.
                        Defaults to 12.
  --disable-verification
                        Disables verification of hashes of downloaded files.
                        Not recommended.
  --no-cleanup          By default, temporary files during the build process
                        are removed after the build is finished. This option
                        keeps them around.
  --no-install          Just build the packages, but do not install them.
  -v, --verbose         Increases verbosity. Can be specified multiple times
                        to increase.
```

The typical configuration is split into a local JSON file that contains your
local build environment, such as:

```json
{
	"gcc-prefix":	"~/bin/gcc"
}
```

And a target-specific/configuration-specific configuration file, such as:

```json
{
	"target":	"cortex-m3",
	"prefix":	"{{gcc-prefix}}/cm3"
}
```

Then, the build process can be easily invoked:

```
$ ./etcbuild -e env_joe.json -e env_cortex_m3.json binutils
```

or

```
$ ./etcbuild -e env_joe.json -e env_cortex_m3.json binutils gcc gdb
```

Package names have the following form: `pkgname-version/flag1,flag2,...`. I.e.,
`gcc` is a valid flag, but `gcc-1.2.3` as well and `gcc-1.2.3/foo,bar,c++` one
that specifies a version and flags.

## Targets
Currently recognized targets are:

  * cortex-m0
  * cortex-m1
  * cortex-m3
  * cortex-m4
  * tdmi7
  * avr
  * blackfin

## License
GNU GPL-3.
