import json
from json import JSONDecodeError
from time import sleep
import datetime
import asyncio
import aiohttp
import aiogram
from botconfig import BotConf

CURRENCIES = {'RUB': 'руб.',
              'USD': 'долл.',
              'EUR': 'евро'}

ADMIN_USER_ID = BotConf.ADMIN_USER_ID
# CHANGE! telegram channel username "@dfasfdfadfafa343", or chat ID, or user id
BOT_ID = BotConf.BOT_ID
# CHANGE! from bot father, BOT_ID = 23123123123131231323
TOKEN = BotConf.TOKEN
# CHANGE! from bot father, format '12312423:Sdarf2r3resdf-Sdr3rsfsff'
SERVER_URL = BotConf.SERVER_URL
# we took this blank page, you should also specify it in here https://www.donationalerts.com/application/clients
CLIENT_ID = BotConf.CLIENT_ID
# CHANGE!  you can get it in the DonationAlerts application
CLIENT_SECRET = BotConf.CLIENT_SECRET
# CHANGE!   you can get it in the DonationAlerts application
OAUTH_URL = BotConf.OAUTH_URL
OAUTH_TOKEN_URL = BotConf.OAUTH_TOKEN_URL
config = {}

# You also need a looooooooooong access token "code". You will be asked for it.
# Go to OAUTH_URL and you will be redirected to https://api.vk.com/blank.html?code= where Code is .....html?code=

async def load_config():
    global config
    try:
        with open('config.json', 'r') as config_file:
            config = json.loads(config_file.read())
    except (FileNotFoundError, JSONDecodeError):
        return


async def remove_config():
    global config
    config = {}
    with open('config.json', 'w') as f:
        f.write('')


async def save_config():
    global config
    try:
        with open('config.json', 'w') as f:
            f.write(json.dumps(config))
    except Exception as e:
        print(str(e))


async def refresh_token(session):
    global config

    params = {
        'grant_type': 'refresh_token',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': config['refresh_token'],
        'redirect_uri': f'{SERVER_URL}',
        'scope': 'oauth-donation-index'
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    async with session.post(OAUTH_TOKEN_URL, data=params, headers=headers) as resp:
        conf = await resp.json()
        if 'error' in conf:
            print(conf)
            await remove_config()
            exit(1)
        config = conf
    await save_config()


async def request_api(session, method, *args):
    timestamp = datetime.datetime.now().timestamp()
    if timestamp >= int(config['expires_in']):
        await refresh_token(session)

    headers = {
        'Authorization': f'Bearer {config["access_token"]}'
    }
    async with session.get(f'https://www.donationalerts.com/api/v1/{method}', params=args, headers=headers) as resp:
        e = await resp.json()
        return e
    # response = requests.get(f'https://www.donationalerts.com/api/v1/{method}', params=args, headers=headers)
    # return response.json()


async def update_donate_id(did):
    with open('.last_donate', 'w') as file:
        file.write(str(did))


async def showDonate(session, bot):
    global _last_donate_id
    donations = (await request_api(session, 'alerts/donations'))['data']
    new_last_id = _last_donate_id
    ignore_id = False
    for donate in donations:
        if ignore_id or donate['id'] > _last_donate_id:
            try:
                donation = await bot.send_message(ADMIN_USER_ID, f"{donate['username']} задонатил {str(donate['amount'])} {CURRENCIES[donate['currency']]} со словами: \"{donate['message']}\"")
                _last_donate_id = donate['id']
                sleep(1)
            except Exception as e:
                print(e)
    await update_donate_id(_last_donate_id)


async def create_a_token(code, session):
    data = {"grant_type":"authorization_code", "client_id":CLIENT_ID, "client_secret":CLIENT_SECRET,
            "redirect_uri":SERVER_URL, "code":code}
    async with session.post("https://www.donationalerts.com/oauth/token", data=data) as resp:
        out = await resp.json()
        if 'error' in out:
            print(out)
            exit(1)
        global config
        config = out


async def main():
    global loop
    bot = aiogram.Bot(TOKEN, loop)
    await load_config()
    if 'access_token' not in config:
        print("Go to ", OAUTH_URL)
        code = input("Code: ")
        async with aiohttp.ClientSession() as session:
            await create_a_token(code, session)
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                await showDonate(session, bot)
            sleep(30)
            print('Pending...')
        except Exception as e:
            print(e.__class__.__name__, str(e))
            if 'connect' in e.lower():
                await asyncio.sleep(60)
            else:
                loop.stop()
                break


try:
    with open('.last_donate', 'r') as file:
        _last_donate_id = int(file.read())
except (FileNotFoundError, IOError, ValueError):
    exit(1)

loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
