from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from dotenv import load_dotenv

import os

load_dotenv()


#print(api_key)


trading_client = TradingClient(
    api_key=os.getenv("APCA_API_KEY_ID"),
    secret_key=os.getenv("APCA_API_SECRET_KEY"),
    paper=True  )


account = trading_client.get_account()

if account.trading_blocked:
    print('blocked account')

print('${} is available as buying power.'.format(account.buying_power))


