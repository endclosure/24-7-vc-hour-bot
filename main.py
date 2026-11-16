import json
import logging
from pathlib import Path

import discord
from discord import app_commands


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

with CONFIG_PATH.open(encoding="utf-8") as config_file:
    config = json.load(config_file)

TOKEN = config.get("token")
GUILD_ID = config.get("guildid")
if not TOKEN or TOKEN == "token":
    raise RuntimeError("Set your Discord bot token in config.json before starting the bot.")

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.default()
intents.voice_states = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@tree.command(name="join", description="Join the voice channel you are currently in.")
async def join(interaction: discord.Interaction) -> None:
    voice_state = getattr(interaction.user, "voice", None)
    channel = voice_state.channel if voice_state else None
    if channel is None:
        await interaction.response.send_message(
            "Join a voice channel first, then use `/join`.", ephemeral=True
        )
        return

    voice_client = interaction.guild.voice_client if interaction.guild else None
    try:
        if voice_client and voice_client.is_connected():
            if voice_client.channel != channel:
                await voice_client.move_to(channel)
        else:
            await channel.connect()
    except (discord.Forbidden, discord.HTTPException, discord.ClientException) as exc:
        logging.exception("Could not join voice channel")
        await interaction.response.send_message(
            f"I couldn't join that voice channel: {exc}", ephemeral=True
        )
        return

    await interaction.response.send_message(f"Connected to **{channel.name}**.")


@tree.command(name="disconnect", description="Disconnect the bot from voice.")
@app_commands.default_permissions(administrator=True)
async def disconnect(interaction: discord.Interaction) -> None:
    if not interaction.permissions.administrator:
        await interaction.response.send_message(
            "Only server administrators can use this command.", ephemeral=True
        )
        return

    voice_client = interaction.guild.voice_client if interaction.guild else None
    if voice_client is None or not voice_client.is_connected():
        await interaction.response.send_message("I'm not connected to a voice channel.", ephemeral=True)
        return

    await voice_client.disconnect()
    await interaction.response.send_message("Disconnected from voice.")


@client.event
async def on_ready() -> None:
    logging.info("Logged in as %s (%s)", client.user, client.user.id if client.user else "unknown")
    if GUILD_ID:
        try:
            guild = discord.Object(id=int(GUILD_ID))
        except (TypeError, ValueError):
            logging.error("guildid in config.json must be a numeric Discord server ID")
            return
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
    else:
        await tree.sync()


client.run(TOKEN)
