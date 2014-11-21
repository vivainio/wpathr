wpathr: shorten your PATH on windows.

Motivation:

Windows has path size limitations, so when you add new entries (even through
relevant registry entries), you may end up truncating and losing entries from path.

Mechanism:

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

$ python wpathr.py dump > path_backup.txt

# preview what the new path would look like
$ python wpathr.py squash

# I like it, squash again with --commit to write changes

$ python wpathr.py squash --commit
```

This utility supports several path operations, like:

ls - list all entries in USER and SYSTEM paths, in alphabetical order

squash - shorten path names (as explained above)

dump - dump paths to screen. Useful as quick backup (as illustrated above)

dedupe - remove duplicates from path, ignoring case

exists - remove nonexisting items from path

search PATTERN PATTERN - search through path, looking for files matching any of PATTERNs
