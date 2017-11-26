import telebot
import logging
import const
import markups
import requests
import hashlib
from aiohttp import web
import ssl
import pymysql as sql
import datetime
from dateutil import parser
import time




WEBHOOK_HOST = '78.155.218.194'
WEBHOOK_PORT = 443  # 443, 80, 88 or 8443 (port need to be 'open')
WEBHOOK_LISTEN = '0.0.0.0'  # In some VPS you may need to put here the IP address

WEBHOOK_SSL_CERT = './webhook_cert.pem'
WEBHOOK_SSL_PRIV = './webhook_pkey.pem'

WEBHOOK_URL_BASE = "https://{}:{}".format(WEBHOOK_HOST, WEBHOOK_PORT)
WEBHOOK_URL_PATH = "/{}/".format(const.token)


logger = telebot.logger
telebot.logger.setLevel(logging.INFO)

loggerPy = logging.getLogger('bot.py')
loggerPy.setLevel(logging.DEBUG)
ch = logging.FileHandler('journal.log')
formatter = logging.Formatter('%(levelname)s : DATE ---> %(asctime)s - %(message)s')
ch.setFormatter(formatter)
loggerPy.addHandler(ch)

bot = telebot.TeleBot(const.token)

app = web.Application()



# Process webhook calls
async def handle(request):
    if request.match_info.get('token') == bot.token:
        request_body_dict = await request.json()
        update = telebot.types.Update.de_json(request_body_dict)
        bot.process_new_updates([update])
        return web.Response()
    else:
        return web.Response(status=403)

app.router.add_post('/{token}/', handle)


def connect():
    return sql.connect("localhost", "root", "churchbynewton", "TRADER", use_unicode=True, charset="utf8")

def daily_check():
    db = connect()
    cur = db.cursor()
    r = 'SELECT uid, end_date FROM payments'
    cur.execute(r)
    res = cur.fetchall()
    r = "SELECT state, days FROM demo WHERE id = 1"
    cur.execute(r)
    state, days_left = cur.fetchone()
    if state:
        if days_left == 0:
            r = "UPDATE demo SET state = 0 WHERE id = 1"
        else:
            r = "UPDATE demo SET days = days - 1 WHERE id = 1"
        cur.execute(r)
    today = str(datetime.datetime.now()).split(' ')[0]
    after_tomorrow = parser.parse(today) + datetime.timedelta(days=2)
    for user in res:
        if after_tomorrow == parser.parse(str(user[1])):
            text = 'У вас истекает подписка.'
            bot.send_message(user[0], text, reply_markup=markups.payBtnMarkup())
            time.sleep(0.1)
        if parser.parse(str(user[1])) <= parser.parse(today):
            text = 'Время действия вашей подписки окончено.'
            bot.send_message(user[0], text)
            r = 'DELETE FROM payments WHERE uid=%s'
            cur.execute(r, user[0])
            time.sleep(0.1)
    db.commit()
    db.close()


def addInvitation(user_id, invited_user_id):
    db = connect()
    cur = db.cursor()
    r = "SELECT * FROM INVITATIONS WHERE INVITED=%s"
    cur.execute(r, invited_user_id)
    if not cur.fetchone() and int(user_id) != int(invited_user_id):
        r = "INSERT INTO INVITATIONS (ID, INVITED) VALUES (%s, %s)"
        cur.execute(r, (user_id, invited_user_id))
        db.commit()
    db.close()


@bot.message_handler(commands=["start"])
def start(message):
    text = message.text.split(" ")
    if len(text) == 2:
        if text[1].isdigit():
            initial_id = text[1]
            addInvitation(initial_id, message.chat.id)
    db = connect()
    cur = db.cursor()
    r = 'SELECT * FROM users WHERE uid = %s'
    cur.execute(r, message.chat.id)
    if not cur.fetchone():
        r = "INSERT INTO users (uid, first_name, last_name, alias) VALUE (%s,%s,%s,%s)"
        cur.execute(r, (message.chat.id, message.from_user.first_name,
                        message.from_user.last_name, message.from_user.username))
        db.commit()
    bot.send_message(message.chat.id, const.startMsg % message.chat.id, reply_markup=markups.mainMenu(message.chat.id),
                     parse_mode="html")
    db.close()



def getUserBalance(uid):
    db = connect()
    cur = db.cursor()
    r = "SELECT balance FROM users WHERE uid = %s"
    cur.execute(r, uid)
    balance = cur.fetchone()
    db.close()
    return balance[0] / 100000000


def getIds():
    db = connect()
    cur = db.cursor()
    r = "SELECT uid FROM users"
    cur.execute(r)
    data = cur.fetchall()
    db.close()
    res = []
    for i in data:
        res.append(i[0])
    return res


def getPaidIds():
    db = connect()
    cur = db.cursor()
    r = "SELECT uid FROM payments"
    cur.execute(r)
    data = cur.fetchall()
    db.close()
    res = []
    for i in data:
        res.append(i[0])
    return res




@bot.message_handler(regexp="Админ-панель")
def admin(message):
    if message.chat.id == const.admin:
        bot.send_message(message.chat.id, "Админ-панель", reply_markup=markups.adminPanel())


@bot.callback_query_handler(func=lambda call: call.data == "admin")
def admin2(call):
    bot.edit_message_text("Админ-панель", call.message.chat.id, call.message.message_id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markups.adminPanel())


@bot.callback_query_handler(func=lambda call: call.data == "addVideo")
def addVideo(call):
    msg = bot.send_message(call.message.chat.id, "Введите ссылку на видео")
    bot.register_next_step_handler(msg, getVideo)


@bot.callback_query_handler(func=lambda call: call.data == "usersList")
def showUsers(call):
    const.listPointer = 0
    getUsers()
    bot.edit_message_text("Список пользователей", call.message.chat.id, call.message.message_id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markups.users())


@bot.callback_query_handler(func=lambda call: call.data == "nextList")
def listforward(call):
    const.listPointer += 1
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markups.users())


@bot.callback_query_handler(func=lambda call: call.data == "prevList")
def listback(call):
    const.listPointer -= 1
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markups.users())


def getUsers():
    db = connect()
    cur = db.cursor()
    r = "SELECT * FROM users"
    cur.execute(r)
    data = cur.fetchall()
    const.userList.clear()
    db.close()
    for user in data:
        const.userList.append(user[2] + " " + user[3] + '%' + str(user[0]))
    const.userList.sort()
    return const.userList


@bot.callback_query_handler(func=lambda call: call.data[0] == '<')
def detailedInfo(call):
    db = connect()
    cur = db.cursor()
    r = "SELECT * FROM payments WHERE uid = %s"
    cur.execute(r, call.data[1:])
    data = cur.fetchone()
    if data:
        text = "Куплена подписка до %s" % data[1]
    else:
        text = "У данного пользователя не куплена подписка"
    r = "SELECT INVITED FROM INVITATIONS WHERE ID = %s"
    cur.execute(r, call.data[1:])
    ids = cur.fetchall()
    if ids:
        text += "\nПригласил следующий список пользователей:\n"
        for user in ids:
            r = "SELECT first_name, last_name from users WHERE uid = %s"
            cur.execute(r, user)
            text += "<b>" + " ".join(cur.fetchone()) + "</b>\n"
    else:
        text += "\nЕще не пригласил ни одного пользователя"
    db.close()
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="html")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                  reply_markup=markups.showDetails(call.data[1:]))


@bot.callback_query_handler(func=lambda call: call.data == "changePrices")
def changePrices(call):
    bot.edit_message_text("Изменить цену на подписку", call.message.chat.id, call.message.message_id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                  reply_markup=markups.chooseMonth())


@bot.callback_query_handler(func=lambda call: call.data[0:2] == "$$")
def showInfo(call):
    text = "Текущая цена подписки: {price}\nВведите новую цену в биткойнах, цифры разделены точкой (0.15)"
    if call.data[2:] == "15":
        text = text.format(price=str(const.days15))
        msg = bot.send_message(call.message.chat.id, text)
        bot.register_next_step_handler(msg, change15)
    if call.data[2:] == "30":
        text = text.format(price=str(const.days30))
        msg = bot.send_message(call.message.chat.id, text)
        bot.register_next_step_handler(msg, change30)
    if call.data[2:] == "60":
        text = text.format(price=str(const.days60))
        msg = bot.send_message(call.message.chat.id, text)
        bot.register_next_step_handler(msg, change60)
    if call.data[2:] == "90":
        text = text.format(price=str(const.days90))
        msg = bot.send_message(call.message.chat.id, text)
        bot.register_next_step_handler(msg, change90)


def change15(message):
    try:
        const.days15 = float(message.text)
        bot.send_message(message.chat.id, "Цена изменена", reply_markup=markups.adminPanel())
    except:
        bot.send_message(message.chat.id, "Неправильный формат", reply_markup=markups.adminPanel())


def change30(message):
    try:
        const.days30 = float(message.text)
        bot.send_message(message.chat.id, "Цена изменена", reply_markup=markups.adminPanel())
    except:
        bot.send_message(message.chat.id, "Неправильный формат", reply_markup=markups.adminPanel())


def change60(message):
    try:
        const.days60 = float(message.text)
        bot.send_message(message.chat.id, "Цена изменена", reply_markup=markups.adminPanel())
    except:
        bot.send_message(message.chat.id, "Неправильный формат", reply_markup=markups.adminPanel())


def change90(message):
    try:
        const.days90 = float(message.text)
        bot.send_message(message.chat.id, "Цена изменена", reply_markup=markups.adminPanel())
    except:
        bot.send_message(message.chat.id, "Неправильный формат", reply_markup=markups.adminPanel())


@bot.callback_query_handler(func=lambda call: call.data[0:10] == "changeDate")
def changeDate(call):
    const.chosenUserId = call.data[10:]
    msg = bot.send_message(call.message.chat.id, "Введите дату формате 2017-03-23 <b>(гггг-мм-чч)</b>\n", parse_mode="html")
    bot.register_next_step_handler(msg, confirm_date)


def confirm_date(message):
    if len(message.text) == 10:
        date = message.text.replace(".", "-")
        db = connect()
        cur = db.cursor()
        r = "SELECT * FROM payments WHERE uid = %s"
        cur.execute(r, const.chosenUserId)
        if not cur.fetchone():
            r = "INSERT INTO payments (end_date, uid) VALUE (%s,%s)"
        else:
            r = "UPDATE payments SET end_date = %s WHERE uid = %s"
        cur.execute(r, (date, const.chosenUserId))
        db.commit()
        db.close()
        bot.send_message(message.chat.id, "Срок подписки изменен", reply_markup=markups.adminPanel())
    else:
        bot.send_message(message.chat.id, "Неправильный формат ввода", reply_markup=markups.adminPanel())


def getVideo(message):
    db = connect()
    cur = db.cursor()
    r = 'INSERT INTO VIDEO (link) VALUES (%s)'
    cur.execute(r, message.text)
    db.commit()
    db.close()
    bot.send_message(message.chat.id, "Видео успешно добавлено!")


@bot.callback_query_handler(func=lambda call: call.data == "demo on")
def turn_on_demo(call):
    db = connect()
    cur = db.cursor()
    r = "SELECT state from demo"
    cur.execute(r)
    state = int(cur.fetchone()[0])
    if state:
        bot.send_message(call.message.chat.id, "Демо режим уже включен", reply_markup=markups.adminPanel())
    else:
        msg = bot.send_message(call.message.chat.id, "Введите количество дней, на которое хотите включить")
        bot.register_next_step_handler(msg, handle_days)


@bot.callback_query_handler(func=lambda call: call.data == "demo off")
def turn_off(call):
    db = connect()
    cur = db.cursor()
    r = "SELECT state, days from demo"
    cur.execute(r)
    state, days = cur.fetchone()
    if state:
        bot.send_message(call.message.chat.id, "Демо режим будет работать для пользователей еще %s дней" % str(days), reply_markup=markups.adminPanel())
    else:
        bot.send_message(call.message.chat.id, "Демо режим выключен", reply_markup=markups.adminPanel())


def handle_days(message):
    try:
        days = int(message.text)
        db = connect()
        cur = db.cursor()
        r = "UPDATE demo SET state = 1"
        cur.execute(r)
        r = "UPDATE demo SET days = %s"
        cur.execute(r, days)
        r = "SELECT uid FROM users"
        cur.execute(r)
        ids = cur.fetchall()
        print(ids)
        today = str(datetime.datetime.now()).split(' ')[0]
        end_day = str(parser.parse(today) + datetime.timedelta(days=days)).split(' ')[0]
        print(end_day)
        for user in ids:
            r = "SELECT * FROM payments WHERE uid = (%s)"
            cur.execute(r, user)
            if cur.fetchone():
                continue
            else:
                request = "INSERT INTO payments (uid, end_date) VALUE (%s,%s)"
                cur.execute(request, (user, end_day))
            time.sleep(0.1)
        db.commit()
        db.close()
        bot.send_message(message.chat.id, "Демо режим включен для всех пользователей на %s дней" % message.text, reply_markup=markups.adminPanel())
    except:
        bot.send_message(message.chat.id, "Неправильный формат")


@bot.callback_query_handler(func=lambda call: call.data == "toAll")
def getText(call):
    msg = bot.send_message(call.message.chat.id, "Введите текст, который хотите отправить всем пользователям")
    bot.register_next_step_handler(msg, simpleDistribution)



def simpleDistribution(message):
    count = 0
    for user_id in getIds():
        if user_id == const.admin:
            continue
        if count == 20:
            time.sleep(1)
        bot.send_message(user_id, message.text)
        count += 1
    bot.send_message(message.chat.id, "Сообщение успешно отправлено всем пользователям!")


@bot.callback_query_handler(func=lambda call: call.data == "toPaid")
def getText1(call):
    msg = bot.send_message(call.message.chat.id, "Введите текст, который хотите отправить пользователям,"
                                                 " которые оплатили подписку")
    bot.register_next_step_handler(msg, simpleDistribution)


def paidDistribution(message):
    count = 0
    for user_id in getIds():
        if user_id == const.admin:
            continue
        if count == 20:
            time.sleep(1)
        bot.send_message(user_id, message.text)
        count += 1
    bot.send_message(message.chat.id, "Сообщение успешно отправлено всем пользователям!")


@bot.message_handler(regexp="Партнерская программа")
def materials(message):
    balance = "<b>Ваш баланс:</b> %s BTC\n" % getUserBalance(message.chat.id)
    text = "<b>Ваша реферальная ссылка:</b>\nhttps://t.me/arthur1bot?start=%s" % message.chat.id
    bot.send_message(message.chat.id, balance + text,  parse_mode="html", reply_markup=markups.withdrawBtn())


@bot.callback_query_handler(func=lambda call: call.data == "withdraw")
def withdraw(call):
    msg = bot.send_message(call.message.chat.id, "Введите сумму, которую хотите вывести")
    bot.register_next_step_handler(msg, checkSum)


def checkSum(message):
    try:
        value = float(message.text)
        if value <= getUserBalance(message.chat.id) and value > 0:
            const.values[message.chat.id] = value
            msg = bot.send_message(message.chat.id, "Введите адрес, на который будет произведена выплата")
            bot.register_next_step_handler(msg, sendRequest)
        else:
            bot.send_message(message.chat.id, "Недостаточно средств")
    except:
        bot.send_message(message.chat.id, "Неккоректная сумма")


def sendRequest(message):
    bot.send_message(const.admin, "Новая заявка на вывод %s BTC на адрес %s"
                     % (const.values.get(message.chat.id), message.text))
    bot.send_message(message.chat.id, "Ваша заявка отпралена!\nОжидайте подтверждения.")


@bot.message_handler(regexp="Маркетинг")
def marketing(message):
    bot.send_message(message.chat.id, const.marketingMsg, parse_mode="html")


@bot.message_handler(regexp="Начать работу")
def startWork(message):
    bot.send_message(message.chat.id, const.startWorkMsg % (const.days15, const.days90), reply_markup=markups.startWork())


@bot.message_handler(regexp="Посмотреть отзывы")
def showVideos(message):
    db = connect()
    cur = db.cursor()
    r = "SELECT link FROM VIDEO"
    cur.execute(r)
    data = cur.fetchall()
    for i in data:
        bot.send_message(message.chat.id, i[0])
        time.sleep(1)


@bot.callback_query_handler(func=lambda call: call.data == "conditions")
def showConditions(call):
    bot.send_message(call.message.chat.id, const.conditionsMsg)


@bot.callback_query_handler(func=lambda call: call.data == "news")
def channelLink(call):
    bot.send_message(call.message.chat.id, const.channelLink)


@bot.callback_query_handler(func=lambda call: call.data == "socialNetworks")
def showMedia(call):
    bot.edit_message_text("текст", call.message.chat.id, call.message.message_id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markups.socialNetworks())


@bot.callback_query_handler(func=lambda call: call.data == "profit")
def showProfit(call):
    bot.send_message(call.message.chat.id, const.profitMsg, reply_markup=markups.payBtnMarkup())


@bot.callback_query_handler(func=lambda call: call.data == "processPayment")
def chooseDuration(call):
    bot.send_message(call.message.chat.id, "Выберите подписку", reply_markup=markups.chooseDuration())


@bot.callback_query_handler(func=lambda call: call.data[:4] == "days")
def processPayment(call):
    days = call.data[4:]
    if days == "15":
        pay = const.days15
    elif days == "30":
        pay = const.days30
    elif days == "60":
        pay = const.days60
    else:
        pay = const.days90
    address = createBTCAddress()
    db = connect()
    cur = db.cursor()
    r = 'SELECT * FROM TEMP_DETAILS WHERE ID = %s'
    cur.execute(r, call.message.chat.id)
    if cur.fetchone():
        r = 'UPDATE TEMP_DETAILS SET BTC_ADDRESS = %s WHERE ID = %s'
        cur.execute(r, (address, call.message.chat.id))
    else:
        r = 'INSERT INTO TEMP_DETAILS (ID, BTC_ADDRESS) VALUES (%s, %s)'
        cur.execute(r, (call.message.chat.id, address))
    db.commit()
    db.close()
    bot.send_message(call.message.chat.id, const.paymentMsg.format(pay, address), parse_mode="html")


def createBTCAddress():
    sign = hashlib.md5("".join((const.wallet_id, const.walletApiKey)).encode()).hexdigest()
    data = {
        "wallet_id": const.wallet_id,
        "sign": sign,
        "action": "create_btc_address"
    }
    url = "https://wallet.free-kassa.ru/api_v1.php"
    response = requests.post(url, data).json()
    return response.get("data").get("address")



def send_payment_message(cid):
    pass


# if __name__ == '__main__':
#     with sqlite3.connect(const.dbName) as db:
#         cursor = db.cursor()
#         sql = '''CREATE TABLE IF NOT EXISTS payments (
#             id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
#             uid INTEGER NOT NULL,
#             end_date TEXT NOT NULL)'''
#         cursor.execute(sql)
#         db.commit()
#     bot.remove_webhook()
#     bot.polling()


def init_bot():

    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,
                    certificate=open(WEBHOOK_SSL_CERT, 'r'))

    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV)

    web.run_app(
        app,
        host=WEBHOOK_LISTEN,
        port=WEBHOOK_PORT,
        ssl_context=context,
    )


if __name__ == '__main__':
    init_bot()
