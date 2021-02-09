import discord
from enum import Enum, auto
from pathlib import Path
import uuid
import asyncio
from typing import List
import SyscheckOperations
import os

max_attach_size = 10240  # 10 KB
storage = Path("temp").absolute()
disclaimer = "This bot is currently in alpha and under active development. \n\
It only speaks English, and may fail to reply on weirdly formatted data. \n\
The bot will never reply to abusers"


class DiscordSyscheck(discord.Client):
    tasks_cleaning = False
    async_tasks = []
    active_files = []

    async def create_file(self, attachment: discord.Attachment) -> Path:
        filename = (
            storage / f"{uuid.uuid4()}.syscheck.txt"
        )  # This *probably* won't collide ¯\_(ツ)_/¯ I'll write a check later
        with open(filename, "wb") as syscheck_file:
            await attachment.save(syscheck_file)
            print(filename)
            self.active_files.append(filename)
        return filename.absolute()

    async def handle_syscheck(self, msg: discord.Message):
        attachment = msg.attachments[0]
        filename = await self.create_file(attachment)
        report = SyscheckOperations.summaraize(filename)
        reply_msg = discord.Embed(title="Syscheck Summary")
        reply_msg.add_field(name="Report", value=report, inline=False)
        reply_msg.add_field(name="Disclaimer", value=disclaimer, inline=False)
        await msg.channel.send(embed=reply_msg)

    async def clean_tasks(self):
        while True:
            await asyncio.sleep(60)
            try:
                to_pop = []
                self.tasks_cleaning = True
                for idx, task in enumerate(self.async_tasks):
                    if task.done():
                        try:
                            await task
                        except:
                            task.cancel()
                        to_pop.append(idx)
                for idx in sorted(to_pop, reverse=True):
                    print(f"Clean {idx}")
                    self.async_tasks.pop(idx)
            finally:
                self.tasks_cleaning = False
            for syscheck_file in os.listdir(storage):
                if ("syscheck.txt" in syscheck_file) and (
                    Path(storage / syscheck_file) not in self.active_files
                ):
                    print(f"Unlinking old {syscheck_file}")
                    os.unlink(storage / syscheck_file)

    async def on_ready(self):
        print(f"Bot ready {client.user}")
        asyncio.create_task(self.clean_tasks())

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.attachments:
            attachment: discord.Attachment = message.attachments[0]
        else:
            return
        if attachment.width:
            print("no image")
            return
        if attachment.size > max_attach_size:
            print("too big")
            return
        if "syscheck" in attachment.filename.lower():
            while self.tasks_cleaning:
                await asyncio.sleep(0.1)
            self.async_tasks.append(asyncio.create_task(self.handle_syscheck(message)))


client = DiscordSyscheck()
client.run(open("private-discord-token.txt", "r").read().strip())
