import os
import ctypes
from ctypes import wintypes
from collections import OrderedDict
import _winreg
import args
import fnmatch
import argparse

import sys
from subprocess import check_call

if sys.hexversion > 0x03000000:
    import winreg
else:
    import _winreg as winreg

class Win32Environment:
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


_GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
_GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
_GetShortPathNameW.restype = wintypes.DWORD

_GetLongPathNameW = ctypes.windll.kernel32.GetLongPathNameW
_GetLongPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
_GetLongPathNameW.restype = wintypes.DWORD


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
    SendMessageTimeoutW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, u'Environment', SMTO_ABORTIFHUNG, 5000, ctypes.byref(result));

def shorten_path(ents):
    od = OrderedDict()
    for e in ents:
        od.update({e:1})

    def should_shorten(ent):
        if '~' in ent or len(ent) < 50:
            return False
        if ' ' in ent:
            return True
        return False

    return [get_short_path_name(e) if should_shorten(e) else e for e in od.keys()]



def process_paths(funcs, commit=False):
    """ run a sequence of funcs on path """
    for sc in ['user', 'system']:
        env = Win32Environment(scope=sc)
        oldpath = env.getenv("PATH")
        cur_path = oldpath.split(";")

        for f in funcs:
            cur_path = f(cur_path)


        if cur_path is None:
            # no manipulation, assume no mods needed and exit
            return

        newpath = ";".join(cur_path)
        print sc,":="
        print newpath
        if commit:
            env.setenv("PATH", newpath)

    if commit is None:
        # hack - do not complain if commit makes no sense
        return
    if not commit:
        print "Call with '--commit' to commit changes to env registry"


def main():
    def ls(a):
        """ Show list of paths in alphabetical order """

        full_path = set(os.environ["PATH"].split(";"))



        eu = Win32Environment(scope='user')
        print "\n\n*** USER: ***\n"
        upath = sorted(eu.getenv("PATH").split(";"))
        print "\n".join(upath)

        es = Win32Environment(scope='system')
        print "\n\n*** SYSTEM: ***\n"
        spath = sorted(es.getenv("PATH").split(";"))
        print "\n".join(spath)

        uncovered = full_path.difference(set(upath).union(set(spath)))
        if uncovered:
            print "\n\n*** OTHER (nonregistry): ***\n"
            print "\n".join(sorted(uncovered))

        inactive = set(upath).union(set(spath)).difference(full_path)
        if inactive:
            print "\n\n*** INACTIVE (in registry but not in current environ): ***\n"
            print "\n".join(sorted(inactive))




    def squash(arg):
        """ Shorten path by using windows "short" path names (Program~1)"""
        for sc in ['user', 'system']:
            env = Win32Environment(scope=sc)
            oldpath = env.getenv("PATH")

            newpath = ";".join(shorten_path(oldpath.split(";")))
            print sc,":="
            print newpath
            if arg.commit:
                env.setenv("PATH", newpath)


        if not arg.commit:
            print "Call 'wpathr squash --commit' to commit changes to env registry"
        else:
            print "Committed changes to registry"
            #print newpath

    def dump(arg):
        """ Dump user and system path settings """
        for sc in ['user', 'system']:
            env = Win32Environment(scope=sc)
            oldpath = env.getenv("PATH")
            print sc, ":="
            print oldpath

    def dedupe(arg):
        """ Remove duplicates from path """
        def deduper(path):
            rset = set()
            r = []
            for e in path:
                if e.lower() in rset:
                    print "Duplicate:", e
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
                    print "Path does not exist:", p
            return r

        process_paths([check_existing], arg.commit)


    def search(arg):
        """ Search path for files matching a pattern """

        patterns = [p if '*' in p else p+"*" for p in arg.pattern]
        def search_path(path):
            for p in path:
                ep = os.path.expandvars(p)
                ents = os.listdir(ep)

                #print ents
                hits = set()
                for pat in patterns:

                    hits.update(h for h in ents if fnmatch.fnmatch(h,pat))

                if hits:
                    print p
                    print " " + " ".join(hits)
            return None

        process_paths([search_path], None)

    def longnames(arg):
        """ Show long names for all entries in path """
        def to_long(path):
            for p in path:
                long = get_long_path_name(p)
                if p != long:

                    print p, "->", long
                else:
                    print p
            return None

        process_paths([to_long], None)

    def factor(arg):
        print "Factor", arg
        var = arg.variable
        val = arg.value
        def factor_out(path):
            r = []
            for p in path:
                replaced = p.replace(val, "%" + var + "%")
                if replaced != p:
                    print "Can replace:", p,"->", replaced
                r.append(replaced)
            return r


        if arg.commit and var in os.environ:
            print "Cannot factor out against existing environment variable. Please remove:",var

        process_paths([factor_out], arg.commit)
        if arg.commit:
            Win32Environment('system').setenv(var, val)


    def sset(arg):
        Win32Environment("system").setenv(arg.variable, arg.value)
        broadcast_settingschanged()

    def sync(arg):
        broadcast_settingschanged()

    def add_s(arg):
        e = Win32Environment('system')
        oldpath = e.getenv("PATH")
        oldpath_l = oldpath.lower().split(";")
        newpath = oldpath.split(";")
        for d in arg.directory:
            d = os.path.abspath(d)
            if d.lower() in oldpath_l:
                print "Skip existing:", d
                continue

            newpath.append(d)
            print "Add:",d
        if not arg.commit:
            print "Call with '--commit' to write changes"
            return

        e.setenv("PATH", ';'.join(newpath))

    def remove_s(arg):
        def remover(path):
            newpath = path[:]
            for d in arg.directory:
                if d in newpath:
                    print "Remove:",d
                    newpath.remove(d)
            return newpath

        process_paths([remover], arg.commit)

    pp = argparse.ArgumentParser(prog = "wpathr",
    description="PATH optimization and management utility for Windows",
    epilog="See https://github.com/vivainio/wpathr for detailed documentation.")

    args.init(pp)
    args.sub("ls", ls, help = "List paths alphabetically")
    sqc = args.sub("squash", squash, help = "Shorten paths by squashing (convert to progra~1 format)")
    args.sub("dump", dump, help = "Dump paths to screen in original format (for backup)")
    ddc = args.sub("dedupe", dedupe, help = "Remove duplicate paths")
    exc = args.sub("exists", exists, help = "Remove nonexisting paths")
    src = args.sub("search", search, help = "Scan through path for files matching PATTERN")
    lnc = args.sub("long", longnames, help = "Show long names (progra~1 -> Program Files")
    fac = args.sub("factor", factor, help = "Factor out runs of VALUE in path to %%VARIABLE%% referenses")
    fac.arg("variable", metavar="VARIABLE")
    fac.arg("value", metavar="VALUE")
    sset = args.sub("sset", sset, help="Set SYSTEM env variable to VALUE. Like xset /s, really")
    sset.arg("variable", metavar="VARIABLE")
    sset.arg("value", metavar="VALUE")

    syc = args.sub("sync", sync, help="Notify other processes to sync the environment")

    src.arg("pattern", type=str, nargs="+")

    adc = args.sub("add", add_s, help='Add directory to System path')
    adc.arg('directory', nargs="+")

    rmc = args.sub('remove', remove_s, help="Remove directory from path")
    rmc.arg('directory', nargs="+")

    # operations that support --commit
    for a in [sqc, ddc, exc, fac, adc, rmc]:
        a.arg("--commit", action='store_true')

    args.parse()

if __name__ == "__main__":
    main()
