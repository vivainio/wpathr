""" Quick and dirty wrapper for argparse, with the intent to be less verbose

Meant to be used like this::

    import args
    s1 = args.sub("check", do_check, ["filename"])
    s1 = args.sub("sign", do_sign, ["filename"])


    ops = args.parse()

"""

import argparse, sys

p = argparse.ArgumentParser()

arg = p.add_argument

subparsers = p.add_subparsers()

def parse():
    """ Call this after declaring your arguments
    """
    parsed = p.parse_args(sys.argv[1:])
    if parsed.func:
        parsed.func(parsed)
    return parsed

def sub(name, func, arg = None, **kwarg):
    """ Add subparser

    """
    sp = subparsers.add_parser(name, **kwarg)
    sp.set_defaults(func=func)
    sp.arg = sp.add_argument
    if arg is not None:
        for a in arg:
            sp.add_argument(a, type=str)
    return sp


