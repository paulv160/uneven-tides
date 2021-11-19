from typing import Callable, List
import re

import globals

from gametypes import *
class Command:

    """
    A game command. A list of these is iterated through and matched every time the user inputs something. If the regex pattern is matched,
    the onCall method will run. 
    
    Note: wrap onCall functions that take arguments inside of lambdas, because they are called with no arguments.
    """

    MATCH_ALL: RegexStr = r'.*'

    def __init__(self, name: CommandName, *, pattern: RegexStr, onCall: Callable):
        self.name: CommandName = name
        self.pattern: RegexPattern = globals.compile(pattern)
        self.onCall: Callable = onCall

    __str__ = __repr__ = lambda s, f='short': f'Command: {s.name}' + (f', /{s.pattern}/, onCall={repr(s.onCall)}' if f != 'short' else '')