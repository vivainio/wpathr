# wpp: shorten your PATH on windows.

wpathr (pronounced 'weather') is a PATH manipulation tool. Taking backup of your relevant Path registry entries is
adviced. Note that editing registry *can* wedge up your system.

Confusingly, the actual command name is now 'wpp' as 'wpathr' turned out to be too hard to type.

Installation (assuming pip):

```sh

$ pip install wpathr
$ wpp -h
# ... should see help message for wpp
```

If you don't have pip, just git clone and

```sh
python wppathr -h
```

Motivation:

Windows has path size limitations, so when you add new entries (even through editing relevant registry entries
directly), you may end up truncating and losing entries from path.

Solution:

- Scans PATH environment settings for User and System scope in registry.
- Removes duplicate entries (same path twice in PATH)
- Shortens certain path names with legacy "Progra~1" approach (that is
  still supported on windows)
- Commits the changes to registry.

Requires:

- Python 2.7.x

Typical usage:

```sh
# grab a backup

$ wpp dump > path_backup.txt

# preview what the new path would look like
$ wpp squash

# I like it, squash again with --commit to write changes

$ wpp squash --commit
```

This utility supports several path operations, like:

ls: list all entries in USER and SYSTEM paths, in alphabetical order

squash: shorten path names (as explained above)

dump: dump paths to screen. Useful as quick backup (as illustrated above)

dedupe: remove duplicates from path, ignoring case

exists: remove nonexisting items from path

search PATTERN PATTERN: search directories in PATH, looking for files matching any of
 the PATTERNs under these directories.

long: map shortened names (e.g. by squash) to long names, show on screen (but do not modify)

factor: extract runs of path segment to new environment variable, e.g.

```sh
$ wpp factor CONEMU_ROOT "C:\Program Files\ConEmu"

```

Example: configure PATH for sublime text:

```
# set environment variable
$ wpp sset SUBLIME c:\opt\ST3

# add the environment variable to PATH
wpp add --commit %SUBLIME%
```

Example: make GitHub for windows paths shorter

```
wpp factor --commit GITHUB C:\Users\villevai\AppData\Local\GitHub
```

Help text:

```
usage: wpp [-h]
              {ls,squash,dump,dedupe,exists,search,long,factor,sset,sync,add,remove}
              ...

PATH optimization and management utility for Windows

positional arguments:
  {ls,squash,dump,dedupe,exists,search,long,factor,sset,sync,add,remove}
    ls                  List paths alphabetically
    squash              Shorten paths by squashing (convert to progra~1
                        format)
    dump                Dump paths to screen in original format (for backup)
    dedupe              Remove duplicate paths
    exists              Remove nonexisting paths
    search              Scan through path for files matching PATTERN
    long                Show long names (progra~1 -> Program Files
    factor              Factor out runs of VALUE in path to %VARIABLE%
                        referenses
    sset                Set SYSTEM env variable to VALUE. Like xset /s, really
    sync                Notify other processes to sync the environment
    add                 Add directory to System path
    remove              Remove directory from path

optional arguments:
  -h, --help            show this help message and exit
```
