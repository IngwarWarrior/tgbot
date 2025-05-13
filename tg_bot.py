import csv
import logging
import random

from telegram import ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)


class Enemy:
    enemies = [[], [], [], [], []]

    def __init__(self, name, hp, av_dmg, lvl):
        self.name = name
        self.max_hp = hp
        self.av_dmg = av_dmg
        self.lvl = lvl


class Game:
    users = {}
    story = {}
    max_story = 5

    def __init__(self):
        pass

    def new_player(self, user, name):
        Game.users[user] = Player(user, name)
        Game.story[user] = [1, False]

    async def about(self, update, context):
        a = Game.users.get(update.effective_user)
        if a:
            await update.message.reply_text(
                f'''Привет, {a.name}! Твои характеристики:
Уровень: {a.lvl}
Опыт: {a.xp}/{a.max_xp} опыта от уровня {a.lvl + 1}
Здоровье: {a.hp}/{a.max_hp}
Урон: {a.dmg}
Деньги: {a.money} монет
Оружие: {a.equipment['wp']}
Броня: {a.equipment['ar']}
Первый навык: {a.skills[1]}
Второй навык: {a.skills[2]}
Увидимся!''')
        else:
            await update.message.reply_text('Ты ещё не начал игру!')


class Equipment:
    equipment = {}

    def __init__(self, dmg, df, reg, ev, eq_type, name, cost):
        self.ev = ev
        self.reg = reg
        self.df = df
        self.dmg = dmg
        self.eq_type = eq_type
        self.name = name
        self.cost = cost

    def __str__(self):
        ret = self.name + ' - ' + f'+{self.dmg} к урону, ' + f'+{self.df} к защите, ' + f'+{self.ev}% к шансу уклонения, ' + f'+{self.reg} к регенерации'
        return ret


class Skill:
    skills = {}

    def __init__(self, name, dmg, df, reg, ev, cd, cost):
        self.ev = ev
        self.reg = reg
        self.df = df
        self.dmg = dmg
        self.cd = cd
        self.name = name
        self.cost = cost

    def __str__(self):
        spr = int(2 <= self.cd <= 4) * 'хода' + int(self.cd >= 5) * 'ходов' + int(self.cd == 1) * 'ход'
        ret = self.name + ' - ' + f'+{self.dmg} к урону, ' * int(self.dmg != 0) + 'не наносит урон,' * int(
            self.dmg == 0) + f'+{self.df} к защите, ' + f'+{self.ev}% к шансу уклонения, ' + f'+{self.reg} к регенерации' + f'\nПерезарядка: {self.cd} {spr}'
        return ret


class Player:
    def __init__(self, user, name):
        self.user = user
        self.name = name
        self.money = 0
        self.hp = 100
        self.dmg = 10
        self.lvl = 1
        self.xp = 0
        self.max_xp = self.lvl * 10
        self.ser_lvl = 1
        self.ser_hp = 0
        self.max_hp = 100
        self.cds = [0, 0]
        self.equipment = {'wp': Equipment(0, 0, 0, 0, 'wp', 'Старый меч', 0),
                          'ar': Equipment(0, 0, 0, 0, 'ar', 'Старые доспехи', 0)}
        self.skills = {1: Skill.skills['Пропуск хода'],
                       2: Skill.skills['Пропуск хода']}
        self.last_markup = menu_markup


async def help_message(update, context):
    if not Game.users.get(update.effective_user, False):
        await update.message.reply_text('Сначала введите /start !')
    else:
        await context.bot.reply_text('''Этот бот - текстовая RPG игра.
Используйте доступные команды, чтоюы управлять персонажем.
Используйте /about чтобы увидеть характеристики своего персонажа.
Все доступные сейчас команды показаны вам.''',
                                     reply_markup=Game.users.get(update.effective_user).last_markup)


async def start_message(update, context):
    if not Game.users.get(update.effective_user, False):
        user = update.effective_user
        game.new_player(user, user.first_name + ' ' + user.last_name)
        await update.message.reply_html(
            rf'''Привет, {user.mention_html()}! Ты - великий воин, достигший небывалых высот и способный уничтожить любого врага одним ударом!
Но Боги этого мира решили, что с такой силой, ты должен быть таким же уязвимым, как и обычный человек.''')
        await update.message.reply_text(
            '''В сражениях ты играешься, но, получая урон, становишься всё серьёзнее. Однако, можно и просто стараться не попадать под удары''')
        await update.message.reply_text('''Напиши "Бой", чтобы найти приключений!''')
        await update.message.reply_text('''P.S. Если хочешь увидеть свои характеристики, напиши /about''',
                                        reply_markup=menu_markup)
    else:
        await update.message.reply_text('Вы уже начали игру!')


async def message(update, context):
    if not Game.users.get(update.effective_user, False):
        await update.message.reply_text('Сначала введите /start !')
    else:
        if update.message.text in available_messages:
            if update.message.text in ['Атаковать', 'Сбежать', 'Бой', 'Навык 1', 'Навык 2', 'Применить навык',
                                       'Отменить навык']:
                if update.message.text == 'Бой':
                    if context.user_data.get('shop', False) or context.user_data.get('skill_shop', False):
                        await update.message.reply_text('Цены может и высокие, но не настолько же!')
                    elif not context.user_data.get('is_started', False):
                        context.user_data['is_started'] = True
                        a = random.choice(Enemy.enemies[Game.users.get(update.effective_user).lvl // 5])
                        context.user_data['enemy'] = [a, a.max_hp]
                        await update.message.reply_text(f'''Тебе встретился {a.name}! Что ты будешь делать?
Здоровье врага: {context.user_data['enemy'][1]}/{context.user_data['enemy'][0].max_hp}''',
                                                        reply_markup=battle_markup)
                        Game.users.get(update.effective_user).last_markup = battle_markup
                    else:
                        await update.message.reply_text('Ты и так в бою!')
                elif context.user_data.get('is_started', False):
                    a = await battle(update, context)
                else:
                    await update.message.reply_text('Вы не в бою!')
            elif update.message.text == 'Сюжет':
                await story_start(update, context)
            elif update.message.text in ['Лавка', 'Покинуть лавку'] or (
                    update.message.text in ['1', '2', '3'] and context.user_data.get('shop')):
                await shop(update, context)
            elif update.message.text in ['Мудрец', 'Уйти'] or (
                    update.message.text in ['1', '2', '3', 'Заменить первый навык',
                                            'Заменить второй навык'] and context.user_data.get('skill_shop')):
                await skill_shop(update, context)
            else:
                await update.message.reply_text('Сейчас данная команда недоступна')
        else:
            await update.message.reply_text('Извините, я вас не понял')
    return 1


async def battle(update, context):
    if update.message.text == 'Сбежать':
        a = await run_away(update, context)
    else:
        did_attack = 1
        a = Game.users.get(update.effective_user, False)
        eq_buffs = [a.equipment['wp'].dmg + a.equipment['ar'].dmg, a.equipment['wp'].df + a.equipment['ar'].df,
                    a.equipment['wp'].ev + a.equipment['ar'].ev, a.equipment['wp'].reg + a.equipment['ar'].reg]
        if update.message.text == 'Атаковать':
            context.user_data['enemy'][1] -= int(
                (a.dmg + random.randint(-int((a.dmg + eq_buffs[0]) * 0.15), int((a.dmg + eq_buffs[0]) * 0.15))) * (
                        1.5 ** (a.ser_lvl - 1)))
        else:
            if 'Навык' in update.message.text:
                if a.cds[int(update.message.text[-1]) - 1] <= 0:
                    context.user_data['skill'] = int(update.message.text[-1])
                    await update.message.reply_text(
                        f'''Вы уверены, что хотите использовать навык?\n{a.skills[int(update.message.text[-1])]}''',
                        reply_markup=skill_markup)
                    Game.users.get(update.effective_user).last_markup = skill_markup
                else:
                    await update.message.reply_text(
                        f'''Навык перезаряжается! Ходов осталось: {a.cds[int(update.message.text[-1]) - 1]}''',
                        reply_markup=battle_markup)
                    Game.users.get(update.effective_user).last_markup = battle_markup
                did_attack = 0
            elif update.message.text == 'Применить навык':
                if context.user_data.get('skill'):
                    s = context.user_data.get('skill')
                    eq_buffs = [eq_buffs[0], eq_buffs[1] + a.skills[s].df, eq_buffs[2] + a.skills[s].ev,
                                eq_buffs[3] + a.skills[s].reg]
                    context.user_data['enemy'][1] -= (int(
                        (a.dmg + random.randint(-int((a.dmg + eq_buffs[0]) * 0.15),
                                                int((a.dmg + eq_buffs[0]) * 0.15))) * (
                                1.5 ** (a.ser_lvl - 1))) + a.skills[s].dmg) * int(a.skills[s].dmg != 0)
                    a.cds[s - 1] = a.skills[s].cd + 1
                    context.user_data['skill'] = 0
                else:
                    await update.message.reply_text('Какой навык?')
                    did_attack = 0
            else:
                context.user_data['skill'] = 0
                did_attack = 0
        if context.user_data['enemy'][1] > 0 and did_attack:
            a.cds = [a.cds[0] - 1, a.cds[1] - 1]
            a.hp = min(a.hp + eq_buffs[3], a.max_hp)
            if random.randint(1, 100) <= eq_buffs[2]:
                await update.message.reply_text(
                    f'''Здоровье врага: {context.user_data['enemy'][1]}/{context.user_data['enemy'][0].max_hp}\n
Он бьёт вас в ответ!\n
Вы уклонились!
Ваше здоровье: {a.hp}/{a.max_hp}''', reply_markup=battle_markup)
                Game.users.get(update.effective_user).last_markup = battle_markup
            else:
                damage = max(0, int((context.user_data['enemy'][0].av_dmg + random.randint(
                    -int(context.user_data['enemy'][0].max_hp * 0.05),
                    int(context.user_data['enemy'][0].max_hp * 0.05))) * (100 - eq_buffs[1]) / 100))
                a.hp -= damage
                a.ser_hp += damage
                if a.hp <= 0:
                    a.money = a.money // 2
                    a.hp = a.max_hp
                    context.user_data.clear()
                    await update.message.reply_text('''Кажется вы недооценили врага...\n
Вас сразили! Придется отлежаться и восстановиться.
Вы теряете половину накоплений''', reply_markup=menu_markup)
                    a.cds = [0, 0]
                    a.ser_lvl = 1
                    a.ser_hp = 0
                    a.last_markup = menu_markup
                else:
                    await update.message.reply_text(
                        f'''Здоровье врага: {context.user_data['enemy'][1]}/{context.user_data['enemy'][0].max_hp}\n
Он бьёт вас в ответ!\n
Ваше здоровье: {a.hp}/{a.max_hp}''', reply_markup=battle_markup)
                    if a.ser_hp >= 100:
                        a.ser_hp -= 100
                        a.ser_lvl += 1
                        await update.message.reply_text('''В таком бою шутить не стоит.
Вы стали серьёзнее!
Ваш урон увеличился в 1.5 раз!''')
                    Game.users.get(update.effective_user).last_markup = battle_markup
            return 1
        elif context.user_data['enemy'][1] <= 0:
            gm = random.randint(context.user_data['enemy'][0].lvl * 5,
                                (context.user_data['enemy'][0].lvl + 2) * 5)
            a.money += gm
            a.xp += random.randint((context.user_data['enemy'][0].lvl - 1) * 2,
                                   context.user_data['enemy'][0].lvl * 3) + random.randint(0, a.xp)
            a.hp = min(a.max_hp, a.hp + a.max_hp // 2)
            a.cds = [0, 0]
            a.ser_lvl = 1
            a.ser_hp = 0
            await update.message.reply_text(f'''Вы победили врага {context.user_data['enemy'][0].name}!\n
У вас {a.xp}/{a.max_xp} опыта от уровня {a.lvl + 1}
Вы получили {gm} монет
У вас {a.money} монет''', reply_markup=menu_markup)
            if context.user_data.get('story'):
                await story_end(update, context)
            Game.users.get(update.effective_user).last_markup = menu_markup
            context.user_data.clear()
            if a.xp >= a.max_xp:
                if a.lvl < 25:
                    a.lvl += 1
                    a.xp -= a.max_xp
                    a.max_xp = a.lvl * 10
                    a.max_hp = (5 + a.lvl // 5) * 20
                    a.hp = a.max_hp
                    a.dmg += 2
                    await update.message.reply_text(f'''Поздравляем! Вы достигли уровня {a.lvl}!
Урон: {a.dmg - 2} -> {a.dmg}
{a.xp}/{a.max_xp} опыта от уровня {a.lvl + 1}''')
                else:
                    await update.message.reply_text('У вас максимальный уровень!')


async def story_start(update, context):
    if context.user_data:
        await update.message.reply_text('Сейчас вы не можете начать сюжетное сражение')
    else:
        if Game.story[update.effective_user][0] > Game.max_story:
            await update.message.reply_text('Вы прошли сюжет! Спасибо за игру!')
        else:
            f = open(f'{Game.story[update.effective_user][0]}.txt', mode='r', encoding='utf8')
            txt = f.readlines()
            start_text = []
            for i in range(len(txt)):
                if txt[i][:5] != 'stats':
                    start_text.append(txt[i][:-1])
                else:
                    break
            en_inf = txt[i][7:].split(';')
            enemy = Enemy(en_inf[0], int(en_inf[1]), int(en_inf[2]), 1)
            if not Game.story[update.effective_user][1]:
                context.user_data['story'] = True
                Game.story[update.effective_user][1] = True
                for i in start_text:
                    await update.message.reply_text(i)
            context.user_data['enemy'] = [enemy, enemy.max_hp]

            f.close()
            await update.message.reply_text(f'''Тебе встретился {enemy.name}! Что ты будешь делать?
Здоровье врага: {context.user_data['enemy'][1]}/{context.user_data['enemy'][0].max_hp}''', reply_markup=battle_markup)
            Game.users.get(update.effective_user).last_markup = battle_markup
            context.user_data['is_started'] = True
            await battle(update, context)


async def story_end(update, context):
    f = open(f'{Game.story[update.effective_user][0]}.txt', mode='r', encoding='utf8')
    txt = f.readlines()
    for i in range(len(txt)):
        if txt[i][:5] == 'stats':
            break
    end_text = []
    for j in range(i + 1, len(txt)):
        end_text.append(txt[j][:-1])
    for i in end_text:
        await update.message.reply_text(i)
    f.close()
    Game.story[update.effective_user] = [Game.story[update.effective_user][0] + 1, False]


async def shop(update, context):
    if context.user_data.get('shop', False):
        if update.message.text == 'Лавка':
            await update.message.reply_text('Вы и так здесь!')
        else:
            if update.message.text in ['1', '2', '3']:
                a = Game.users.get(update.effective_user)
                chosen = context.user_data['shop'][int(update.message.text) - 1]
                if not chosen[1]:
                    if a.money < chosen[0].cost:
                        await update.message.reply_text('Не хватает монет!', reply_markup=shop_markup)
                        Game.users.get(update.effective_user).last_markup = shop_markup
                    else:
                        a.equipment[chosen[0].eq_type] = chosen[0]
                        a.money -= chosen[0].cost
                        await update.message.reply_text(f'''Вы купили {chosen[0].name} за {chosen[0].cost} монет
У вас осталось {a.money} монет''', reply_markup=shop_markup)
                        Game.users.get(update.effective_user).last_markup = shop_markup
                else:
                    await update.message.reply_text('Уже куплено', reply_markup=shop_markup)
                    Game.users.get(update.effective_user).last_markup = shop_markup
            else:
                await update.message.reply_text('Вы вышли из лавки', reply_markup=menu_markup)
                Game.users.get(update.effective_user).last_markup = shop_markup
                context.user_data.clear()
    else:
        if context.user_data.get('is_started', False):
            await update.message.reply_text('Вряд ли соперник тебе что-то продаст...')
            return
        elif context.user_data:
            await update.message.reply_text('Сейчас вы не можете воспользоваться Лавкой.')
            return
        a = Game.users.get(update.effective_user)
        goods = random.choices(list(Equipment.equipment.keys()), k=3)
        context.user_data['shop'] = [[Equipment.equipment[goods[0]], False],
                                     [Equipment.equipment[goods[1]], False],
                                     [Equipment.equipment[goods[2]], False]]
        await update.message.reply_text(f'''Сегодня в лавке есть следующие товары:
1: {context.user_data['shop'][0][0]} - {context.user_data['shop'][0][0].cost} монет\n
2: {context.user_data['shop'][1][0]} - {context.user_data['shop'][1][0].cost} монет\n
3: {context.user_data['shop'][2][0]} - {context.user_data['shop'][2][0].cost} монет\n
Ваши накопления: {a.money}\n
Внимание! При покупке нового снаряжения вы теряете старое! Предыдущее снаряжение придется снова покупать''',
                                        reply_markup=shop_markup)
        Game.users.get(update.effective_user).last_markup = shop_markup


async def skill_shop(update, context):
    if context.user_data.get('skill_shop', False):
        if update.message.text == 'Мудрец':
            await update.message.reply_text('Вы и так здесь!')
        else:
            if update.message.text in ['1', '2', '3']:
                a = Game.users.get(update.effective_user)
                chosen = context.user_data['skill_shop'][0][int(update.message.text) - 1]
                if a.money < chosen[0].cost:
                    await update.message.reply_text('Не хватает монет!', reply_markup=skill_shop_markup)
                    Game.users.get(update.effective_user).last_markup = skill_shop_markup
                elif not chosen[1]:
                    a.skills[context.user_data['skill_shop'][1]] = chosen[0]
                    a.money -= chosen[0].cost
                    context.user_data['skill_shop'][0][int(update.message.text) - 1][1] = True
                    await update.message.reply_text(f'''Вы купили {chosen[0].name} за {chosen[0].cost} монет
    У вас осталось {a.money} монет''', reply_markup=skill_shop_markup)
                    Game.users.get(update.effective_user).last_markup = skill_shop_markup
                else:
                    await update.message.reply_text('Уже куплено', reply_markup=skill_shop_markup)
                    Game.users.get(update.effective_user).last_markup = skill_shop_markup
            elif update.message.text in ['Заменить первый навык', 'Заменить второй навык']:
                bbb = 1 + int('второй' in update.message.text)
                context.user_data['skill_shop'][1] = bbb
                await update.message.reply_text(
                    f'''Следующий навык заменит навык в{'о' * int(update.message.text[9] == 'в')} {update.message.text[9:13]}ой ячейке!''',
                    reply_markup=skill_shop_markup)
                Game.users.get(update.effective_user).last_markup = skill_shop_markup
            else:
                await update.message.reply_text('Вы покинули Мудреца', reply_markup=menu_markup)
                Game.users.get(update.effective_user).last_markup = skill_shop_markup
                context.user_data.clear()
    else:
        if context.user_data.get('is_started', False):
            await update.message.reply_text('Вряд ли ваш соперник поделится навыками...')
            return
        elif context.user_data:
            await update.message.reply_text('Сейчас вы не можете воспользоваться услугами Мудреца.')
            return
        a = Game.users.get(update.effective_user)
        goods = random.choices(list(Skill.skills.keys()), k=3)
        context.user_data['skill_shop'] = [[[Skill.skills[goods[0]], False],
                                            [Skill.skills[goods[1]], False],
                                            [Skill.skills[goods[2]], False]], 1]
        bbb = 'первой' * int(context.user_data['skill_shop'][1] == 1) + 'второй' * int(
            context.user_data['skill_shop'][1] == 2)
        await update.message.reply_text(f'''Мудрец готов обучить вас следующим навыкам:
    1: {context.user_data['skill_shop'][0][0][0]} - {context.user_data['skill_shop'][0][0][0].cost} монет\n
    2: {context.user_data['skill_shop'][0][1][0]} - {context.user_data['skill_shop'][0][1][0].cost} монет\n
    3: {context.user_data['skill_shop'][0][2][0]} - {context.user_data['skill_shop'][0][2][0].cost} монет\n
    Ваши накопления: {a.money}\n
    Следующий навык заменит навык в {bbb} ячейке!\n
    Внимание! При покупке новых навыков вы теряете старые! Предыдущие навыки придется снова покупать''',
                                        reply_markup=skill_shop_markup)
        Game.users.get(update.effective_user).last_markup = skill_shop_markup


async def run_away(update, context):
    await update.message.reply_text(f'''Вы сбежали!''', reply_markup=menu_markup)
    Game.users.get(update.effective_user).last_markup = menu_markup
    Game.users.get(update.effective_user).cds = [0, 0]
    Game.users.get(update.effective_user).ser_lvl = 1
    Game.users.get(update.effective_user).ser_hp = 0
    Game.users.get(update.effective_user).hp = min(int(Game.users.get(update.effective_user).hp * 1.25), Game.users.get(update.effective_user).max_hp)
    context.user_data.clear()
    return 1


def main():
    application = Application.builder().token('7603762601:AAGvWYbHaQWPUbNQzqoEctLTyt1Fre-UYGY').build()
    application.add_handler(CommandHandler('start', start_message))
    application.add_handler(CommandHandler('help', help_message))
    application.add_handler(CommandHandler('about', game.about))
    application.add_handler(
        ConversationHandler(entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, message)],
                            states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, message)]},
                            fallbacks=[CommandHandler('stop', run_away)]))
    application.run_polling()


if __name__ == '__main__':
    with open('enemies.csv', mode='r', encoding="utf8") as f:
        reader = csv.DictReader(f, delimiter=',')
        for i in reader:
            Enemy.enemies[int(i['lvl']) - 1].append(Enemy(i['name'], int(i['hp']), int(i['av_dmg']), int(i['lvl'])))
    with open('equipment.csv', mode='r', encoding="utf8") as f:
        reader = csv.DictReader(f, delimiter=',')
        for i in reader:
            Equipment.equipment[i['name']] = Equipment(int(i['dmg']), int(i['df']), int(i['reg']), int(i['ev']),
                                                       i['eq_type'], i['name'], int(i['cost']))
    with open('skills.csv', mode='r', encoding='utf8') as f:
        reader = csv.DictReader(f, delimiter=',')
        for i in reader:
            Skill.skills[i['name']] = Skill(i['name'], int(i['dmg']), int(i['df']), int(i['reg']), int(i['ev']),
                                            int(i['cd']), int(i['cost']))
    game = Game()
    available_messages = ['Атаковать', 'Сбежать', 'Бой', 'Лавка', '1', '2', '3', 'Покинуть лавку', 'Навык 1', 'Навык 2',
                          'Применить навык', 'Отменить навык', 'Мудрец', 'Уйти', 'Заменить первый навык',
                          'Заменить второй навык', 'Сюжет']
    battle_markup = ReplyKeyboardMarkup([['Атаковать'], ['Навык 1', 'Навык 2'], ['Сбежать']], one_time_keyboard=True)
    skill_markup = ReplyKeyboardMarkup([['Применить навык'], ['Отменить навык']], one_time_keyboard=True)
    menu_markup = ReplyKeyboardMarkup([['Бой'], ['Лавка'], ['Мудрец'], ['Сюжет']], one_time_keyboard=True)
    shop_markup = ReplyKeyboardMarkup([['1', '2', '3'], ['Покинуть лавку']], one_time_keyboard=True)
    skill_shop_markup = ReplyKeyboardMarkup([['1', '2', '3'], ['Заменить первый навык'], ['Заменить второй навык'],
                                             ['Уйти']], one_time_keyboard=True)
    main()
