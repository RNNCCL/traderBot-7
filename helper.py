from bot import daily_check
import datetime
import time


def init_interval():

    while True:
        clock = str(datetime.datetime.now()).split(' ')[1][:5]
        #if clock == '00:00':
        daily_check()
        time.sleep(60)