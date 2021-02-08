import discord
from enum import Enum, auto
from pprint import pprint
from pathlib import Path
import uuid
import asyncio
from typing import List
max_attach_size = 10240 # 10 KB
storage = Path("temp").absolute()

class MessageStatus(Enum):
    OK = auto()
    UNKNOWN = auto()
    NO_ATTACHMENT = auto()
    ATTACHMENT_SIZE = auto()
    ATTACHMENT_TYPE = auto()


client = discord.Client()
async_tasks = []
active_files = []

async def create_file(attachment: discord.Attachment):
    filename = f"{uuid.uuid4()}.txt" # This *probably* won't collide ¯\_(ツ)_/¯ I'll write a check later
    with open(storage / filename, "wb") as syscheck_file:
        await attachment.save(syscheck_file)
        active_files.append(filename)
    
async def clean_tasks(tasklist: List[asyncio.Task]):
    to_pop = []
    for idx,task in enumerate(tasklist):
        if task.done():
            await task
            to_pop.append(idx)
    for idx in to_pop:
        tasklist.pop(idx)

@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")

@client.event
async def on_message(message):
    janitor = asyncio.create_task(clean_tasks(async_tasks))
    if message.author == client.user:
        return
    if message.attachments:
        print("yeet")
        attachment: discord.Attachment = message.attachments[0]
    else:
        return
    if attachment.width:
        print('no image')
        return
    if attachment.size > max_attach_size:
        print('too big')
        return
    if "syscheck" in attachment.filename:
        async_tasks.append(asyncio.create_task(create_file(attachment)))
    await janitor


client.run(open("private-discord-token.txt", "r").read().strip())