import os
import ctypes
from ctypes import wintypes
from collections import OrderedDict
import _winreg
import args

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
            
        newpath = ";".join(cur_path)
        print sc,":="
        print newpath
        if commit:
            env.setenv("PATH", newpath)
    if not commit:
        print "Call with '--commit' to commit changes to env registry"


def main():
    def ls(a):
        eu = Win32Environment(scope='user')
        print "\n\n*** USER: ***\n"
        print "\n".join(sorted(eu.getenv("PATH").split(";")))

        es = Win32Environment(scope='system')
        print "\n\n*** SYSTEM: ***\n"
        print "\n".join(sorted(es.getenv("PATH").split(";")))

    def squash(arg):
        for sc in ['user', 'system']:
            env = Win32Environment(scope=sc)
            oldpath = env.getenv("PATH")

            newpath = ";".join(shorten_path(oldpath.split(";")))
            print sc,":="
            print newpath
            if arg.commit:
                env.setenv("PATH", newpath)


        if not arg.commit:
            print "Call 'wpathr.py squash --commit' to commit changes to env registry"
        else:
            print "Committed changes to registry"
            #print newpath

    def dump(arg):
        for sc in ['user', 'system']:
            env = Win32Environment(scope=sc)
            oldpath = env.getenv("PATH")
            print sc, ":="
            print oldpath

    def dedupe(arg):
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
            
            
    args.sub("ls", ls)
    sq = args.sub("squash", squash)
    args.sub("dump", dump)
    dd = args.sub("dedupe", dedupe)
    for a in [sq, dd]:
        a.add_argument("--commit", action='store_true')

    args.parse()

if __name__ == "__main__":
    main()
