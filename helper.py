from bot import daily_check
import datetime
import time




while True:
    clock = str(datetime.datetime.now()).split(' ')[1][:5]
    #if clock == '00:00':
    daily_check()
    print("chaecked")
    break
    time.sleep(60)