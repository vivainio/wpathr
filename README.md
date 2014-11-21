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

$ python wpath.py dump > path_backup.txt

# preview what the new path would look like
$ python wpath.py squash

# I like it, squash again with --commit to write changes

$ python wpath.py squash --commit
```
