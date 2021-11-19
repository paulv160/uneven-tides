import re
from typing import NamedTuple, NewType, TypeVar
from collections import namedtuple

ItemName = NewType('ItemName', str)
RoomName = NewType('RoomName', str)
CharName = NewType('CharName', str)
DialogOptionName = NewType('DialogOptionName', str)
CommandName = NewType('CommandName', str)

RegexStr = NewType('RegexStr', str)
RegexPattern = NewType('RegexPattern', re.Pattern)

TideLevel = NewType('TideLevel', int)

# room: Room
# times: List[TimeState] | TIME.All
Path = namedtuple('Path', ['room', 'accessTimes'], defaults=[None, []])