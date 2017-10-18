import telebot
import logging
import const
import markups
import datetime
import parser
import time
import requests
import hashlib
from aiohttp import web
import ssl
import pymysql as sql



WEBHOOK_HOST = '85.143.175.233'
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

db = sql.connect("localhost", "root", "churchbynewton", "TRADER")


@bot.message_handler(commands=["start"])
def start(message):
    cur = db.cursor()
    r = 'SELECT * FROM users WHERE uid = %s'
    cur.execute(r, message.chat.id)
    if not cur.fetchone():
        r = "INSERT INTO users (uid) VALUE (%s)"
        cur.execute(r, message.chat.id)
        db.commit()
    bot.send_message(message.chat.id, const.startMsg, reply_markup=markups.mainMenu())


@bot.message_handler(regexp="Маркетинговые материалы")
def materials(message):
    bot.send_message(message.chat.id, "Выберите маркетинговый материал", reply_markup=markups.materials())


@bot.message_handler(regexp="Маркетинг")
def marketing(message):
    bot.send_message(message.chat.id, const.marketingMsg)


@bot.message_handler(regexp="Начать работу")
def startWork(message):
    bot.send_message(message.chat.id, const.startWorkMsg, reply_markup=markups.startWork())


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

#
# def daily_check():
#     with sqlite3.connect(const.dbName) as db:
#         cursor = db.cursor()
#         sql = 'SELECT uid, end_date FROM payments'
#         res = cursor.execute(sql).fetchall()
#         today = str(datetime.datetime.now()).split(' ')[0]
#         after_tomorrow = parser.parse(today) + datetime.timedelta(days=2)
#         print(after_tomorrow)
#         for user in res:
#             if after_tomorrow == parser.parse(str(user[1])):
#                 text = 'У вас истекает подписка.'
#                 bot.send_message(user[0], text)
#                 send_payment_message(user[0])
#                 time.sleep(0.1)
#             if parser.parse(str(user[1])) <= parser.parse(today):
#                 text = 'Время действия вашей подписки окончено.'
#                 bot.send_message(user[0], text)
#                 send_payment_message(user[0])
#                 # Delete user from DataBase
#                 sql = 'DELETE FROM payments WHERE uid=?'
#                 cursor.execute(sql, (user[0],))
#                 time.sleep(0.1)
#         db.commit()


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
