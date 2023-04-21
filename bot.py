from discord.ext import commands
import discord
import os

from team.components import VoteView

intents = discord.Intents.default()
# intents.message_content = True
intents.members = True

extensions = [
    'admin.cog',
    'match.cog',
    'results.cog',
    'sokuji.cog',
    'team.cog',
    'utility.cog',
    'friend.cog'
]

class Bot(commands.Bot):

    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",
            intents=intents,
            case_insensitive=True,
            help_command=None,
            owner_id = 123456789
        )
        self.persistent_views_added: bool = False


    async def on_ready(self):
        if not self.persistent_views_added:
            self.add_view(VoteView())
            self.persistent_views_added = True
        print('Bot ready.')


bot = Bot()
bot.load_extensions(*extensions)

bot.run(os.environ['BOT_TOKEN'])
