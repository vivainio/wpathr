""" Quick and dirty wrapper for argparse, with the intent to be less verbose

Meant to be used like this::

    import args
    s1 = args.sub("check", do_check)
    s2 = args.sub("sign", do_sign, help="Sign the delivery")

    s2.arg("signature", metavar="SIGNATURE")

    ops = args.parse()
"""

import argparse, sys

# yes, 'p' will contain the parser

p = None
subparsers = None

def init(parser = None):
    """ module needs to be initialized by 'init'.

    Can be called with parser to use a pre-built parser, otherwise
    a simple default parser is created
    """

    global p,subparsers
    if parser is None:
        p = argparse.ArgumentParser()
    else:
        p = parser

    arg = p.add_argument

    subparsers = p.add_subparsers()


def parse():
    """ Call this after declaring your arguments
    """
    parsed = p.parse_args(sys.argv[1:])
    if parsed.func:
        parsed.func(parsed)
    return parsed

def sub(name, func,**kwarg):
    """ Add subparser

    """
    sp = subparsers.add_parser(name, **kwarg)
    sp.set_defaults(func=func)
    sp.arg = sp.add_argument
    return sp
