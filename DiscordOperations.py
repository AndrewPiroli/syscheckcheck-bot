import discord
from enum import Enum, auto
from pprint import pprint
from pathlib import Path
max_attach_size = 10240 # 10 KB
storage = Path("./temp")

class MessageStatus(Enum):
    OK = auto()
    UNKNOWN = auto()
    NO_ATTACHMENT = auto()
    ATTACHMENT_SIZE = auto()
    ATTACHMENT_TYPE = auto()


client = discord.Client()

@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.attachments:
        print("yeet")
        attachment = message.attachments[0]
    else:
        return
    if attachment.width:
        print('no image')
        return
    if attachment.size > max_attach_size:
        print('too big')
        return
    


client.run(open("private-discord-token.txt", "r").read().strip())