# wpathr: shorten your PATH on windows.

wpathr (pronounced 'weather') is a PATH manipulation tool.
Taking backup of your relevant Path registry entries is adviced. Note that
editing registry *can* wedge up your system.

Installation (assuming pip):

```sh

$ pip install wpathr
$ wpathr -h
# ... should see help message for wpathr
```

If you don't have pip, just git clone and

```sh
python wpathr -h
```

Motivation:

Windows has path size limitations, so when you add new entries (even through
editing relevant registry entries directly), you may end up truncating and losing entries from path.

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

$ wpathr dump > path_backup.txt

# preview what the new path would look like
$ wpathr squash

# I like it, squash again with --commit to write changes

$ wpathr squash --commit
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
    $ wpathr factor CONEMU_ROOT "C:\Program Files\ConEmu"
```
