# pyright: reportMissingImports=false
from __future__ import annotations
from pprint import pprint
from typing import Any, Callable, Dict, Generator, Generic, ItemsView, Iterable, KeysView, List, Set, TypeVar, ValuesView, Iterator
from blessed import Terminal

from gametypes import *

T = TypeVar('T')

class Collection(Generic[T]):

    """
    
    To be used for collections of game flags, item attrs, room messages, etc.

    Better than a dictionary since items are accessed directly.

    keys(), values(), items() - access certain parts of the internal dictionary

    reset - resets the Collection to the value given.

    """


    def __init__(self, resetValue=None, **attrs) -> None:
        self.__dict__.update(attrs)
        self.resetValue = resetValue

    def __getitem__(self, item: T) -> T:
        return self.__dict__.__getitem(item)
    
    def __setitem__(self, k: str, new: T) -> None:
        self.__dict__.__setitem__(k, new)

    def __iter__(self) -> Iterator[T]:
        return self.__dict__.__iter__()
    
    def __next__(self) -> T:
        return self.__iter__.__next__()
    
    def keys(self) -> KeysView[T]:
        return self.__dict__.keys()
    
    def values(self) -> ValuesView[T]:
        return self.__dict__.values()
    
    def items(self) -> ItemsView[T]:
        return self.__dict__.items()
    
    def reset(self) -> None:
        self.__dict__.update({k: self.resetValue for k in self.__dict__.keys()})
 
class CycleGen(Generic[T]):

    """
    Yields objects from the given iterable in a cycle, with easy __call__ syntax (no bullshit generator wrapper functions)
    """

    def __init__(self, iter: Iterable[T]) -> None:
        self.iter: Iterable[T] = iter
        def _gen():
            yield from self.iter
        self.gen: Generator = _gen()
    
    def __call__(self) -> T:
        try:
            return self.gen.__next__()
        except StopIteration:
            self.reset()
            return self.gen.__next__()


    def reset(self) -> None:
        def _gen():
            yield from self.iter
        self.gen = _gen()

                                                            ### ------- DIRECTION STUFF ------- ###
class Direction:

    """
    Represents a direction the player can move in, and the options are defined in globals.Collection (sort of like an enum)
    """

    def __init__(self, name, *, pattern: str, reverse: Direction = None):
        self.name = name
        self.pattern = pattern
        self.reverse = reverse
    
    __str__ = __repr__ = lambda s, f='short': f'Dir({s.name})'
    
    def __hash__(self) -> int:
        return self.name.__hash__()

    def __eq__(self, o: object) -> bool:
        return self.name == o.name if isinstance(o, Direction) else NotImplemented

# the patterns will be compiled through the command constructor in the actual game
# for now they are just strings
DIRS: Collection[Direction] = Collection(
    NORTH = Direction('North', pattern=r'(go )?(n|north)'),
    SOUTH = Direction('South', pattern=r'(go )?(s|south)'),
    EAST = Direction('East', pattern=r'(go )?(e|east)'),
    WEST = Direction('West', pattern=r'(go )?(w|west)'),
    NORTHEAST = Direction('Northeast', pattern=r'(go )?(ne|northeast)'),
    NORTHWEST = Direction('Northwest', pattern=r'(go )?(nw|northwest)'),
    SOUTHEAST = Direction('Southeast', pattern=r'(go )?(se|southeast)'),
    SOUTHWEST = Direction('Southwest', pattern=r'(go )?(sw|southwest)'),
)

# potential source of bugs later on
def _dirs_iter(self) -> Direction:
    yield from [
        self.NORTH,
        self.SOUTH,
        self.EAST,
        self.WEST,
        self.NORTHEAST,
        self.NORTHWEST,
        self.SOUTHEAST,
        self.SOUTHWEST,
    ]

# so uncomment this if you really need it
# DIRS.__iter__ = _dirs_iter

DIRS.NORTH.reverse = DIRS.SOUTH
DIRS.SOUTH.reverse = DIRS.NORTH
DIRS.EAST.reverse = DIRS.WEST
DIRS.WEST.reverse = DIRS.EAST
DIRS.NORTHEAST.reverse = DIRS.SOUTHWEST
DIRS.NORTHWEST.reverse = DIRS.SOUTHEAST
DIRS.SOUTHEAST.reverse = DIRS.NORTHWEST
DIRS.SOUTHWEST.reverse = DIRS.NORTHEAST


                                                            ### ------- KEYWORD STUFF ------- ###

# keywords
# set used here for quick 'in' checking, can use list 
STR_KEYWORDS: Collection[Set[str]] = Collection(

    TakeItem = {
        'take',
        'pick up',
        'grab'
    },
    DropItem = {
        'drop',
        'throw away',
        'put down',
        'discard'
    },
    InspectItem = {
        'look at',
        'inspect'
    },
    UseItem = {
        'use'
    },
    BuyItem = {
        'buy',
        'purchase',
        'trade'
    },
    SellItem = {
        'sell',
        'give'
    },
    TalkTo = {
        'talk to',
        'talk with',
        'speak to',
        'speak with'
    },
    Move = {
        'move',
        'go',
        'travel'
    },
    LookAround = {
        'look',
        'look around',
    },
    DoNothing = {
        'wait',
        'do nothing'
    },
    Exit = {
        'quit',
        'exit',
        'leave'
    }
)

                                                            ### ------- TIDE/TIME STUFF ------- ###



class TimeState:
    def __init__(self, name: str, repr: str, tideLevel: TideLevel) -> None:
        self.name = name
        self.repr = repr
        self.tideLevel = tideLevel
    
    __str__ = __repr__ = lambda s, _='': f'{s.name} time ({s.repr})'

TIME: Collection[TimeState] = Collection(
    Afternoon = TimeState('Afternoon', '3:00 PM', 3),
    Evening = TimeState('Evening', '6:00 PM', 4),
    Sunset = TimeState('Sunset', '9:00 PM', 3),
    Midnight = TimeState('Midnight', '12:00 AM', 2),
    Night = TimeState('Night', '3:00 AM', 1),
    Sunrise = TimeState('Sunrise', '6:00 AM', 0),
    Morning = TimeState('Morning', '9:00 AM', 1),
    Noon = TimeState('Noon', '12:00 PM', 2),
)

TIME.All = [
    TIME.Afternoon,
    TIME.Evening,
    TIME.Sunset,
    TIME.Midnight,
    TIME.Night,
    TIME.Sunrise,
    TIME.Morning,
    TIME.Noon
]

TIME.advance = CycleGen(TIME.All)

# more constants
TIME.START = TIME.Afternoon
TIME.LowTide = [TIME.Evening]
TIME.HighTide = [TIME.Sunrise]

                                                            ### ------- MISC ------- ###

# used for text formatting
_term = Terminal()
FORMATTING: Collection[str] = Collection(
    normal = _term.normal,
    bold = _term.bold
)

class ReturnToMenu(Exception):

    """
    Raise this exception in the game when the user wants to quit, to return to the menu.
    """
    
    pass

# allows you to pass in a list of regex strings and joins them into one string (inefficiently - can be a long string)
# ex. ['what\'s up', 'how are you doing', ...] -> r'(what\'s up)|(how are you doing)|...'
def collect(*options: List[str]) -> RegexStr:

    """
    allows you to pass in a list of regex strings and joins them into one string (inefficiently - can be a long string).
    
    ex. ['what\'s up', 'how are you doing', ...] -> r'(what\'s up)|(how are you doing)|...'
    
    Used in the DialogOption and Command classes.
    """

    return '(' + ('|'.join([f'({o})' for o in options])) + ')'

def compile(pattern: RegexStr) -> RegexPattern:
    
    """
    A wrapper around re.compile that provides some small improvements (like making spaces optional)
    """

    #return re.compile(re.sub(r' ', r'( )*', pattern), re.IGNORECASE)
    return re.compile(pattern, re.IGNORECASE)

KEYWORDS: Collection[RegexStr] = Collection(
    **{name: collect(*_set) for name, _set in STR_KEYWORDS.__dict__.items() if _set is not None}
)
KEYWORDS.__dict__.pop('resetValue')

if __name__ == '__main__':
    # pprint(KEYWORDS.__dict__, sort_dicts=False)
    while True:
        __import__('time').sleep(1)
        print(TIME.advance())