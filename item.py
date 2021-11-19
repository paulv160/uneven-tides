# pyright: reportMissingImports=false
from __future__ import annotations
from typing import Any, Callable, List, Dict

from command import Command
from gametypes import *
import globals

"""
TODO

"""

class Item:

    """
    An item in the game. Has parameters for whether it can be picked up/dropped, or used.
    """

    exampleAttrs = globals.Collection(
        taken = False,
        canCarry = True,
        canUse = True,
        alwaysUsable = False # if false, must be picked up before using
    )

    exampleMessages = globals.Collection(
            onTake = 'You took the {name}.',
            onDrop = 'You dropped the {name}.',
            onUse = 'You used the {name}.',
            onInspect = 'This {name} appears to be a regular {name}'
        )

    exampleOnCalls = {
        '_writeline': 'pass in the writeline function here',
        'use': lambda: 'this will run when an item is used on its own',
        'Lamp': lambda: 'this will run when an item is used on an item with the name Lamp',
        # and so on
        'take': lambda: 'this will run when an item is taken',
        'drop': lambda: 'this will run when an item is dropped',
        'inspect': lambda: 'this will run when an item is looked at',
        'invalid': lambda: 'this will run when an item is used in a wrong way'
    }

    # NOTE - targets is redundant sadly, you have to supply the targets[] into the list and also into the onCalls
    # will find a shortcut for this if i feel like it
    # must pass in messages - will throw an error otherwise
    # only verbose message is onInspectVerbose in self.messages
    # generally stick to this order when making items
    def __init__(self, name: ItemName, *,
            # contains a list of regex strings like r'(lamp|light)' - the same as that item's aliases
            targets: Dict[ItemName] = {},
            aliases: RegexStr,
            repr: str = None,
            # BUG possibly, every item copies the default one, so if you change exampleAttrs.taken you're gonna have problems
            attrs: globals.Collection[Any] = exampleAttrs,
            specialCommands: List[Command] = [],
            messages: globals.Collection[str] = None,
            onCalls: Dict[str, Callable] = dict()) -> None:

        self.name: ItemName = name
        self.aliases: RegexStr = aliases
        # how the name will be displayed in game
        self.repr: str = repr
        # redeclaring this so no mutability issues happen
        self.attrs: globals.Collection[Any] = attrs

        self.commands: Dict[CommandName, Command] = {
            # if this is unreadable i'm sorry, it's just a long list comprehension
            c.name: c for c in ([
                # use this
                # don't remove the self in self.aliases here
                Command(f'Inspect {name}', pattern=fr'{globals.KEYWORDS.InspectItem} ({self.aliases})', onCall=lambda: onCalls['inspect']())
            ] +
                # special commands that were passed in
            [
                x for x in specialCommands
            ])
        }

        self.useCommands: Dict[CommandName, Command] = {
            c.name: c for c in [
                Command(f'Use {name}', pattern=fr'{globals.KEYWORDS.UseItem} ({self.aliases})', onCall=onCalls['use']),
            ]
        }

        self.carryCommands: Dict[CommandName, Command] = {
            c.name: c for c in [
                Command(f'Take {name}', pattern=fr'{globals.KEYWORDS.TakeItem} ({self.aliases})', onCall=onCalls['take']),
                Command(f'Drop {name}', pattern=fr'{globals.KEYWORDS.DropItem} ({self.aliases})', onCall=onCalls['drop']),
            ]
        }

        self.targetCommands: Dict[CommandName, Command] = {
            c.name: c for c in
                # use this on [target]
                # "for target in targets" this gives you a string not an Item btw
            [
                Command(f'Use {name} on {t_name}', pattern=fr'{globals.KEYWORDS.UseItem} ({self.aliases}) on ({t_regex})', onCall=onCalls[t_name]) for t_name, t_regex in targets.items()
            ]
        }

        self.failsafeCommands: Dict[CommandName, Command] = {
            c.name: c for c in 
            [
                Command(f'Invalid Use of {name}', pattern=fr'{globals.KEYWORDS.UseItem} ({self.aliases}) on .*', onCall=onCalls['invalid'])
            ]
        }

        self.messages: globals.Collection[str] = messages
        self.onCalls: globals.Collection[Callable] = onCalls
    
    __str__ = __repr__ = lambda s, f='short': s.repr if s.repr else (('an ' if s.name[0] in 'aeiou' else 'a ') + s.name.lower()) # if f == 'game' else f'Item({s.name})'

if __name__ == '__main__':
    # NOTE broken
    Item('Poop')