import discord
from discord.ext import commands, tasks

import asyncio
import steam
import psutil
import json
import matplotlib.pyplot as plt
import os

from platform import python_version
from datetime import datetime
from aiohttp import ClientSession

from .loader import LoaderCog


class DiscordCog(commands.Cog, name='Discord'):
    """Commands that are mostly help commands but more useful"""

    def __init__(self, bot):
        self.bot = bot
        self.profitgraphing.start()
        self.acceptedfiles = ['history', 'history.json', 'inventory', 'inventory.json', 'schema', 'schema.json',
                              'listings', 'listings.json']

    @tasks.loop(seconds=10)
    async def profitgraphing(self):
        """A task that at 23:59 will get your profit
        It will convert all your values to keys"""
        self.bot.currenttime = str(datetime.now().strftime("%H:%M"))
        if self.bot.currenttime == '23:59':
            date = datetime.today().strftime("%d-%m-%Y")
            self.bot.client.get_user(self.bot.bot64id).send_message(f'{self.bot.command_prefix}profit')
            await asyncio.sleep(2)
            async with ClientSession() as session:
                async with session.get('https://api.prices.tf/items/5021;6?src=bptf') as response:
                    response = await response.json()
                    keyValue = response["sell"]["metal"]

            log = self.bot.graphplots
            log = log.replace("You've made ", '')
            if 'all' in log:
                log = log.replace(' if all items were sold).', '')
            else:
                log = log[:-1]

            todprofit = log.split(' today')
            fixedtodprofit = int(todprofit[0][:-4])
            totprofit = str(todprofit[1]).replace(']', '').replace('[', '')

            if '(' in log:  # checks your total profit and if you have total profit
                totprofit = totprofit[2:-5].split(' in total')
            else:
                totprofit = totprofit[2:].split(' in total')

            if 'key' in fixedtodprofit:  # converts 1st value to keys
                fixedtodprofit = fixedtodprofit.split(' ')
                if '-' in fixedtodprofit[0]:
                    minus = '-'
                else:
                    minus = ''
                fixedtodprofit = round(float(fixedtodprofit[0]) + float(minus + fixedtodprofit[2]) / keyValue, 2)

            if 'key' in totprofit[0] or 'keys' in totprofit[0]:  # converting 2nd
                fixedtotprofit = totprofit[0].split(', ')
                if 'keys' in fixedtotprofit[0]:
                    fixedtotprofit[0] = fixedtotprofit[0][:-5]
                elif 'key' in fixedtotprofit[0]:
                    fixedtotprofit[0] = fixedtotprofit[0][:-3]
                fixedtotprofit[1] = fixedtotprofit[1][:-4]

                fixedtotprofit = round(float(fixedtotprofit[0]) + float(fixedtotprofit[1]) / keyValue, 2)

            if 'more' in str(log):  # checks if you have predicted profit
                predprofit = str(totprofit[1]).replace(' (', '').replace('[', '').replace(']', '').replace("'",
                                                                                                           '')
                fixedpredprofit = predprofit.split(', ')
                if 'keys' in fixedpredprofit[0]:
                    fixedpredprofit[0] = fixedpredprofit[0][:-5]
                elif 'key' in fixedpredprofit[0]:
                    fixedpredprofit[0] = fixedpredprofit[0][:-3]
                fixedpredprofit[1] = fixedpredprofit[1][:-4]

                fixedpredprofit = round(float(fixedpredprofit[0]) + float(fixedpredprofit[1]) / keyValue, 2)
                graphdata = [fixedtodprofit, fixedtotprofit, fixedpredprofit, self.bot.trades]
            else:
                graphdata = [fixedtodprofit, fixedtotprofit, self.bot.trades]

            tempprofit = {date: graphdata}

            with open('profit_graphing.json') as f:
                data = json.load(f)
                data.update(tempprofit)
            with open('profit_graphing.json', 'w') as f:
                json.dump(data, f, indent=4)

    @commands.command()
    @commands.is_owner()
    async def last(self, ctx, days: int = 7):
        """Used to get the last x days profit

        :days <7>
        eg. `!last 7` (days has to be an integer)"""
        data = json.load(open('Login details/profit_graphing.json', 'r'))
        if days > len(data):
            await ctx.send('You can\'t request that man days as there haven\'t been enough days plotted to do that.\n'
                           f'Maximum requestable days is {len(data)}')
        else:
            embed = discord.Embed(title=' ', color=self.bot.color)
            embed.set_author(name=f'Last {days} days profit')
            for key, value in reversed(list(data.items())):
                try:
                    embed.add_field(name=f'{key}:', value=f'Days profit **{value[0]}** keys. Total profit **{value[1]}'
                                                          f'** keys. Predicted profit **{value[2]}** keys. '
                                                          f'Total trades **{value[3]}**',
                                    inline=False)
                except:
                    pass
            await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def graph(self, ctx):
        """Used to generate a graph of all of your profit whilst using the bot"""
        data = json.load(open('Login details/profit_graphing.json', 'r'))
        date_values = []
        for key in data.keys():
            date_values.append(key)

        # List to hold y values.
        tod_values = []
        for value in data.values():
            tod_values.append(float(value[0]))
        tot_values = []
        for value in data.values():
            tot_values.append(float(value[1]))
        pred_values = []
        for value in data.values():
            try:
                pred_values.append(float(value[2]))
            except IndexError:
                pred_values.append(0)

        # Plot the number in the list and set the line thickness.
        plt.setp(plt.plot(date_values, tod_values, linewidth=3), color='blue')
        plt.setp(plt.plot(date_values, tot_values, linewidth=3), color='orange')
        plt.setp(plt.plot(date_values, pred_values, linewidth=3), color='green')

        plt.title(f"A graph to show your bot\'s over the last {len(data)} days", fontsize=16)
        plt.xlabel("Date", fontsize=10)
        plt.ylabel("Keys", fontsize=10)
        plt.tick_params(axis='both', labelsize=9)
        plt.gca().legend(('Days profit', 'Total profit', 'Predicted profit'))

        location = os.getcwd() + '\\Login details\\graph.png'
        plt.savefig(location)
        file = discord.File(location, filename='graph.png')
        await ctx.send(content='Here is your graph:', file=file)
        await asyncio.sleep(10)
        os.remove(location)

    @commands.command()
    @commands.is_owner()
    async def acknowledged(self, ctx):
        """Used to acknowledge a user message

        This is so user messages don't get lost in the channel history"""
        self.bot.usermessage = 0
        await ctx.send('Acknowledged the user\'s message')

    @commands.command()
    @commands.is_owner()
    async def togpremium(self, ctx):
        """Used to remind yourself when your bp.tf premium will run out"""
        if self.bot.togglepremium == 0:
            self.bot.togglepremium = 1
            await ctx.send(
                'Premium Alerts now toggled on (this will send you a message when 1 months and 29 days have gone past)')
        elif self.bot.togglepremium == 1:
            self.bot.togglepremium = 0
            await ctx.send('Premium Alerts now toggled off')

        while self.bot.togglepremium == 1:
            await asyncio.sleep(4654687)  # 2 months in seconds - 1 day = 4654687 seconds
            await ctx.send('You may wish to renew your premium subscription')

    @commands.command(aliases=['warm-my-insides'])
    @commands.is_owner()
    async def donate(self, ctx):
        """Used to feel warm and fuzzy on the inside"""
        embed = discord.Embed(title=' ', color=0x2e3bad)
        embed.set_thumbnail(
            url='https://cdn.discordapp.com/avatars/340869611903909888/6acc10b4cba4f29d3c54e38d412964cb.png?size=1024')
        embed.add_field(name='Want to donate?',
                        value='[Trade link](https://steamcommunity.com/tradeoffer/new/?partner=287788226&token=NBewyDB2)')
        embed.set_footer(text='Thank you for any donations')
        await ctx.send(embed=embed)

    @commands.command(aliases=['gimme'])
    @commands.is_owner()
    async def get(self, ctx, *, file=None):
        """Used to get files from your temp folder

        :file [required]
        eg. `!get history` (if you don't type anything you can see the files you can request)"""
        if file is None:
            await ctx.send(f'You can request these `{self.acceptedfiles}`')
        file = file.lower()
        if file in self.acceptedfiles:
            file = f'/{file}'
            if '.json' in file:
                filename = file
                file = f'{self.bot.templocation}{file}'
            elif '.json' not in file:
                filename = f'{file}.json'
                file = f'{self.bot.templocation}{file}.json'
            file = discord.File(file, filename=filename)
            await ctx.send('Here you go, don\'t do anything naughty with it.', file=file)
        else:
            await ctx.send('I\'m sorry you can request that file')

    @commands.command(aliases=['about', 'stats', 'status'])
    async def info(self, ctx):
        """Get some interesting info about the bot"""
        rawram = psutil.virtual_memory()
        os.system(f'cd {os.getcwd()}')
        updateable = os.popen('git checkout').read()
        if 'Your branch is up to date with' in updateable:
            emoji = '<:tick:626829044134182923>'
        else:
            emoji = '<:goodcross:626829085682827266>'
        embed = discord.Embed(title="**tf2-autocord:** Developer - Gobot1234", colour=self.bot.color)
        embed.set_thumbnail(url=ctx.bot.user.avatar_url)
        embed.add_field(name="Commands loaded & Cogs loaded",
                        value=f'`{(len([x.name for x in self.bot.commands]))}` commands loaded, `{len([x for x in self.bot.cogs])}` cogs loaded :gear:',
                        inline=True)
        embed.add_field(name="<:compram:622622385182474254> RAM Usage",
                        value=f'`{round(rawram[3] / 1024 ** 2)}` MB used / `{round(rawram[0] / 1024 ** 2)}` MB total | `{rawram[2]}`% used',
                        inline=True)
        embed.add_field(name="<:cpu:622621524418887680> CPU Usage", value=f'`{psutil.cpu_percent()}`%', inline=True)
        embed.add_field(name='<:tf2autocord:624658299224326148> tf2-autocord Version', value=f'Version: `{LoaderCog.__version__}`. Up to date: {emoji}')
        embed.add_field(name=':exclamation:Command prefix',
                        value=f"Your command prefix is `{self.bot.command_prefix}`. "
                              f"Type {self.bot.command_prefix}help to list the commands you can use",
                        inline=False)
        embed.add_field(name='<:tf2automatic:624658370447671297> About the bot',
                        value='It was coded in Python to help you manage your tf2automtic bot. DM me with any '
                              'suggestions or features you would like on this bot', inline=False)
        embed.add_field(name='<:dpy:622794044547792926> Discord.py Version',
                        value=f'`{discord.__version__}` works with versions 1.1+ of Discord.py and versions 3.5.4+ of Python',
                        inline=True)
        embed.add_field(name='<:python:622621989474926622> Python Version',
                        value=f'`{python_version()}` works with versions 3.6+ (uses f-strings)',
                        inline=True)
        embed.add_field(name='<:steam:622621553800249364> Steam Version',
                        value=f'`{steam.__version__}` works with versions 3.4+ of Python',
                        inline=True)
        embed.add_field(name='Join the help server :hugging:', value='[Here](https://discord.gg/S3eVmxD)')
        embed.set_footer(text="If you need any help contact the creator of this code @Gobot1234#2435",
                         icon_url='https://cdn.discordapp.com/avatars/340869611903909888/6acc10b4cba4f29d3c54e38d412964cb.webp?size=1024')
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(DiscordCog(bot))