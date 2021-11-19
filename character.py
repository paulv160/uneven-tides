from __future__ import annotations
import re
from pprint import pprint
from typing import Any, Callable, Dict, List, NoReturn, Set

from command import Command
from gametypes import *
import globals

class GoodbyeException(Exception):

    """
    Raise this exception to end a conversation with a character (when the player says "goodbye"), and catch it right after
    """

    pass
class DialogOption:

    """
    Represents a single dialogue option when talking to a character, has (among other things) a pattern to match the user input with,
    a response to give, and a list of new dialogue options available to the player after this one.
    """

    MATCH_ALL: RegexStr = r'.*'

    DO_NOTHING: Callable = lambda: 0

    def __init__(self, name, *,
            hidden: bool = False,
            unchanged: bool = False, # whether to leave the options unchanged
            repr: str,
            pattern: RegexStr,
            response: str,
            newOptions: List[DialogOptionName],
            onCall: Callable = lambda: DialogOption.DO_NOTHING) -> None:
        
        self.name: str = name
        self.hidden: bool = hidden
        self.unchanged: bool = unchanged
        self.repr: str = repr
        self.pattern: RegexPattern = globals.compile(pattern)
        self.response: str = response
        self.newOptions: List[DialogOptionName] = newOptions
        self.onCall: Callable = onCall

class Character:

    """
    A game NPC, with which the player can interact with by talking to them or by trading items with them
    """

    exampleMessages = globals.Collection(
        onFirstTalk = 'Hello, I am Sadim. How are you doing my friend?',
        onTalk = 'Hello again habibi, how you doing today?',
        onFailedSale = 'My brother are you bull shitting?? You don\'t have that one habibi so nothing for you.',
        onLeave = 'My brother have a good day!'
    )

    exampleCommands = [
        Command('Talk to Sadim', pattern=r'hi sadim', onCall=lambda: talkTo('Sadim')),
        Command('Buy from Sadim', pattern=r'what\'s for sale?', onCall=lambda: listWares()),
        ...
    ]

    exampleAttrs = globals.Collection(
        talkedTo = False
    )

    def sayGoodbye() -> NoReturn:

        """ Raises GoodbyeException """

        raise GoodbyeException

    def __init__(self, name: CharName, *,
            messages: globals.Collection[str],
            attrs: globals.Collection[Any],
            options: List[DialogOption],
            failsafes: List[DialogOption],
            startingOptions: List[DialogOptionName],
            commands: List[Command],
            itemsForSale: Dict[ItemName, ItemName] = None) -> None:
                
        self.name: CharName = name
        self.messages: globals.Collection[str] = messages
        self.attrs: globals.Collection[Any] = attrs
        self.options: Dict[DialogOptionName, DialogOption] = {d.name: d for d in options}
        self.failsafes = failsafes
        self.currentOptions: List[DialogOptionName] = list(startingOptions)
        self.startingOptions: List[DialogOptionName] = list(startingOptions)
        self.commands: List[Command] = commands
        self.itemsForSale: Dict[ItemName, ItemName] = dict(itemsForSale) or dict()
        self.originalItemsForSale: Dict[ItemName, ItemName] = dict(itemsForSale) or dict()

    # returns the string to be printed
    def talkTo(self, message: str, debug=False) -> str:
        for optionName in self.currentOptions:
            optionObj = self.options[optionName]
            if debug:
                print(optionName)
            if optionObj.pattern.fullmatch(message.strip()):
                if debug:
                    print(f'option chosen: {optionName}')
                optionObj.onCall()
                if not optionObj.unchanged:
                    self.currentOptions = list(optionObj.newOptions)
                return optionObj.response

        # failsafes come last 

        for failsafeOption in self.failsafes:
            if debug:
                print(failsafeOption.name)
            if failsafeOption.pattern.fullmatch(message.strip()):
                if debug:
                    print(f'failsafe chosen: {failsafeOption.name}')
                self.currentOptions = list(failsafeOption.newOptions)
                return failsafeOption.response


    def listOptions(self):
        return f'[ {globals.FORMATTING.bold}' + f'{globals.FORMATTING.normal} / {globals.FORMATTING.bold}'.join(
            [self.options[o].repr for o in self.currentOptions if not self.options[o].hidden]) + f'{globals.FORMATTING.normal} ]'

    def listWares(self):
        return '\n'.join(f' {k} -> {v}' for k, v in self.itemsForSale.items())

    # for debugging

    def printCurrOptions(self):
        pprint({o: self.options[o].pattern for o in self.currentOptions}, sort_dicts=False)

