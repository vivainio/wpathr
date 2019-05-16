from __future__ import print_function
from future import standard_library
standard_library.install_aliases()
from builtins import object
import os
import ctypes
from ctypes import wintypes
from collections import OrderedDict
import winreg
import argp as args
import fnmatch
import argparse
import pickleshare
import pprint
import sys

from subprocess import check_call

if sys.hexversion > 0x03000000:
    import winreg
else:
    import winreg as winreg

def get_db():
    return pickleshare.PickleShareDB('~/.wpathr')

class Win32Environment(object):
    """Utility class to get/set windows environment variable"""

    def __init__(self, scope):
        assert scope in ('user', 'system')
        self.scope = scope
        if scope == 'user':
            self.root = winreg.HKEY_CURRENT_USER
            self.subkey = 'Environment'
        else:
            self.root = winreg.HKEY_LOCAL_MACHINE
            self.subkey = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'

    def getenv(self, name):
        key = winreg.OpenKey(self.root, self.subkey, 0, winreg.KEY_READ)
        try:
            value, _ = winreg.QueryValueEx(key, name)
        except WindowsError:
            value = ''
        return value

    def setenv(self, name, value):
        # Note: for 'system' scope, you must run this as Administrator
        key = winreg.OpenKey(self.root, self.subkey, 0, winreg.KEY_ALL_ACCESS)
        winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
        winreg.CloseKey(key)
        # For some strange reason, calling SendMessage from the current process
        # doesn't propagate environment changes at all.
        # TODO: handle CalledProcessError (for assert)
    def items(self):
        key = winreg.OpenKey(self.root, self.subkey,0, winreg.KEY_ALL_ACCESS)
        i=0
        while 1:
            try:
                v = winreg.EnumValue(key, i)
            except WindowsError:
                return
            yield (v[0],v[1])
            i+=1


_GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
_GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
_GetShortPathNameW.restype = wintypes.DWORD

_GetLongPathNameW = ctypes.windll.kernel32.GetLongPathNameW
_GetLongPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
_GetLongPathNameW.restype = wintypes.DWORD

CreateSymbolicLinkW = ctypes.windll.kernel32.CreateSymbolicLinkW
CreateSymbolicLinkW.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
CreateSymbolicLinkW.restype = ctypes.c_ubyte

def symlink_ms(source, link_name):
    flags = 1 if os.path.isdir(source) else 0
    if CreateSymbolicLinkW(link_name, source.replace('/', '\\'), flags) == 0:
        raise ctypes.WinError()

def get_short_path_name(long_name):
    """
    Gets the short path name of a given long path.
    http://stackoverflow.com/a/23598461/200291
    """
    output_buf_size = 0
    while True:
        output_buf = ctypes.create_unicode_buffer(output_buf_size)
        needed = _GetShortPathNameW(long_name, output_buf, output_buf_size)
        if output_buf_size >= needed:
            return output_buf.value
        else:
            output_buf_size = needed

def get_long_path_name(short_name):
    """
    Gets the long path name of a given long path.
    http://stackoverflow.com/a/23598461/200291
    """
    output_buf_size = 0
    while True:
        output_buf = ctypes.create_unicode_buffer(output_buf_size)
        needed = _GetLongPathNameW(short_name, output_buf, output_buf_size)
        if output_buf_size >= needed:
            return output_buf.value
        else:
            output_buf_size = needed


def broadcast_settingschanged():
    HWND_BROADCAST = 0xFFFF
    WM_SETTINGCHANGE = 0x1A

    SMTO_ABORTIFHUNG = 0x0002

    result = ctypes.c_long()
    SendMessageTimeoutW = ctypes.windll.user32.SendMessageTimeoutW
    SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, u'Environment', SMTO_ABORTIFHUNG, 5000,
        ctypes.byref(result))

def shorten_path(ents):
    od = OrderedDict()
    for e in ents:
        od.update({e:1})

    def should_shorten(ent):
        if ' ' in ent:
            return True
        if '~' in ent or len(ent) < 50:
            return False
        return False

    return [get_short_path_name(e) if should_shorten(e) else e for e in list(od.keys())]



def process_paths(funcs, commit=False):
    """ run a sequence of funcs on path """
    dirty = False
    for sc in ['user', 'system']:
        env = Win32Environment(scope=sc)
        oldpath = env.getenv("PATH").rstrip(";")
        cur_path = oldpath.split(";")
        old_items = set(cur_path)
        for f in funcs:
            cur_path = f(cur_path)


        if cur_path is None:
            # no manipulation, assume no mods needed and exit
            continue

        # remove empty elements
        cur_path = [_f for _f in cur_path if _f]

        newpath = ";".join(cur_path)
        new_items = set(cur_path)


        #print sc,":="
        #print newpath
        actions = []
        for added in new_items.difference(old_items):
            actions.appends("+ " + added)
        for deleted in old_items.difference(new_items):
            actions.append("- " + deleted)

        if not actions:
            print("No changes for:",sc)
        else:
            print("Changes for:",sc)
            print("\n".join(actions))
            dirty = True

        if commit:
            env.setenv("PATH", newpath)

    if commit is None:
        # hack - do not complain if commit makes no sense
        return
    if dirty and not commit:
        print("Call with '--commit' to commit changes to env registry")


#def main():
def ls(a):
    """ Show list of paths in alphabetical order """

    full_path = set(os.environ["PATH"].split(";"))

    eu = Win32Environment(scope='user')
    print("\n\n*** USER: ***\n")
    upath = sorted(eu.getenv("PATH").split(";"))
    print("\n".join(upath))

    es = Win32Environment(scope='system')
    print("\n\n*** SYSTEM: ***\n")
    spath = sorted(es.getenv("PATH").split(";"))
    print("\n".join(spath))

    uncovered = full_path.difference(set(upath).union(set(spath)))
    if uncovered:
        print("\n\n*** OTHER (nonregistry): ***\n")
        print("\n".join(sorted(uncovered)))

    inactive = set(upath).union(set(spath)).difference(full_path)
    if inactive:
        print("\n\n*** INACTIVE (in registry but not in current environ): ***\n")
        print("\n".join(sorted(d for d in inactive if not d.startswith('%'))))


def squash(arg):
    """ Shorten path by using windows "short" path names (Program~1)"""
    for sc in ['user', 'system']:
        env = Win32Environment(scope=sc)
        oldpath = env.getenv("PATH")

        newpath = ";".join(shorten_path(oldpath.split(";")))
        print(sc,":=")
        print(newpath)
        if arg.commit:
            env.setenv("PATH", newpath)


    if not arg.commit:
        print("Call 'wpathr squash --commit' to commit changes to env registry")
    else:
        print("Committed changes to registry")
        #print newpath

def dump(arg):
    """ Dump user and system path settings """
    for sc in ['user', 'system']:
        env = Win32Environment(scope=sc)
        oldpath = env.getenv("PATH")
        print(sc, ":=")
        print(oldpath)

def dedupe(arg):
    """ Remove duplicates from path """
    def deduper(path):
        rset = set()
        r = []
        for e in path:
            if e.lower() in rset:
                print("Duplicate:", e)
            else:
                r.append(e)
                rset.add(e.lower())
        return r

    process_paths([deduper], arg.commit)

def exists(arg):
    """ Filter path by removing nonexisting entries """

    def check_existing(path):
        r = []
        for p in path:
            pe = os.path.expandvars(p)
            if os.path.isdir(pe):
                r.append(p)
            else:
                print("Path does not exist:", p)
        return r

    process_paths([check_existing], arg.commit)


def search(arg):
    """ Search path for files matching a pattern """

    patterns = [p if '*' in p else p+"*" for p in arg.pattern]
    def search_path(path):
        for p in path:
            ep = os.path.expandvars(p)
            if not os.path.isdir(ep):
                print("NONEXISTING:", ep)
            # print "Scan",ep
            ents = os.listdir(ep)

            #print ents
            hits = set()
            for pat in patterns:

                hits.update(h for h in ents if fnmatch.fnmatch(h,pat))

            if hits:
                print(p)
                print(" " + " ".join(hits))
        return None

    process_paths([search_path], None)

def longnames(arg):
    """ Show long names for all entries in path """
    def to_long(path):
        for p in path:
            longname = get_long_path_name(os.path.expandvars(p))
            if p != longname:

                print(p, "->", longname)
            else:
                print(p if p else '<empty>')
        return None

    process_paths([to_long], None)

def factor(arg):
    print("Factor", arg)
    var = arg.variable
    val = arg.value
    def factor_out(path):
        r = []
        for p in path:
            replaced = p.replace(val, "%" + var + "%")
            if replaced != p:
                print("Can replace:", p,"->", replaced)
            r.append(replaced)
        return r


    if arg.commit and var in os.environ:
        print("Cannot factor out against existing environment variable. Please remove:",var)

    process_paths([factor_out], arg.commit)
    if arg.commit:
        Win32Environment('system').setenv(var, val)


def sset_c(arg):
    Win32Environment("system").setenv(arg.variable, arg.value)
    broadcast_settingschanged()

def sync(arg):
    broadcast_settingschanged()

def add_s(arg):
    e = Win32Environment('system')
    oldpath = e.getenv("PATH").rstrip(";")
    oldpath_l = oldpath.lower().split(";")
    newpath = oldpath.split(";")
    for d in arg.directory:
        d = os.path.abspath(d) if not d.startswith("%") else d
        if d.lower() in oldpath_l:
            print("Skip existing:", d)
            continue

        newpath.append(d)
        print("Add:",d)
    if not arg.commit:
        print("Call with '--commit' to write changes")
        return

    e.setenv("PATH", ';'.join(newpath))

def remove_s(arg):
    def remover(path):
        newpath = path[:]
        for d in arg.directory:
            if d in newpath:
                #print "Remove:",d
                newpath.remove(d)
        return newpath

    process_paths([remover], arg.commit)

def env_paths(arg):

    uncovered = set(k.upper() for k in os.environ)
    for sco in ('user', 'system'):
        print("\n**",sco)
        vars = list(Win32Environment(sco).items())
        for k,v in sorted(vars):
            if os.path.exists(os.path.expandvars(v)):
                uncovered.discard(k.upper())

                print(k,"->", v)
    print("\n** Unknown (not in registry)")
    for uc in sorted(uncovered):
        v = os.environ[uc]
        if os.path.exists(os.path.expandvars(v)):
            print(uc,"->", v)

def symlink_c(arg):
    fpath = os.path.abspath(arg.filepath)
    assert os.path.exists(fpath)
    symlink_ms(fpath, arg.linkname)

def symlinks_c(arg):
    print("symlinks", arg)

def alias_c(arg):
    db = get_db()
    aliases = db.get('alias', {})

    # 1: no args
    if arg.name is None:
        pprint.pprint(aliases)
        return
   # 2: one arg
    if arg.command is None:
        arg.command = os.path.abspath(arg.name)
        arg.name = os.path.splitext(os.path.basename(arg.command))[0]


    aliases[arg.name] = os.path.abspath(arg.command)
    print("alias: '%s' for '%s'" % (arg.name, arg.command))

    db['alias'] = aliases

def run_and_exit(cmd):
    """ Run command and exit process with the status value.

    Run as very last thing!
    """
    r = os.system(cmd)
    sys.exit(r)

def runalias_c(arg):
    db = get_db()
    aliases = db['alias']
    cmd = aliases.get(arg.name, None)
    if cmd is None:
        pprint.pprint(aliases)
        return

    fullcmd = ('"%s"' % cmd) + ' ' + " ".join(arg.args)
    print(">", fullcmd)
    run_and_exit(fullcmd)

def scan_up_tree(cmd):
    found = None
    current = os.path.abspath(os.getcwd())
    while 1:
        trie = os.path.join(current, cmd)
        if os.path.isfile(trie):
            found = trie
            break
        new = os.path.dirname(current)
        if current == new:
            break
        current = new
    return found

def run_command_or_script(cmd, args):
    interp = ""
    if cmd.endswith(".py"):
        interp = "python "
    elif cmd.endswith(".ps1"):
        interp = "powershell "
    elif cmd.endswith(".js"):
        interp = "node "

    run_and_exit("%s%s %s" % (interp, cmd, " ".join(args.argument)))

def run_up_c(arg):
    cmd = scan_up_tree(arg.command)
    if not cmd:
        print("Cannot find %s in any parent directory" % arg.command)
        return
    os.chdir(os.path.dirname(cmd))
    run_command_or_script(cmd, arg)

def main():
    pp = argparse.ArgumentParser(prog = "wpp",
    description="PATH optimization and management utility for Windows",
    epilog="See https://github.com/vivainio/wpathr for detailed documentation.")

    args.init(pp)
    args.sub("ls", ls, help = "List paths alphabetically")
    sqc = args.sub("squash", squash, help = "Shorten paths by squashing (convert to progra~1 format)")
    args.sub("dump", dump, help = "Dump paths to screen in original format (for backup)")
    ddc = args.sub("dedupe", dedupe, help = "Remove duplicate paths")
    exc = args.sub("exists", exists, help = "Remove nonexisting paths")
    src = args.sub("search", search, help = "Scan through path for files matching PATTERN")
    lnc = args.sub("long", longnames, help = "Show long names (progra~1 -> Program Files)")
    fac = args.sub("factor", factor, help = "Factor out runs of VALUE in path to %%VARIABLE%% referenses")
    fac.arg("variable", metavar="VARIABLE")
    fac.arg("value", metavar="VALUE")
    sset = args.sub("sset", sset_c, help="Set SYSTEM env variable to VALUE. Like xset /s, really")
    sset.arg("variable", metavar="VARIABLE")
    sset.arg("value", metavar="VALUE")

    syc = args.sub("sync", sync, help="Notify other processes to sync the environment")

    src.arg("pattern", type=str, nargs="+")

    adc = args.sub("add", add_s, help='Add directory to System path')
    adc.arg('directory', nargs="+")

    rmc = args.sub('remove', remove_s, help="Remove directory from path")
    rmc.arg('directory', nargs="+")

    pvc = args.sub('env', env_paths, help="List env variables that refer to existing paths")
    # operations that support --commit

    slc = args.sub('symlink', symlink_c, help="Create symbolic link at LINKPATH from SOURCE")
    slc.arg('linkname', metavar="LINKPATH")
    slc.arg('filepath', metavar="FILEPATH")

    alias = args.sub('alias', alias_c, help="Create alias for a command")
    alias.arg('name', nargs="?")
    alias.arg('command', nargs="?")

    runalias = args.sub('r', runalias_c, help="Run aliased command with arguments")
    runalias.arg('name', metavar="ALIAS")
    runalias.arg('args', metavar="ARGUMENTS", nargs=argparse.REMAINDER)

    up = args.sub('up', run_up_c, help="Run command that exist in any parent directory")
    up.arg("command")
    up.arg("argument", nargs="*")

    for a in [sqc, ddc, exc, fac, adc, rmc]:
        a.arg("--commit", action='store_true')

    args.parse()

if __name__ == "__main__":
    main()
