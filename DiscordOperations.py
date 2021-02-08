import discord
from enum import Enum, auto
from pprint import pprint
from pathlib import Path
import uuid
import asyncio
from typing import List
import SyscheckOperations

max_attach_size = 10240  # 10 KB
storage = Path("temp").absolute()
disclaimer = "This bot is currently in alpha and under active development. \n\
It only speaks English, and may fail to reply on weirdly formatted data. \n\
The bot will never reply to abusers"


class MessageStatus(Enum):
    OK = auto()
    UNKNOWN = auto()
    NO_ATTACHMENT = auto()
    ATTACHMENT_SIZE = auto()
    ATTACHMENT_TYPE = auto()


client = discord.Client()
async_tasks = []
active_files = []


async def create_file(attachment: discord.Attachment) -> Path:
    filename = (
        storage / f"{uuid.uuid4()}.txt"
    )  # This *probably* won't collide ¯\_(ツ)_/¯ I'll write a check later
    with open(storage / filename, "wb") as syscheck_file:
        await attachment.save(syscheck_file)
        active_files.append(filename)
    return filename.absolute()


async def handle_syscheck(msg: discord.Message):
    attachment = msg.attachments[0]
    filename = await create_file(attachment)
    report = SyscheckOperations.summaraize(filename)
    await msg.reply(f"```{report}\n\n{disclaimer}```")


async def clean_tasks(tasklist: List[asyncio.Task]):
    to_pop = []
    for idx, task in enumerate(tasklist):
        if task.done():
            try:
                await task
            except:
                task.cancel()
            to_pop.append(idx)
    for idx in to_pop:
        print(f"Clean {idx}")
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
        attachment: discord.Attachment = message.attachments[0]
    else:
        await janitor
        return
    if attachment.width:
        print("no image")
        return
    if attachment.size > max_attach_size:
        print("too big")
        return
    if "syscheck" in attachment.filename.lower():
        async_tasks.append(asyncio.create_task(handle_syscheck(message)))
    await janitor


client.run(open("private-discord-token.txt", "r").read().strip())
