from gevent.monkey import patch_socket, patch_ssl; patch_socket(); patch_ssl()
from aiohttp import ClientSession
from datetime import datetime
from logging import getLogger, INFO, Formatter, FileHandler
from os import listdir
from os.path import isfile, join
from sys import stderr
from traceback import print_exc

from discord import ClientException
from discord.ext.commands import Bot, when_mentioned_or, Cog
from steam.enums import EResult
from steam.client import SteamClient
from steam import guard
from Login_details import preferences, sensitive_details


class AutoCord(Bot):
    def __init__(self):
        super().__init__(command_prefix=when_mentioned_or(preferences.command_prefix), case_insensitive=True,
                         description='Used to manage your tf2automatic bot and send all of Steam messages through Discord')

    @Cog.listener()
    async def on_connect(self):
        bot.dsdone = True

    async def setup(self, bot):
        bot.dsdone = False
        bot.log = getLogger()
        bot.log.setLevel(INFO)
        handler = FileHandler(filename='tf2autocord.log', encoding='utf-8', mode='w')
        handler.setFormatter(Formatter('%(asctime)s : %(levelname)s : %(name)s | %(message)s'))
        bot.log.addHandler(handler)

        bot.initial_extensions = [f[:-3] for f in listdir('Cogs') if isfile(join('Cogs', f))]
        print(f'Extensions to be loaded are {bot.initial_extensions}')
        bot.log.info(f'Extensions to be loaded are {bot.initial_extensions}')

        for extension in bot.initial_extensions:
            try:
                bot.load_extension(f'Cogs.{extension}')
            except (ClientException, ModuleNotFoundError):
                bot.log.error('Failed to load extension %s.', extension, file=stderr)
                print_exc()
        bot.log.info('Completed loading extensions')
        bot.session = ClientSession()

    def steam_start(self, bot):
        print('Steam is now logging on')
        bot.log.info('Steam is now logging on')
        bot.client = SteamClient()
        bot.client.set_credential_location('Login_details')  # where to store sentry files and other stuff  

        @bot.client.on('error')
        def handle_error(result):
            bot.log.error('Logon result: %s', repr(result))

        @bot.client.on('connected')
        def handle_connected():
            bot.log.info('Connected to: %s', bot.client.current_server_addr)

        @bot.client.on('reconnect')
        def handle_reconnect(delay):
            bot.log.info('Reconnect in %s...', delay)

        @bot.client.on('disconnected')
        def handle_disconnect():
            bot.log.warning('Disconnected.')

            if bot.client.relogin_available:
                bot.log.info('Reconnecting...')
                bot.client.reconnect(maxdelay=30)

        @bot.client.on('logged_on')
        def handle_after_logon():
            bot.s_bot = bot.client.get_user(bot.bot64id)
            bot.logged_on = True
            print(f'Logged on as: {bot.client.user.name}')
            bot.log.info('Logged on as: %s', bot.client.user.name)

        @bot.client.on('chat_message')
        def handle_message(user, message_text):
            if user.steam_id == bot.bot64id:
                if message_text.startswith('Message from'):
                    bot.usermessage = message_text
                elif bot.current_time.split()[1] == '23:59' and "You've made" in message_text:
                    bot.graphplots = message_text
                else:
                    bot.sbotresp = message_text

        if preferences.cli_login:
            bot.log.info('Using cli_login')
            result = bot.client.cli_login(username=sensitive_details.username, password=sensitive_details.password)
        else:
            bot.log.info('Using automatic')
            SA = guard.SteamAuthenticator(sensitive_details.secrets).get_code()
            result = bot.client.login(username=sensitive_details.username, password=sensitive_details.password, two_factor_code=SA)
        if result != EResult.OK:
            bot.log.fatal('Failed to login: %s', repr(result))
            bot.session.close()
            raise SystemExit
        while 1:
            try:
                bot.client.run_forever()
            except KeyboardInterrupt:
                bot.client.logout()
                print('Logging out')
                bot.log.info('Logging out')
                bot.session.close()
                raise SystemExit

    def run(self, bot):
        print('Discord is logging on')
        bot.loop.run_until_complete(bot.setup(bot))
        bot.log.info('Discord is logging on')
        bot.log.info('-' * 30)
        try:
            bot.loop.run_in_executor(None, self.steam_start, bot)
            bot.launch_time = datetime.utcnow()
            super().run(sensitive_details.token)
        except RuntimeError:
            bot.log.info('Logging out')
            bot.session.close()
            raise SystemExit


if __name__ == '__main__':
    bot = AutoCord()
    bot.run(bot)
