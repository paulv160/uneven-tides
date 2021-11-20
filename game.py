# pyright: reportMissingImports=false
from globals import Collection
from enum import auto
from typing import Any, Iterable, List, Dict
from pprint import pprint
import textwrap
import random
import os
import sys

from command import Command
from item import Item
from room import Room
from character import Character, DialogOption, GoodbyeException
from gametypes import *
import globals

# change this to True to see more info about the game
DEBUGGING = False
# or just this to skip the intro
SKIP_INTRO = True

class Game:
        
    def __init__(self) -> None:

        # MAIN VARS

        # these are actually initialized in setup
        self.currentRoom: Room = None
        self.rooms: Dict[RoomName, Room] = dict() # room ID => room obj
        self.items: Dict[ItemName, Item] = dict() # item ID => item obj
        self.characters: Dict[CharName, Character] = dict() # character ID => character obj
        self.inventory: Dict[ItemName, Item] = dict() # item ID => item obj

        self.time = globals.TIME.START

        # used for game settings like verbose mode which used to be here but was removed
        self.config: globals.Collection[Any] = globals.Collection(
            LINE_WRAP = 100
        )

        # used for other game state stuff like "should i show the message on look next time around?"
        self.flags: globals.Collection[Any] = globals.Collection(
            resetValue=False,
            showMsgonStay=True
            # etc
        )
        
        # used for standard global game messages
        self.messages: globals.Collection[str] = globals.Collection(
            playerDidNothing = 'You did nothing.'
        )

        # used to indicate that the player did something wrong/not allowed
        self.errors: globals.Collection[str] = globals.Collection(
            # when the direction was not recognized
            UNKNOWN_DIR = 'Which way do you want to go?',
            # when a character's name is not recognized
            UNKNOWN_NPC = 'Who?',
            # when an item is not recognized
            UNKNOWN_ITEM = 'You can\'t do that.',
            # when the user tries to use an item on an invalid target
            INVALID_ITEM_USE = 'You can\'t use it that way.',
            # when an item cannot be used because of the flags
            CANNOT_USE_ITEM = 'You can\'t seem to use that.',
            # when an item trying to be dropped is not in the inventory
            CANNOT_DROP_ITEM = 'You can\'t drop that! It\'s not in your inventory.',
            # when an item trying to be taken is not in the current room
            CANNOT_TAKE_ITEM = 'I don\'t see that in here.',
            # when an item cannot be picked up - set in Item.attrs
            CANNOT_CARRY_ITEM = 'You can\'t carry that!',
            # when an item is already in the inventory and the user tries to pick it up
            ITEM_ALREADY_IN_INV = 'You\'re already carrying that!',
            # when an item is in the current room and the user tries to drop it
            ITEM_NOT_IN_INV = 'You\'re not carrying that item.',
            # when the user input makes no sense whatsoever
            UNKNOWN_CMD = 'Command not recognized.'
        )

        self.commands: Dict[CommandName, Command] = {
            c.name: c for c in (

                # Game Commands
                # NOTE none of these lambdas should have tuples in them, define a function if you're doing that
            [   
                Command('Help', pattern=r'help( me)?', onCall=lambda: self.help()),
                Command('Look Around', pattern=fr'{globals.KEYWORDS.LookAround}', onCall=lambda: self.lookAround()),
                Command('Do Nothing', pattern=fr'{globals.KEYWORDS.DoNothing}', onCall=lambda: self.doNothing()),
                Command('Exit Game', pattern=fr'{globals.KEYWORDS.Exit}( (the )?game)?', onCall=lambda: self.exit()),
                Command('Check Inventory', pattern=r'(check (the)?)?(inventory|inv|bag|backpack)', onCall=lambda: self.showInventory()),
                Command('Open Settings', pattern=r'(open (the)?)?(game )?settings', onCall=lambda: self.settings()),
            ] + 
                # Direction Commands
            [
                Command(f'Move {d.name}', pattern=d.pattern, onCall=lambda d=d: self.move(d)) for d in globals.DIRS.values() if d is not None
            ] +
                # Failsafes
            [
                Command('Unknown Direction', pattern=fr'{globals.KEYWORDS.Move}.*', onCall=lambda: self.writeline(self.errors.UNKNOWN_DIR)),
                Command('Unknown Item', pattern=globals.collect(
                        globals.KEYWORDS.UseItem,
                        globals.KEYWORDS.TakeItem,
                        globals.KEYWORDS.DropItem
                    ) + r'.*', onCall=lambda: self.writeline(self.errors.UNKNOWN_ITEM)),
                Command('Unknown Character', pattern=fr'{globals.KEYWORDS.TalkTo}.*', onCall=lambda: self.writeline(self.errors.UNKNOWN_NPC)),
                Command('Unknown Command', pattern=Command.MATCH_ALL, onCall=lambda: self.writeline(self.errors.UNKNOWN_CMD))
            ]
        )}

        # do not modify the way this string looks in the program - will fuck up the format of it in the game
        self.INTRO_TEXT = 'You wake up staring at a blue sky, hearing the sound of seagulls overhead. As you sit up, you notice that you\'re on a beach - what looks to be a remote island with no land in sight.'
        # same goes for this
        self.titleText = \
            """
      ________            __  __                              _______     __         
     /_  __/ /_  ___     / / / /___  ___ _   _____  ____     /_  __(_)___/ /__  _____
      / / / __ \/ _ \   / / / / __ \/ _ \ | / / _ \/ __ \     / / / / __  / _ \/ ___/
     / / / / / /  __/  / /_/ / / / /  __/ |/ /  __/ / / /    / / / / /_/ /  __(__  ) 
    /_/ /_/ /_/\___/   \____/_/ /_/\___/|___/\___/_/ /_/    /_/ /_/\__,_/\___/____/  
                                                                                 
                                                                                       
        """

        self.setup()
        if not (DEBUGGING or SKIP_INTRO):
            self.title()
            self.intro()
        self.run()
        self.exit()

    # ------- IO METHODS ------- #

    def input(self, prompt: str = '') -> str:
        return input(f'\n  {prompt}\n\n> ')

    # same as writeline but without the preceding newline
    def write(self, text: str) -> None:
        print(f'  {text}')

    def writeline(self, text: str = '', end='\n') -> None:
        print(f'\n  {text}', end=end)

    def clearTerminal(self):
        os.system('printf "\ec\r                        \r"')

    def reprItemList(self, i: Iterable[Item], c=False) -> str:
        ret = ''
        if (l := list(i)):
            if len(l) == 1:
                return str(l[0])
            elif len(l) == 2:
                return f'{str(l[0])}, and {str(l[1])}' if c else f'{str(l[0])} and {str(l[1])}'
            else:
                f, *r = l
                return str(f) + ', ' + self.reprItemList(r, c=True)
        return ret

    # ------- DEBUGGING IO ------- #

    # turn DEBUGGING to true at the top of the file and all these run every game loop

    def _printCurrentRoomDirs(self):
        print(f'CURRENT ROOM DIRS: {self.currentRoom.dirs}')
    
    def _printcurrentRoomItems(self):
        print(f'CURRENT ROOM ITEMS: {self.currentRoom.items}')

    def _printInventory(self):
        print(f'INVENTORY: {self.inventory}')
    
    def _printAllInfo(self):
        self._printCurrentRoomDirs()
        self._printcurrentRoomItems()
        self._printInventory()

    # ------- GAMEPLAY METHODS ------- #

    # moves a player around once in a direction by changing the currentRoom to currentRoom.dirs[dir]
    def move(self, dir: globals.Direction) -> None:
        if (d := self.currentRoom.dirs[dir].room):
            self.writeline(self.getRoomMessage(self.currentRoom.name, f'playerWent{dir.name}'))
            self.currentRoom = d
            # this method handles flags.playerHasVisited
            self.writeline(self.getRoomMessage(self.currentRoom.name, 'onEnter'))
            self.currentRoom.flags.playerHasVisited = True
            self.flags.showMsgonStay = False
        else:
            # if currentRoom[dir] is None
            self.writeline(self.getRoomMessage(self.currentRoom.name, f'playerTried{dir.name}'))

    # adds an item from the current room's item list to the inventory, provided the command and situation make sense
    def takeItem(self, itemName: ItemName) -> None:
        itemObj: Item = self.items[itemName]
        if not itemObj.attrs.canCarry:
            self.writeline(self.errors.CANNOT_CARRY_ITEM)
        elif itemObj in self.inventory.values():
            self.writeline(self.errors.ITEM_ALREADY_IN_INV)
        else:
            self.inventory.update({itemObj.name: itemObj})
            self.currentRoom.items.remove(itemObj)
            self.writeline(self.getItemMessage(itemName, 'onTake'))
            # if you're looking here ^ chances are you got an attribute error so always make sure to include messages.onTake and onDrop if the item is carryable

    # does the reverse of the above, adding it to the current room's item list
    def dropItem(self, itemName: ItemName) -> None:
        itemObj: Item = self.items[itemName]
        if itemObj not in self.inventory.values():
            self.writeline(self.errors.ITEM_NOT_IN_INV if itemObj in self.currentRoom.items.values() else self.errors.UNKNOWN_ITEM)
        else:
            self.inventory.pop(itemObj.name)
            self.currentRoom.items.append(itemObj)
            self.writeline(self.getItemMessage(itemName, 'onDrop'))
    
    def talkToCharacter(self, charName: CharName):
        charObj = self.characters[charName]
        if charObj.attrs.talkedTo:
            self.writeline(charObj.messages.onTalk)
        else:
            self.writeline(charObj.messages.onFirstTalk)
            charObj.attrs.talkedTo = True
        self.writeline(charObj.listOptions(), end='')
        while True:
            try:
                if DEBUGGING:
                    charObj.printCurrOptions()
                if (resp := charObj.talkTo(self.input(), debug=DEBUGGING)):
                    self.writeline(resp)
            except GoodbyeException:
                self.writeline(charObj.messages.onLeave)
                break
            self.writeline(charObj.listOptions(), end='')
            
    
    # ------- MISC GAME METHODS ------- #

    # player chose to do nothing
    def doNothing(self) -> None:
        self.writeline(self.messages.playerDidNothing)

    # looks around in the current room
    def lookAround(self) -> None:
        self.flags.showMsgOnStay = False
        self.writeline(self.getRoomMessage(self.currentRoom.name, 'onLook'))

    # displays the inventory contents
    def showInventory(self) -> None:
        s = 'Your inventory '
        if (l := self.reprItemList(self.inventory.values())):
            s += 'contains ' + l
        else:
            s += 'is empty'
        s += '.'

        self.writeline(s)

    # brings up the help message
    def help(self) -> None:
        helpMsg = f'This is the help message. To play the game, type commands to interact with your surroundings. Here are some suggestions:\n look around\n go ' + \
        random.choice([d for d, r in self.currentRoom.dirs.items() if r is not None]).name.lower()
        if (validCarryableItemsInCurrentRoom := [x for x in self.currentRoom.items if x.attrs.canCarry]):
            helpMsg += f'\n take {random.choice(validCarryableItemsInCurrentRoom).name.lower()}'
        elif (validCarryableItemsInInventory := [x for x in self.inventory.values()]):
            helpMsg += f'\n drop {random.choice(validCarryableItemsInInventory).name.lower()}'
        self.writeline(helpMsg)
    
    # opens the settings menu
    def settings(self) -> None:
        self.flags.showMsgonStay = False
        showSettings = lambda: self.writeline(f'\n\t"settings" - show this message again\n\n\t"return" to the game')
        showSettings()
        while True:
            i = input('\n> ').lower().partition(' ')
            if i[0] == 'settings':
                showSettings()
            elif i[0] == 'return':
                self.flags.showMsgonStay = True
                return
            else:
                self.writeline('Sorry, I don\'t understand.')
            

    # ------- METHODS TO BE PASSED IN TO ITEMS ------- #

    # These methods are run during the game as a result of the player using certain items.
    # They should be passed into the Item constructor in onCalls (a dict).

    # used to connect two rooms during the game, not before it starts - happens to be the same as linkRooms()
    def _openDirOfRoom(self, room1Name: RoomName, dir: globals.Direction, room2Name: RoomName, bothways=True) -> None:
            room1, room2 = self.rooms[room1Name], self.rooms[room2Name]
            room1.dirs.update({dir: room2})
            if bothways:
                room2.dirs.update({dir.reverse: room1})

    # opposite of the above                
    # if bothways is False, turns A <=> B into A <= B where B is A.dirs[dir]
    # if it's true, disconnects the rooms completely
    def _closeDirOfRoom(self, roomName: RoomName, dir: globals.Direction, bothways=True) -> None:
            roomObj = self.rooms[roomName]
            if bothways:
                roomObj.dirs[dir].update({dir.reverse: None})
            roomObj.dirs.update({dir: None})
    
    # exact same method as in setup
    def _addItemToRoom(self, itemName: ItemName, roomName: RoomName) -> None:
            self.rooms[roomName].items.append(self.items[itemName])
    
    def _movePlayerToRoom(self, roomName: RoomName, textOnMove: str) -> None:
        self.currentRoom = self.rooms[roomName]
        self.currentRoom.flags.playerHasVisited = True
        self.writeline(textOnMove)

    # opposite of the above
    def _removeItemFromRoom(self, itemName: ItemName, roomName: RoomName) -> None:
            self.rooms[roomName].items.remove(self.items[itemName])
    
    def _addItemToInventory(self, itemName: ItemName):
        self.inventory.update({itemName: self.items[itemName]})

    # for consumable items - removes itself from inv when used and DOES NOT GO BACK INTO CURRENT ROOM
    def _removeItemFromInventory(self, itemName: ItemName) -> None:
        self.inventory.pop(itemName)

    # ------- SPECIFIC ROOM/ITEM/NPC METHODS ------- #

    def _giveItemToCharacter(self, itemName: ItemName, charName: CharName) -> None:
        charObj = self.characters[charName]
        if itemName not in self.inventory.keys():
            # if out of stock
            if itemName in charObj.originalItemsForSale.keys() and not itemName in charObj.itemsForSale.keys():
                self.writeline(charObj.messages.outOfStock)
                return
            self.writeline(charObj.messages.onFailedSale)
            return
        # if it's an invalid item
        elif not itemName in charObj.originalItemsForSale.keys():
            self.writeline(charObj.messages.unknownItem)
        # if it is/was a legit item
        else:
            # if out of stock
            if not itemName in charObj.itemsForSale.keys():
                self.writeline(charObj.messages.outOfStock)
                return
            # if in stock
            self.inventory.pop(itemName)
            newItemID = charObj.itemsForSale[itemName]
            self.inventory.update({newItemID: self.items[newItemID]})
            charObj.itemsForSale.pop(itemName)
            self.writeline(f'You received {self.items[newItemID].repr} in exchange for {self.items[itemName].repr}.')
    

    # ------- COMMAND STUFF ------- #

    # this method ensures that a command in the form "use object on target" has the target in either the inventory or currentRoom
    # returns false if this is not "valid"
    def evalTargetCommand(self, cmd: str) -> bool:
        if not cmd.startswith('Use'):
            return True
        _items = cmd.replace('Use ', '').split(' on ')
        targetObj = self.items[_items[1]]
        return targetObj in self.inventory.items() or targetObj in self.currentRoom.items

    def getInvCommands(self) -> Dict[CommandName, Command]:
        d: Dict[CommandName, Command] = dict()
        for i in self.inventory.values():
            # this way it accounts for all other keys including Lamp etc (the names of the targets)
            # possible BUG here later?
            d.update(i.commands)
            if i.attrs.canUse:
                d.update(i.useCommands)
            d.update(i.carryCommands)
            d.update({k: v for k, v in i.targetCommands.items() if self.evalTargetCommand(v.name)})
            d.update(i.failsafeCommands)
        return d
    
    """
    inventory items (above):
    - always get commands
    - get useCommands if they can be used
    - always get carryCommands
    - d.update({k: v for k, v in i.targetCommands.items() if self.evalTargetCommand(v.name)})
    - always get failsafes

    curr room items (below):
    - always get commands
    - get useCommands if they can be used but not carried, or if they are always usable
    - get carryCommands if they can be carried
    - d.update({k: v for k, v in i.targetCommands.items() if self.evalTargetCommand(v.name)})
    - always get failsafes
    """

    def getCurrRoomCommands(self) -> Dict[CommandName, Command]:
        d: Dict[CommandName, Command] = dict()
        for i in self.currentRoom.items:
            # all non-carryable items can be used without picking them up
            # possible BUG here later?
            d.update(i.commands)
            if i.attrs.alwaysUsable or (i.attrs.canUse and not i.attrs.canCarry):
                d.update(i.useCommands)
            if i.attrs.canCarry:
                d.update(i.carryCommands)
            d.update({k: v for k, v in i.targetCommands.items() if self.evalTargetCommand(v.name)})
            d.update(i.failsafeCommands)

        d.update({c.name: c for c in self.currentRoom.specialCommands})

        for c in self.currentRoom.characters:
            d.update({x.name: x for x in c.commands})
        return d

    # ------- OTHER IMPORTANT METHODS ------- #
    
    def checkInput(self, text: str) -> None:
        # the order really matters here so that Unknown Command is last
        # inventory items should get "use" and "drop" commands
        # current room commands should get "take" commands
        self.flags.reset()
        allCommands = dict()
        allCommands.update(self.getInvCommands())
        allCommands.update(self.getCurrRoomCommands())
        allCommands.update(self.commands)
        for _, c in allCommands.items():
            if DEBUGGING:
                print(c.__repr__(f='long'))
                #print(c)
            if (m := c.pattern.fullmatch(text.strip())):
                if DEBUGGING:
                    print(f'[{c}]: {m}')
                c.onCall()
                return
    
    # ------- PROBABLY THE LONGEST METHODS WE'RE GONNA HAVE TBH ------- #

    # REMEMBER TO ADD PLACES FOR ALL CARRYABLE ITEMS TO BE DROPPED, IN EACH ROOM
    # ...yeah this is gonna suck when we have hundreds of items
    # but worth the effort for sure and there are shortcuts we can take

    # message can be 'onEnter', 'onLook', or 'onStay'
    # THIS METHOD HANDLES ONFIRSTENTER by checking room.flags.playerHasVisited
    def getRoomMessage(self, roomName: RoomName, message: str) -> str:

        # helper methods - make use of these and self.reprItemList to create the shit

        def itemInRoom(itemName: ItemName, roomName: RoomName) -> bool:
            return self.items[itemName] in self.rooms[roomName].items
        
        # filters the list given and the return value can be evaluated as a bool btw
        def anyInRoom(itemList: List[ItemName], roomName: RoomName) -> List[Item]:
            return [self.items[i] for i in itemList if self.items[i] in self.rooms[roomName].items]

        def playerVisitedRoom(roomName: RoomName) -> bool:
            return self.rooms[roomName].flags.playerHasVisited

        s = ''
        roomObj = self.rooms[roomName]
        
        match roomName:

        # ------- NE COAST ------- #
        
            case 'Northeast Coast':

                match message:
                    
                    case m if m in (options := {
                        'playerWentNorth': None,
                        'playerWentSouth': None,
                        'playerWentEast': None,
                        'playerWentWest': None,
                        'playerWentNortheast': None,
                        'playerWentNorthwest': None,
                        'playerWentSoutheast': None,
                        'playerWentSouthwest': None,
                    }).keys():
                        return options[m] or f'You went {m.replace("playerWent", "").lower()}.'
                
                    case m if m in (options := {
                        'playerTriedNorth': None,
                        'playerTriedSouth': None,
                        'playerTriedEast': None,
                        'playerTriedWest': None,
                        'playerTriedNortheast': None,
                        'playerTriedNorthwest': None,
                        'playerTriedSoutheast': None,
                        'playerTriedSouthwest': None,
                    }).keys():
                            return options[m] or 'You can\'t go that way.'

                    
                return {
                    'onEnter': 'You reached the northeast coast. ',
                    'onLook': 'Nothing here but sand and your footprints. ',
                    'onStay': 'You are on the beach. '
                }[message]

        # ------- N COAST ------- #
        
            case 'Northern Coast':

                match message:
                    
                    case m if m in (options := {
                        'playerWentNorth': None,
                        'playerWentSouth': None,
                        'playerWentEast': None,
                        'playerWentWest': None,
                        'playerWentNortheast': None,
                        'playerWentNorthwest': None,
                        'playerWentSoutheast': None,
                        'playerWentSouthwest': None,
                    }).keys():
                        return options[m] or f'You went {m.replace("playerWent", "").lower()}.'
                
                    case m if m in (options := {
                        'playerTriedNorth': None,
                        'playerTriedSouth': None,
                        'playerTriedEast': None,
                        'playerTriedWest': None,
                        'playerTriedNortheast': None,
                        'playerTriedNorthwest': None,
                        'playerTriedSoutheast': None,
                        'playerTriedSouthwest': None,
                    }).keys():
                            return options[m] or 'You can\'t go that way.'

                return {
                    'onEnter': 'You reached the northernmost coast. ' if roomObj.flags.playerHasVisited else 'You reached the north coast of the island. ',
                    'onLook': 'The beach stretches as far as the eye can see to the southwest and southeast. ',
                    'onStay': 'You are on the northern coast. '
                }[message]

        # ------- NW COAST ------- #
        
            case 'Northwest Coast':

                match message:
                    
                    case m if m in (options := {
                        'playerWentNorth': None,
                        'playerWentSouth': None,
                        'playerWentEast': None,
                        'playerWentWest': None,
                        'playerWentNortheast': None,
                        'playerWentNorthwest': None,
                        'playerWentSoutheast': None,
                        'playerWentSouthwest': None,
                    }).keys():
                        return options[m] or f'You went {m.replace("playerWent", "").lower()}.'
                
                    case m if m in (options := {
                        'playerTriedNorth': None,
                        'playerTriedSouth': None,
                        'playerTriedEast': None,
                        'playerTriedWest': None,
                        'playerTriedNortheast': None,
                        'playerTriedNorthwest': None,
                        'playerTriedSoutheast': None,
                        'playerTriedSouthwest': None,
                    }).keys():
                            return options[m] or 'You can\'t go that way.'

                    
                return {
                    'onEnter': 'You reached the northwest coast. ' if roomObj.flags.playerHasVisited else 'You reached the northwest coast of the island. ',
                    'onLook': 'To the southwest, you can barely make out a dark shape sticking out of the sand, and the beach stretches northeast. ',
                    'onStay': 'You are on the northwest coast. '
                }[message]

        # ------- SHIPWRECK ------- #
        
            case 'Shipwreck':

                match message:
                    
                    case m if m in (options := {
                        'playerWentNorth': None,
                        'playerWentSouth': None,
                        'playerWentEast': None,
                        'playerWentWest': None,
                        'playerWentNortheast': None,
                        'playerWentNorthwest': None,
                        'playerWentSoutheast': None,
                        'playerWentSouthwest': None,
                    }).keys():
                        return options[m] or f'You went {m.replace("playerWent", "").lower()}.'
                
                    case m if m in (options := {
                        'playerTriedNorth': None,
                        'playerTriedSouth': None,
                        'playerTriedEast': None,
                        'playerTriedWest': None,
                        'playerTriedNortheast': None,
                        'playerTriedNorthwest': None,
                        'playerTriedSoutheast': None,
                        'playerTriedSouthwest': None,
                    }).keys():
                            return options[m] or 'You can\'t go that way.'

                # TODO
                # - make sandbar text tide-dependent ("underwater")
                # - review boat name
                # - supply crate is open/closed
                return {
                    'onEnter': 'You reached the shipwreck. ' if roomObj.flags.playerHasVisited else 'Ahead of you, half-buried in the sand, lies a broken fiberglass boat. ',
                    'onLook': 'You are at the shipwreck on the western side of the island. The boat is still in fair condition, aside from the fact that it\'s been cracked open like an egg. ' +
                                'Walking around to the back, you notice a faded inscription: "King of the Blue Tides". A small supply crate lies next to the wreck. ' +
                                'An underwater sandbar extends to the west, ' +
                                'the beach extends far to the northeast and southeast, and there is an open field to the east. ',
                    'onStay': 'You are on the northwest coast. '
                }[message]

        # ------- W COAST ------- #
        
            case 'Western Coast':

                match message:
                    
                    case m if m in (options := {
                        'playerWentNorth': None,
                        'playerWentSouth': None,
                        'playerWentEast': None,
                        'playerWentWest': None,
                        'playerWentNortheast': None,
                        'playerWentNorthwest': None,
                        'playerWentSoutheast': None,
                        'playerWentSouthwest': None,
                    }).keys():
                        return options[m] or f'You went {m.replace("playerWent", "").lower()}.'
                
                    case m if m in (options := {
                        'playerTriedNorth': None,
                        'playerTriedSouth': None,
                        'playerTriedEast': None,
                        'playerTriedWest': None,
                        'playerTriedNortheast': None,
                        'playerTriedNorthwest': None,
                        'playerTriedSoutheast': None,
                        'playerTriedSouthwest': None,
                    }).keys():
                            return options[m] or 'You can\'t go that way.'

                # TODO
                # lights at night coming from the west
                # underwater sandbar conditional
                return {
                    'onEnter': 'You reached the western coast. ' if roomObj.flags.playerHasVisited else 'You reached the western coast of the island. ',
                    'onLook': 'There is an underwater sandbar to the east, and nothing but the ocean to the west. ',
                    'onStay': 'You are on the western coast. '
                }[message]
        
        # ------- SW COAST ------- #
        
            case 'Southwest Coast':

                match message:
                    
                    case m if m in (options := {
                        'playerWentNorth': None,
                        'playerWentSouth': None,
                        'playerWentEast': None,
                        'playerWentWest': None,
                        'playerWentNortheast': None,
                        'playerWentNorthwest': None,
                        'playerWentSoutheast': None,
                        'playerWentSouthwest': None,
                    }).keys():
                        return options[m] or f'You went {m.replace("playerWent", "").lower()}.'
                
                    case m if m in (options := {
                        'playerTriedNorth': None,
                        'playerTriedSouth': None,
                        'playerTriedEast': None,
                        'playerTriedWest': None,
                        'playerTriedNortheast': None,
                        'playerTriedNorthwest': None,
                        'playerTriedSoutheast': None,
                        'playerTriedSouthwest': None,
                    }).keys():
                            return options[m] or 'You can\'t go that way.'

                # TODO
                # lights at night coming from the west
                # underwater sandbar conditional
                return {
                    'onEnter': 'You reached the southwest coast. ' if roomObj.flags.playerHasVisited else 'You reached the southwestern coast of the island. ',
                    'onLook': 'You are on the southwest coast. There is an underwater sandbar to the east. ',
                    'onStay': 'You are on the southwest coast. '
                }[message]

        return s
    
    def getItemMessage(self, itemName: ItemName, message: str) -> str:
        
        """
        message should be one of the following: onTake, onDrop, onInspect, onUse, invalidUse
        """

        return {
            'Dull Rock': {
                'onTake': 'You picked up the dull rock.',
                'onDrop': 'You dropped the dull rock.',
                'onInspect': 'This rock is very dull and has some grains of sand stuck to it.',
                'onUse': 'You used the dull rock.',
                'invalidUse': 'You can\'t use the dull rock that way.'
            },
            'Shiny Rock': {
                'onTake': 'You picked up the shiny rock.',
                'onDrop': 'You dropped the shiny rock.',
                'onInspect': 'This rock is very shiny. You bought it from the old man.',
                'onUse': 'You used the shiny rock.',
                'invalidUse': 'You can\'t use the shiny rock that way.'
            }
        }[itemName][message]

    # ------- GAME SEQUENCE METHODS ------- #

    def setup(self) -> None:

        # methods used to connect rooms and items together
        def linkRooms(room1Name: RoomName, dir: globals.Direction, room2Name: RoomName, bothways=True, accessTimes: List[globals.TimeState] = None) -> None:
            _accessTimes = accessTimes if accessTimes else globals.TIME.All
            room_a, room_b = self.rooms[room1Name], self.rooms[room2Name]
            room_a.dirs.update({dir: Path(room_b, _accessTimes)})
            if bothways:
                room_b.dirs.update({dir.reverse: Path(room_a, _accessTimes)})

        def addItemToRoom(itemName: ItemName, roomName: RoomName) -> None:
            if DEBUGGING:
                print(f'{self.items[itemName].name} => {self.rooms[roomName]}')
            self.rooms[roomName].items.append(self.items[itemName])

        def addCharacterToRoom(charName: CharName, roomName: RoomName) -> None:
            if DEBUGGING:
                print(f'{self.characters[charName].name} => {self.rooms[roomName]}')
            self.rooms[roomName].characters.append(self.characters[charName])

        # constructing room, item, and character dictionaries 
        self.rooms.update({
            r.name: r for r in [
                Room('Northeast Coast'), # where the player starts
                Room('Cliff Top'),
                Room('Cliff Coast'),
                Room('Saltwater Pond'),
                Room('Southeast Coast'),
                Room('Southeast Island'),
                Room('Cove'),
                Room('Hermit Cave'),
                Room('Southern Coast'),
                Room('Southwest Coast'),
                Room('Abandoned Dock'),
                Room('Field'),
                Room('Shipwreck'),
                Room('Western Coast'),
                Room('Northwest Coast'),
                Room('North Coast'),
                Room('Woods 1'),
                Room('Woods 2'),
                Room('Clearing'),
                Room('Mountain South'),
                Room('Mountain East'),
                Room('Mountain Trail'),
                Room('Mountain Summit')
            ]
        })

        # linking rooms together

        [
            linkRooms(*a) for a in [
                # remember bothways=True
                ('Northeast Coast', globals.DIRS.SOUTHEAST, 'Cliff Coast'),
                ('Northeast Coast', globals.DIRS.SOUTH, 'Cliff Top'),
                ('Northeast Coast', globals.DIRS.NORTHWEST, 'North Coast'),
                ('Cliff Coast', globals.DIRS.SOUTHWEST, 'Saltwater Pond'),
                ('Cliff Top', globals.DIRS.EAST, 'Mountain East'),
                ('Cliff Top', globals.DIRS.SOUTH, 'Saltwater Pond'),
                ('North Coast', globals.DIRS.SOUTHWEST, 'Northwest Coast'),
                ('Saltwater Pond', globals.DIRS.NORTHWEST, 'Mountain East'),
                ('Saltwater Pond', globals.DIRS.SOUTHEAST, 'Southeast Coast'),
                ('Mountain East', globals.DIRS.NORTHWEST, 'Mountain Trail'),
                ('Northwest Coast', globals.DIRS.SOUTHWEST, 'Shipwreck'),
                ('Northwest Coast', globals.DIRS.SOUTHEAST, 'Woods 2'),
                ('Southeast Coast', globals.DIRS.SOUTHEAST, 'Southeast Island', globals.TIME.LowTide),    # low tide
                ('Southeast Coast', globals.DIRS.WEST, 'Cove'),
                ('Mountain Trail', globals.DIRS.NORTH, 'Mountain Summit'),
                ('Mountain Trail', globals.DIRS.SOUTH, 'Mountain South'),
                ('Shipwreck', globals.DIRS.WEST, 'Western Coast', globals.TIME.LowTide),                  # low tide
                ('Shipwreck', globals.DIRS.EAST, 'Field'),
                ('Shipwreck', globals.DIRS.SOUTHEAST, 'Southwest Coast'),
                ('Woods 2', globals.DIRS.NORTHEAST, 'Mountain South'),
                ('Woods 2', globals.DIRS.SOUTHWEST, 'Woods 1'),
                ('Woods 2', globals.DIRS.SOUTHEAST, 'Clearing'),
                ('Cove', globals.DIRS.NORTH, 'Hermit Cave', globals.TIME.LowTide),                        # low tide
                ('Cove', globals.DIRS.SOUTH, 'Southern Coast'),
                ('Field', globals.DIRS.SOUTHEAST, 'Woods 1'),
                ('Woods 1', globals.DIRS.EAST, 'Clearing'),
                ('Woods 1', globals.DIRS.SOUTH, 'Southwest Coast'),
                ('Southwest Coast', globals.DIRS.SOUTHEAST, 'Southern Coast'),
                ('Southwest Coast', globals.DIRS.SOUTHWEST, 'Abandoned Dock', globals.TIME.HighTide),     # high tide
            ]
        ]

        self.items.update({
            i.name: i for i in [

                # targets = ['Name|Alias1|Alias2...', 'Name', 'Name|Alias'...]
                # inspect is now implicitly added to onCalls - just prints out messages.onInspect or onInspectVerbose

                # NOTE if an item is not carryable, the onCalls should contain 
                # {
                #   'take': lambda: self.writeline(self.errors.CANNOT_CARRY_ITEM),
                #   'drop': lambda: self.writeline(self.errors.ITEM_NOT_IN_INV)                 
                # }
                
                Item('Dull Rock', aliases=r'dull rock', repr='a dull rock',
                    attrs = globals.Collection(
                        canCarry = True,
                        canUse = False,
                        alwaysUsable = False # if false, must be picked up before using
                    ), messages = globals.Collection(), onCalls = {
                        'use': lambda: self.writeline('You can\'t use that'),
                        'take': lambda: self.takeItem('Dull Rock'),
                        'drop': lambda: self.dropItem('Dull Rock'),
                        'inspect': lambda: self.writeline(self.getItemMessage('Dull Rock', 'onInspect')),
                        'invalid': lambda: self.writeline(self.getItemMessage('Dull Rock', 'invalidUse')),
                    }
                ),
                Item('Shiny Rock', aliases=r'shiny rock', repr='a shiny rock',
                    attrs = globals.Collection(
                        canCarry = True,
                        canUse = False,
                        alwaysUsable = False # if false, must be picked up before using
                    ), messages = globals.Collection(), onCalls = {
                        'use': lambda: self.writeline('You can\'t use that'),
                        'take': lambda: self.takeItem('Shiny Rock'),
                        'drop': lambda: self.dropItem('Shiny Rock'),
                        'inspect': lambda: self.writeline(self.getItemMessage('Shiny Rock', 'onInspect')),
                        'invalid': lambda: self.writeline(self.getItemMessage('Shiny Rock', 'invalidUse')),
                    }
                ),

            ]
        })

        

        # adding items to rooms

        [
            addItemToRoom(*a) for a in [
                ('Dull Rock', 'Northeast Coast')
            ]
        ]

        self.characters.update({
            c.name: c for c in [
                Character('Old Man', messages = globals.Collection(
                    onFirstTalk = 'Hello, I am Sadim. How are you doing my friend?',
                    onTalk = 'Hello again habibi, how you doing today?',
                    displayShopItems = 'Here is what is for sale today my friend:',
                    onFailedSale = 'My brother are you bull shitting?? You don\'t have that one habibi so nothing for you.',
                    unknownItem = 'You so crazy you not making sense habibi. Don\'t know what that one is.',
                    outOfStock = 'No longer for sale my brother.',
                    onLeave = 'My brother have a good day!'
                ), attrs = globals.Collection(
                    talkedTo = False
                ), options = [
                    
                    DialogOption('Greeting',
                        repr='How are you doing?',
                        pattern=r'(how are you doing)(\?)?',
                        response='I am good.',
                        newOptions=['Greeting', 'Location', 'Shop', 'Goodbye', 'Dull Rock -> Shiny Rock']),
                    DialogOption('Location',
                        repr='Where am I?',
                        pattern=r'(where (am i)|(are we))(\?)?',
                        response='We are on the beach my friend.',
                        newOptions=['Greeting', 'Location', 'Beach Location', 'Shop', 'Goodbye', 'Dull Rock -> Shiny Rock']),
                    DialogOption('Beach Location',
                        repr='Where is the beach?',
                        pattern=r'where is the beach',
                        response='Beach is on the island.',
                        newOptions=['Greeting', 'Location', 'Shop', 'Goodbye', 'Dull Rock -> Shiny Rock']),
                    DialogOption('Shop',
                        repr='What\'s for sale?',
                        pattern=r"(what's for sale)(\?)?",
                        response=None,
                        newOptions=['Greeting', 'Location', 'Shop', 'Goodbye', 'Dull Rock -> Shiny Rock'],
                        onCall=lambda: self.writeline(
                                f'Here is what I have today my friend:\n {self.characters["Old Man"].listWares()}'
                            if self.characters['Old Man'].itemsForSale else
                                f'Nothing for sale today habibi :(')),
                    DialogOption('Goodbye',
                        repr='Goodbye.',
                        pattern=r'(good)?bye',
                        response='See you later my friend!',
                        newOptions=['Greeting', 'Location', 'Shop', 'Goodbye', 'Dull Rock -> Shiny Rock'],
                        onCall=lambda: Character.sayGoodbye()),

                    # shop cmds

                    DialogOption('Dull Rock -> Shiny Rock',
                        hidden=True,
                        repr='Buy Shiny Rock',
                        pattern=globals.collect(
                            fr'{globals.KEYWORDS.SellItem} (dull )?rock( to old man)?',
                            fr'{globals.KEYWORDS.BuyItem} shiny rock( from old man)?'
                        ),
                        response=None,
                        newOptions=['Greeting', 'Location', 'Shop', 'Goodbye', 'Dull Rock -> Shiny Rock'],
                        onCall=lambda: self._giveItemToCharacter('Dull Rock', 'Old Man')),

                    # FAILSAFES COME LAST ALWAYS :)

                ], failsafes=[
                    DialogOption('Buy/Sell Unknown Item',
                        hidden=True,
                        repr='Buy Shiny Rock',
                        pattern=globals.collect(
                            fr'{globals.KEYWORDS.SellItem}.*( to old man)?',
                            fr'{globals.KEYWORDS.BuyItem}.*( from old man)?'
                        ),
                        response='Not for sale habibi.',
                        newOptions=['Greeting', 'Location', 'Shop', 'Goodbye', 'Dull Rock -> Shiny Rock']),
                    DialogOption('Unknown',
                        repr='you should not be seeing this',
                        pattern=DialogOption.MATCH_ALL,
                        response = 'You not making sense.',
                        newOptions=['Greeting', 'Location', 'Shop', 'Goodbye', 'Dull Rock -> Shiny Rock']),
                ], 
                startingOptions=[
                    'Greeting',
                    'Location',
                    'Shop',
                    'Goodbye',
                    'Dull Rock -> Shiny Rock'
                ], commands=[
                    Command('Talk to Old Man', pattern=fr'{globals.KEYWORDS.TalkTo} old man', onCall=lambda: self.talkToCharacter('Old Man')),
                    Command('Sell Dull Rock to Old Man', pattern=globals.collect(
                        fr'{globals.KEYWORDS.SellItem} (dull )?rock( to old man)?',
                        fr'{globals.KEYWORDS.BuyItem} shiny rock( from old man)?'
                    ), onCall=lambda: self._giveItemToCharacter('Dull Rock', 'Old Man')),
                    Command('Sell Unknown Item to Old Man', pattern=globals.collect(
                        fr'{globals.KEYWORDS.SellItem}.*( to old man)?',
                        fr'{globals.KEYWORDS.BuyItem}.*( from old man)?'
                    ), onCall=lambda: self.writeline('Not for sale habibi.'))
                ], itemsForSale={
                    'Dull Rock': 'Shiny Rock'
                })
            ]
        })

        # adding characters to rooms
        [
            addCharacterToRoom(*a) for a in [
                ('Old Man', 'Northeast Coast')
            ]
        ]

        self.currentRoom = self.rooms['Northeast Coast']
        self.currentRoom.flags.playerHasVisited = True

        self.clearTerminal()
        
        # END OF GAME SETUP

    def title(self) -> None:
        print(self.titleText)
        while True:
            self.writeline('Type "start", "exit", or "settings".')
            i = self.input().lower()
            if i == 'start':
                return
            elif i == 'exit':
                self.exit(auto=True)
            elif i == 'settings':
                self.settings()

    # displays the intro text
    def intro(self) -> None:
        self.writeline()
        self.writeline(self.INTRO_TEXT)

    def run(self) -> None:

        while True:
            try:
                if DEBUGGING:
                    self._printAllInfo()
                if self.flags.showMsgonStay:
                    message = self.getRoomMessage(self.currentRoom.name, 'onStay')
                    self.checkInput(self.input(message))
                else:
                    self.checkInput(input('\n> '))
            except KeyboardInterrupt:
                self.exit()

    def exit(self, auto=False) -> None:
        if not auto:
            self.flags.showMsgonStay = False
            self.writeline('Are you sure you want to exit? y/n')
            while True:
                i = input('\n> ').lower()
                if i in ('y', 'yes'):
                    self.writeline('Thanks for playing!')
                    break
                elif i in ('n', 'no'):
                    self.flags.showMsgonStay = True
                    return
                else:
                    # TODO make this an error in self.errors? fine either way tbh
                    self.writeline('Sorry, I don\'t understand.')
        sys.exit()
        
if __name__ == '__main__':
    Game()
