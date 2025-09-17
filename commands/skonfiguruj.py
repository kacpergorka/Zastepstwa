#
#
#    ▄▄▄▄▄▄▄▄     ▄▄       ▄▄▄▄    ▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄      ▄▄▄▄    ▄▄▄▄▄▄▄▄ ▄▄      ▄▄    ▄▄   
#    ▀▀▀▀▀███    ████    ▄█▀▀▀▀█   ▀▀▀██▀▀▀  ██▀▀▀▀▀▀  ██▀▀▀▀█▄  ▄█▀▀▀▀█   ▀▀▀██▀▀▀ ██      ██   ████  
#        ██▀     ████    ██▄          ██     ██        ██    ██  ██▄          ██    ▀█▄ ██ ▄█▀   ████  
#      ▄██▀     ██  ██    ▀████▄      ██     ███████   ██████▀    ▀████▄      ██     ██ ██ ██   ██  ██ 
#     ▄██       ██████        ▀██     ██     ██        ██             ▀██     ██     ███▀▀███   ██████ 
#    ███▄▄▄▄▄  ▄██  ██▄  █▄▄▄▄▄█▀     ██     ██▄▄▄▄▄▄  ██        █▄▄▄▄▄█▀     ██     ███  ███  ▄██  ██▄
#    ▀▀▀▀▀▀▀▀  ▀▀    ▀▀   ▀▀▀▀▀       ▀▀     ▀▀▀▀▀█▀▀  ▀▀         ▀▀▀▀▀       ▀▀     ▀▀▀  ▀▀▀  ▀▀    ▀▀
#                                                █▄▄                                                   
#

# Zewnętrzne biblioteki
import discord

# Wewnętrzne importy
from classes.commands import WidokGłówny
from handlers.configuration import konfiguracja
from handlers.logging import (
	logiKonsoli,
	logujPolecenia
)
from main import bot

@bot.tree.command(name="skonfiguruj", description="Skonfiguruj bota, ustawiając kanał tekstowy i filtry zastępstw.")
@discord.app_commands.guild_only()
@discord.app_commands.describe(kanał="Kanał tekstowy, na który będą wysyłane powiadomienia z zastępstwami.", szkoła="Szkoła, z której będą pobierane informacje o zastępstwach.")
@discord.app_commands.choices(szkoła=[discord.app_commands.Choice(name=nazwaSzkoły.get("nazwa", identyfikatorSzkoły), value=identyfikatorSzkoły) for identyfikatorSzkoły, nazwaSzkoły in (konfiguracja.get("szkoły") or {}).items()])
async def skonfiguruj(interaction: discord.Interaction, szkoła: str, kanał: discord.TextChannel):
	try:
		if not interaction.user.guild_permissions.administrator:
			embed = discord.Embed(
				title="**Polecenie nie zostało wykonane!**",
				description="Nie masz uprawnień do użycia tego polecenia. Może ono zostać użyte wyłącznie przez administratora serwera.",
				color=discord.Color(0xca4449),
			)
			embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")
			await interaction.response.send_message(embed=embed, ephemeral=True)
			logujPolecenia(interaction, success=False, error_message="Brak uprawnień.")
			return

		view = WidokGłówny(identyfikatorKanału=str(kanał.id), szkoła=szkoła)
		embed = discord.Embed(
			title="**Skonfiguruj filtrowanie zastępstw**",
			description=("**Jesteś uczniem?**\nAby dostawać powiadomienia z nowymi zastępstwami przypisanymi Twojej klasie, naciśnij przycisk **Uczeń**.\n\n**Jesteś nauczycielem?**\nAby dostawać powiadomienia z nowymi zastępstwami przypisanymi Tobie, naciśnij przycisk **Nauczyciel**.\n\nAby wyczyścić wszystkie ustawione filtry, naciśnij przycisk **Wyczyść filtry**."),
			color=discord.Color(0xca4449),
		)
		embed.set_footer(text="Projekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")
		await interaction.response.send_message(embed=embed, view=view)
		logujPolecenia(interaction, success=True)
	except Exception as e:
		logujPolecenia(interaction, success=False, error_message=str(e))
		logiKonsoli.exception(f"Wystąpił błąd podczas wywołania polecenia /skonfiguruj. Więcej informacji: {e}")
		try:
			if interaction.response.is_done():
				await interaction.followup.send(f"Wystąpił błąd. Więcej informacji: {str(e)}", ephemeral=True)
			else:
				await interaction.response.send_message(f"Wystąpił błąd. Więcej informacji: {str(e)}", ephemeral=True)
		except Exception:
			pass