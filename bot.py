# bot.py
import os
from discord import embeds
import requests
import json
from io import BytesIO

import PIL.Image as Image
URL = 'https://api.scryfall.com/cards/search'

# card = 'Sword of hearth and home'
# PARAMS = {'q': card}
# r = requests.get(url = URL, params = PARAMS)
# data = r.json()
# card_data = data['data'][0]
# breakpoint()

import discord
intents = discord.Intents.default()
intents.members = True
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class CommanderGame():
    def __init__(self, players):
        self.player_list = players
        self.board_state = {}
        for player in players:
            self.board_state[player] = {'Battlefield':[],'Graveyard':[],'Exile':[], 'Hand':[], 'Card_ids': []}
    
    def add_player(self, player):
        self.player_list.append(player)
        self.board_state[player] = {'Battlefield':[],'Graveyard':[],'Exile':[],'Hand':[], 'Card_ids': []}

    def get_player_name(self, player_id):
        if type(player_id) == type(5):
            player = self.player_list[player_id]
        else:
            player = player_id
        return player

    def add_card_to_zone(self, player, card, zone):
        player = self.get_player_name(player)
        if player in self.board_state.keys():
            self.board_state[player][zone].append(card)
            self.board_state[player]['Card_ids'].append(card['name'])
            return True
        return False

    def save_board_state(self):
        with open("board_states/curr_game_state.json", "w") as json_file:
            json.dump(self.board_state, json_file)

    def load_board_state(self):
        with open("board_states/curr_game_state.json", "r") as json_file:
            self.board_state = json.load(json_file)
        self.player_list = self.board_state.keys()

    def add_card(self, player, card):
        player = self.get_player_name(player)
        if player in self.board_state.keys():
            self.board_state[player]['Battlefield'].append(card)
            self.board_state[player]['Card_ids'].append(card['name'])
            return True
        return False
    
    def draw_board(self, card_list, player, zone, save_string = None):
        if not len(card_list) > 0:
            return False
        board = discord.Embed(title=f'{player} {zone}')
        num_cards = len(card_list)
        cards_per_row = 5
        if num_cards > cards_per_row:
            first_card = card_list[0]
            size = requests.get(first_card['image_uris']['normal'])
            img = Image.open(BytesIO(size.content))
            rows = int(num_cards / cards_per_row) + 1
            width, height = img.size
            full_width = (width * cards_per_row) + ((cards_per_row - 1) * 10)
            full_height = (height * rows) + (rows * 5)
            height_interval = height + 5
            width_interval = width + 10
        elif num_cards > 0:
            cards_per_row = num_cards
            first_card = card_list[0]
            size = requests.get(first_card['image_uris']['normal'])
            img = Image.open(BytesIO(size.content))
            width, height = img.size
            
            full_height = height
            height_interval = 5
            if num_cards == 1:
                full_width = width
                width_interval = width
            else:
                full_width = (width * num_cards) + ((num_cards - 1) * 10)
                width_interval = width + 10
        final_image = Image.new('RGB', (full_width, full_height))
        print("Drawing Board")
        body = []
        for idx, card in enumerate(card_list):
            body.append(f'{self.board_state[player]["Card_ids"].index(card["name"])}: {card["name"]}')
            res = requests.get(card['image_uris']['normal'])
            card_img = Image.open(BytesIO(res.content))
            final_image.paste(card_img, ((idx % cards_per_row * width_interval), int(idx / cards_per_row) * height_interval))
        board.add_field(name=f'Card Ids', value="\n".join(body))
        if not save_string:
            save_string = f'{player}_{zone}.png'
        final_image.save(f'board_states/{save_string}')
        file = discord.File(f'board_states/{save_string}', filename=save_string)
        board.set_image(url=f'attachment://{save_string}')
        return(file,board)

    def draw_zone(self, player, zone):
        ## Draw the graveyard and exile as one Block
        if zone != 'Battlefield':
            if len(self.board_state[player][zone]) > 0:
                file, board = self.draw_board(self.board_state[player][zone], player, zone)
                return [(file, board)]
            else:
                return []
               
        ## Draw Types individually on the battlefield
        else:
            all_cards = self.board_state[player][zone]
            ##Broken into 4 types of permanents
            creatures = []
            artifacts = []
            enchantments = []
            lands = []
            battle_zones = []
            for card in all_cards:
                if "creature" in card['type_line'].lower():
                    creatures.append(card)
                if "artifact" in card['type_line'].lower():
                    artifacts.append(card)
                if "land" in card['type_line'].lower():
                    lands.append(card)
                if "enchantment" in card['type_line'].lower():
                    enchantments.append(card)
            if len(creatures) > 0:
                creature_file, creature_board = self.draw_board(creatures, player, zone, save_string=f'{player}_{zone}_creatures.png')
                creature_board.title = f'{player} {zone} creatures'
                battle_zones.append((creature_file, creature_board))
            if len(artifacts) > 0:
                artifacts_file, artifacts_board = self.draw_board(artifacts, player, zone, save_string=f'{player}_{zone}_artifacts.png')
                artifacts_board.title = f'{player} {zone} artifacts'
                battle_zones.append((artifacts_file, artifacts_board))
            if len(enchantments) > 0:
                enchantments_file, enchantments_board = self.draw_board(enchantments, player, zone, save_string=f'{player}_{zone}_enchantments.png')
                enchantments_board.title = f'{player} {zone} Enchantments'
                battle_zones.append((enchantments_file, enchantments_board))
            if len(lands) > 0:
                lands_file, lands_board = self.draw_board(lands, player, zone, save_string=f'{player}_{zone}_lands.png')
                lands_board.title = f'{player} {zone} lands'
                battle_zones.append((lands_file, lands_board))
            return battle_zones

    def get_complete_board_state(self):
        embed_list = []
        for player in self.player_list:
            for zone in ['Battlefield', 'Graveyard', 'Exile']:
                embed_list += self.draw_zone(player, zone)
        return embed_list

    def get_board_state(self):
        embed_list = []
        for player in self.player_list:
            embed_list += self.draw_zone(player, 'Battlefield')
        return embed_list

    def remove(self, player, card_id):
        #player = self.get_player_name(player)
        if player in self.board_state.keys():
            card_name = self.board_state[player]['Card_ids'][card_id]
            for card in self.board_state[player]['Battlefield']:
                if card["name"] == card_name:
                    self.board_state[player]['Battlefield'].remove(card)
                    self.board_state[player]['Graveyard'].append(card)
                    return True
    
        return False
    

class CommanderClient(discord.Client):
    def __init__(self,**kwargs):
        self.game = CommanderGame([])
        super(CommanderClient, self).__init__(**kwargs)

    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
    
    async def on_message(self, message):
        if message.author == client.user:
            return
        if message.content.startswith('!cgr'):
            split = message.content.split(' ')
            if len(split) == 1:
                command = 'board'
            else:
                command = split[1]
            ## Empty command returns board state
            if not command:
                command = 'state'
            ## Play a card command, default add it to board of user who typed it
            if command in ['play','p']:
                card = "".join(split[2:])
                if not card:
                    response = 'No card played'
                    await message.channel.send(response)
                PARAMS = {'q': card}
                r = requests.get(url = URL, params = PARAMS)
                data = r.json()
                card_data = data['data'][0]
                url = card_data['scryfall_uri']
                if ("creature" in card_data['type_line'].lower() or "artifact" in card_data['type_line'].lower() or
                    "enchantment" in card_data['type_line'].lower() or "land" in card_data['type_line'].lower()):
                    self.game.add_card(message.author.name, card_data)
                else:
                    self.game.add_card_to_zone(message.author.name, card_data, "Graveyard")
                
                ##TODO sent instant and sorcery to the graveyard
                    
                mana_cost = self.manacost_converter(card_data['mana_cost'])
                emoji_manacost = "".join([str(discord.utils.get(message.guild.emojis, name=cost))
                                            for cost in mana_cost])
                card_name = card_data['name'] + " " + emoji_manacost
                #body = [card_data['type_line']]
                body = []
                if 'oracle_text' in card_data.keys():
                    body=[card_data['oracle_text']]
                if 'power' in card_data.keys():
                    body.append(card_data['power'] + "/" + card_data['toughness'])
                body = '\n'.join(body)
                embed = discord.Embed(title=card_name, url=url)
                embed.add_field(name=card_data['type_line'],value=body)
                embed.set_thumbnail(url=card_data['image_uris']['large'])
                await message.channel.send(embed=embed)

            ## Command to return the board state
            elif command in ['state','board', 'board_state']:
                boards = self.game.get_board_state()
                for (file, embed) in boards:
                    await message.channel.send(file=file,embed=embed)

            ## make a new game with the author
            elif command in ['new', 'n']:
                username = message.author.name
                self.game = CommanderGame([username])
                res = 'Game Started'
                await message.channel.send(res)
            ## add author to game
            elif command == 'join':
                username = message.author.name
                self.game.add_player(username)
                res = f'{username} added'
                await message.channel.send(res)

            elif command in ['add','a']:
                assert len(split) > 3
                target = split[2]
                if target.beginswith("@"):
                    target = target[1:]

                card = split[3]
                PARAMS = {'q': card}
                r = requests.get(url = URL, params = PARAMS)
                data = r.json()
                card_data = data['data'][0]
                if target.isdigit():
                    target = int(target)
            
            elif command in ['remove','r']:
                assert len(split) > 3
                target_player = split[2]
                if target_player.startswith("<@"):
                    target_player = message.guild.get_member(int(target_player[3:-1])).name
                card_id = int(split[3])
                self.game.remove(target_player, card_id)\
            
            elif command in ['f','full_board']:
                boards = self.game.get_complete_board_state()
                for (file, embed) in boards:
                    await message.channel.send(file=file,embed=embed)
            
            elif command in ['save', 's', 'save_board']:
                self.game.save_board_state()

            elif command in ['load', 'l', 'load_board']:
                self.game.load_board_state()
            
                

    
    def manacost_converter(self, card_string):
        costs = ['mana'+cost[1:].lower() for cost in card_string.split('}')[:-1]]
        return costs



client = CommanderClient(intents=intents)
client.run(TOKEN)
