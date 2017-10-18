import telebot
import const

def mainMenu():
    markup = telebot.types.ReplyKeyboardMarkup(True, False)
    markup.row("Маркетинг", "🚀 Маркетинговые материалы")
    markup.row("Посмотреть отзывы", "Начать работу")
    return markup


def materials():
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton(text="Баннер 120х200", callback_data="banner120*200")
    btn2 = telebot.types.InlineKeyboardButton(text="Баннер 240х400", callback_data="banner240*400")
    btn3 = telebot.types.InlineKeyboardButton(text="Баннер 468х60", callback_data="banner468*60")
    btn4 = telebot.types.InlineKeyboardButton(text="Баннер 728х90", callback_data="banner728*90")
    btn5 = telebot.types.InlineKeyboardButton(text="Логотип", callback_data="logo")
    btn6 = telebot.types.InlineKeyboardButton(text="Презентация", callback_data="presentation")
    markup.row(btn1, btn2)
    markup.row(btn3, btn4)
    markup.row(btn5, btn6)
    return markup


def startWork():
    markup = telebot.types.InlineKeyboardMarkup()
    profit = telebot.types.InlineKeyboardButton(text="Что я получу за %s BTC?" % const.days15, callback_data="profit")
    payBtn = telebot.types.InlineKeyboardButton(text="Приступить к оплате", callback_data="processPayment")
    conditions = telebot.types.InlineKeyboardButton(text="Условия", callback_data="conditions")
    news = telebot.types.InlineKeyboardButton(text="Новости", url="google.com")
    socialNetworksBtn = telebot.types.InlineKeyboardButton(text="Социальные сети", callback_data="socialNetworks")
    markup.add(payBtn)
    markup.add(profit)
    markup.row(news, socialNetworksBtn)
    markup.add(conditions)
    return markup


def payBtnMarkup():
    markup = telebot.types.InlineKeyboardMarkup()
    payBtn = telebot.types.InlineKeyboardButton(text="Оплатить", callback_data="processPayment")
    markup.add(payBtn)
    return markup


def socialNetworks():
    markup = telebot.types.InlineKeyboardMarkup()
    net1 = telebot.types.InlineKeyboardButton(text="Соц сеть 1", url="google.com")
    net2 = telebot.types.InlineKeyboardButton(text="Соц сеть 2", url="google.com")
    markup.add(net1)
    markup.add(net2)
    return markup


def packets():
    markup = telebot.types.InlineKeyboardMarkup()
    investor = telebot.types.InlineKeyboardButton(text="Investor pack - %s BTC/месяц" % const.investorPrice,
                                                  callback_data="packinvestor")
    trader = telebot.types.InlineKeyboardButton(text="Trader pack - %s BTC/месяц" % const.traderPrice,
                                                callback_data="packtrader")
    full = telebot.types.InlineKeyboardButton(text="Full pack - %s BTC/месяц" % const.fullPrice,
                                              callback_data="packfull")
    markup.add(investor)
    markup.add(trader)
    markup.add(full)
    return markup


def chooseDuration():
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton(text="15 дней — %s btc" % const.days15, callback_data="days15")
    btn2 = telebot.types.InlineKeyboardButton(text="30 дней — %s btc" % const.days30, callback_data="days30")
    btn3 = telebot.types.InlineKeyboardButton(text="60 дней — %s btc" % const.days60, callback_data="days60")
    btn4 = telebot.types.InlineKeyboardButton(text="90 дней — %s btc" % const.days90, callback_data="days90")
    markup.add(btn1)
    markup.add(btn2)
    markup.add(btn3)
    markup.add(btn4)
    return markup

