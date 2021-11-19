# pyright: reportMissingImports=false
from __future__ import annotations
from typing import Any, List, Dict, Tuple

from command import Command
from item import Item
from character import Character
from globals import Direction
from gametypes import *
import globals

"""
TODO

"""

class Room:

    """
    A game room. Can contain items or characters within it.
    """

    # no longer used
    exampleMessages = globals.Collection(
            onEnter = 'You have entered the {name}.',
            onLook = 'You are in the {name}.',
            onStay = 'You are in the {name}'
        )
    
    exampleFlags = globals.Collection(
        playerHasVisited = True,
        lightOn = False,
        crateIsOpen = False
    )

    # playerHasVisited is a REQUIRED flag for every room
    def __init__(self, name: ItemName, *,
        items: List[Item] = None,
        characters: List[Character] = None,
        flags: globals.Collection[Any] = None,
        specialCommands: List[Command] = []) -> None:
        
        self.name: ItemName = name
        self.items: List[Item] = items or []
        self.characters: List[Character] = characters or []
        # dict comp does not work here SMH
        # needs to be a dict not a Collection so it can be indexed with directions
        self.dirs: Dict[Direction, Path] = {
            globals.DIRS.NORTH: Path(),
            globals.DIRS.SOUTH: Path(),
            globals.DIRS.EAST: Path(),
            globals.DIRS.WEST: Path(),
            globals.DIRS.NORTHEAST: Path(),
            globals.DIRS.NORTHWEST: Path(),
            globals.DIRS.SOUTHEAST: Path(),
            globals.DIRS.SOUTHWEST: Path(),
        }
        
        # these are special things not covered by basic commands like "open toolbox" which might add a few tool related items to the room - make them available
        self.specialCommands: List[Command] = specialCommands
        self.flags: globals.Collection[Any] = flags if flags else globals.Collection(playerHasVisited=False)
    
    __str__ = __repr__ = lambda s, f='short': f'Room({s.name})'

if __name__ == '__main__':
    k = Room('Kitchen')
    print(
        k.dirs[globals.DIRS.WEST]
    )