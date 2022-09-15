from .card import Card
from random import shuffle, randint, random
import sqlite3
from nonebot.adapters.onebot.v11 import Bot
from models.bag_user import BagUser


def generate_cards():
    cards = []
    for i in range(52):
        cards.append(Card(i))
    return cards


class Deck:
    def __init__(self, deck_id: int, group: int, player1: int, point: int,
                 player1_name: str):
        self.deck_id = deck_id
        self.group = group
        self.player1 = player1
        self.player1_name = player1_name
        self.player2 = None
        self.player2_name = ""
        self.point = point
        self.cards = generate_cards()
        self.player1_cards = []
        self.player2_cards = []

        shuffle(self.cards)

    @property
    def player1_point(self):
        return self.get_player_card_points(1)

    @property
    def player2_point(self):
        return self.get_player_card_points(2)

    def pick_one_card(self):
        return self.cards.pop()

    def init_game(self):
        card1 = self.pick_one_card()
        card2 = self.pick_one_card()
        card3 = self.pick_one_card()
        card4 = self.pick_one_card()
        self.player1_cards += [card1, card2]
        self.player2_cards += [card3, card4]

    def get_player_card_points(self, player_num: int):
        cards = [0, self.player1_cards, self.player2_cards]
        point = 0
        ace_num = 0
        for card in cards[player_num]:
            if card.value == 1:
                ace_num += 1
            elif card.value >= 10:
                point += 10
            else:
                point += card.value
        while ace_num > 0:
            if point + 11 <= 21:
                point += 11
            else:
                point += 1
            ace_num -= 1
        return point

    def get_one_card(self, player):
        cards = [0, self.player1_cards, self.player2_cards]
        player_cards = cards[player]
        player_cards += [self.pick_one_card()]


game_ls = []


async def add_game(group: int, uid: int, point: int, player1_name: str) -> int:
    if game_ls:
        latest_deck_id = game_ls[-1].deck_id
        game_ls.append(
            Deck(latest_deck_id + 1, group, uid, point, player1_name))
        return latest_deck_id + 1
    else:
        game = Deck(1, group, uid, point, player1_name)
        game_ls.append(game)
        return game.deck_id


async def start_game(deck_id: int, player2: int, player2_name: str,
                     group_id: int, user_point: int) -> str:
    if not game_ls:
        return '目前还没有开始任何游戏！'
    for index, game in enumerate(game_ls):
        game: Deck
        if deck_id == game.deck_id and game.player2 is None and game.player1 != player2 and game.group == group_id \
                and user_point >= game.point:
            game.player2 = player2
            game.player2_name = player2_name
            game.init_game()
            player2_point = game.get_player_card_points(2)
            words = f"{game.player1_name}的牌为\n{game.player1_cards[0]} ?\n{game.player2_name}的牌为\n"
            for card in game.player2_cards:
                words += str(card)
            if player2_point == 21:
                words += f"\n黑杰克！牌点为21点\n{game.player2_name}获胜了！"
                result = await count_score(game, 2)
                words += result
                del game_ls[index]
                return words
            else:
                words += f"\n牌点为{player2_point}"
                return words
        elif deck_id == game.deck_id and game.player2 is not None:
            return '该游戏已开始！'
        elif deck_id == game.deck_id and game.player1 == player2:
            return '不能和自己玩！'
        elif deck_id == game.deck_id and game.group != group_id:
            return '不能和群外的玩！'
        elif deck_id == game.deck_id and user_point < game.point:
            return '你的点数不足以游玩该游戏！'
    return '未找到游戏！'


async def call_card(deck_id: int, player: int) -> str:
    if not game_ls:
        return '目前还没有开始任何游戏！'
    for index, game in enumerate(game_ls):
        game: Deck
        if deck_id == game.deck_id and game.player2 == player:
            game.get_one_card(2)
            player2_point = game.player2_point
            words = f"{game.player2_name}的牌为\n"
            for card in game.player2_cards:
                words += str(card)
            if player2_point > 21:
                words += f"\n牌点为{player2_point}\n爆牌！{game.player2_name}输了！\n"
                result = await count_score(game, 1)
                words += result
                del game_ls[index]
                return words
            elif player2_point == 21:
                words += f"\n牌点为{player2_point}\n"
                while game.player1_point < game.player2_point and game.player1_point <= 21:
                    game.get_one_card(1)
                words += f"对手的牌为"
                for card in game.player1_cards:
                    words += str(card)
                words += f"\n牌点为{game.player1_point}\n"
                if game.player1_point > 21:
                    result = await count_score(game, 2)
                else:

                    result = await count_score(game, 0)
                words += result
                del game_ls[index]
                return words
            else:
                words += f"\n牌点为{player2_point}"
                return words
        elif deck_id == game.deck_id and game.player2 != player:
            return '该游戏已开始！'
    return '未找到游戏！'


async def stop_card(deck_id: int, player: int) -> str:
    if not game_ls:
        return '目前还没有开始任何游戏！'
    for index, game in enumerate(game_ls):
        game: Deck
        if deck_id == game.deck_id and game.player2 == player:
            while game.player1_point < game.player2_point and game.player1_point <= 16:
                game.get_one_card(1)
            words = f"{game.player1_name}的牌为\n"
            for card in game.player1_cards:
                words += str(card)
            words += f"\n牌点为{game.player1_point}\n"
            if game.player1_point > 21:
                result = await count_score(game, 2)
            elif game.player1_point < game.player2_point:
                result = await count_score(game, 2)
            elif game.player1_point > game.player2_point:
                result = await count_score(game, 1)
            else:
                result = await count_score(game, 0)
            words += result
            del game_ls[index]
            return words
        elif deck_id == game.deck_id and game.player2 != player:
            return '该游戏已开始！'
    return '未找到游戏！'


async def count_score(game: Deck, player_win: int):
    player1_point = await BagUser.get_gold(game.player1, game.group)
    player2_point = await BagUser.get_gold(game.player2, game.group)
    if player_win == 1:
        winner_point = player1_point
        loser_point = player2_point
        winner = game.player1
        loser = game.player2
        winner_name = game.player1_name
        loser_name = game.player2_name
    elif player_win == 2:
        winner_point = player2_point
        loser_point = player1_point
        winner = game.player2
        loser = game.player1
        winner_name = game.player2_name
        loser_name = game.player1_name
    else:
        return "\n平局！"
    top_bonus = int(game.point * 0.1)
    winner_bonus = randint(0, top_bonus)
    loser_bonus = randint(-top_bonus, top_bonus)
    winner_dif_point = game.point + winner_bonus
    loser_dif_point = -game.point + loser_bonus

    winner_point += winner_dif_point
    loser_point += loser_dif_point
    await BagUser.spend_gold(loser, game.group, -loser_dif_point)
    await BagUser.add_gold(winner, game.group, winner_dif_point)

    words = f"{winner_name}获胜\n{winner_name}获得{game.point}金币！并且获得{winner_bonus}金币奖励\n" \
            f"{loser_name}失败"
    if loser_bonus > 0:
        words += f" 但获得{loser_bonus}金币"
    elif loser_bonus < 0:
        words += f" 并扣除{-loser_bonus}金币"
    return words


async def get_game_ls(group: int):
    s = ""
    for game in game_ls:
        if game.group == group:
            s += f"游戏id:{game.deck_id} 发起人:{game.player1_name} 游戏底分:{game.point}\n"
            if game.player2 is not None:
                s += f"{game.player2_name}正在游戏中\n"
            else:
                s += f"等待玩家二中\n"
    if not s:
        return "当前没有进行中的游戏！"
    return s[:-1]