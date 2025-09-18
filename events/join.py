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
from handlers.logging import logiKonsoli
from helpers.helpers import ograniczWysyłanie

# Wysyła instrukcję konfiguracji oprogramowania
def ustaw(bot: discord.Client):
	@bot.event
	async def on_guild_join(guild):
		dostarczoneWiadomości = 0
		try:
			async for wpis in guild.audit_logs(limit=1, action=discord.AuditLogAction.bot_add):
				dodający = wpis.user
				try:
					embed = discord.Embed(
						title=f"**Cześć! Nadszedł czas na skonfigurowanie bota!**",
						description=f"**Informacja wstępna**\nBot został dodany do serwera **{guild.name}**, a ponieważ jesteś administratorem, który go dodał, otrzymujesz tę wiadomość. Wszystkie ważne informacje dotyczące bota oraz jego administratorów znajdziesz, używając polecenia `/informacje`.\n\n> **Jeśli napotkasz jakikolwiek błąd lub chcesz zgłosić swoją propozycję, [utwórz zgłoszenie w zakładce Issues](https://github.com/kacpergorka/Zastepstwa/issues). Jest to bardzo ważne dla prawidłowego funkcjonowania bota!**\n\n**Konfiguracja bota**\nKonfiguracja bota zaczyna się od utworzenia dedykowanego kanału tekstowego, na który po konfiguracji będą wysyłane zastępstwa, a następnie użycia polecenia `/skonfiguruj`, gdzie przejdziesz przez wygodny i intuicyjny konfigurator. W razie jakichkolwiek pytań odsyłam również do Issues na GitHubie.",
						color=discord.Color(0xca4449)
					)

					embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")
					await dodający.send(embed=embed)
					dostarczoneWiadomości += 1
					logiKonsoli.info(f"Wiadomość z instrukcjami została wysłana do {dodający.name} o ID {dodający.id}, który dodał bota na serwer {guild.name} o ID {guild.id}.")
					return
				except discord.Forbidden as e:
					logiKonsoli.warning(f"Nie można wysłać wiadomości do {dodający.name} o ID {dodający.id}, który dodał bota na serwer {guild.name} o ID {guild.id}. Więcej informacji: {e}")
		except discord.Forbidden:
			logiKonsoli.warning(f"Brak uprawnień do odczytu logów audytu na serwerze {guild.name} o ID {guild.id}.")
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd przy próbie odczytu logów audytu na serwerze {guild.name} o ID {guild.id}. Więcej informacji: {e}")

		if dostarczoneWiadomości == 0:
			kanał = guild.system_channel or next((kanał for kanał in guild.text_channels if kanał.permissions_for(guild.me).send_messages), None)
			if kanał:
				try:
					embed = discord.Embed(
						title="**Cześć! Nadszedł czas na skonfigurowanie bota!**",
						description=f"**Informacja wstępna**\nBot został dodany do serwera **{guild.name}**, a ponieważ administrator, który dodał bota na serwer nie ma włączonych wiadomości prywatnych, to wiadomość ta zostaje dostarczona na serwer. Wszystkie ważne informacje dotyczące bota oraz jego administratorów znajdziesz, używając polecenia `/informacje`.\n\n> **Jeśli napotkasz jakikolwiek błąd lub chcesz zgłosić swoją propozycję, [utwórz zgłoszenie w zakładce Issues](https://github.com/kacpergorka/Zastepstwa/issues). Jest to bardzo ważne dla prawidłowego funkcjonowania bota!**\n\n**Konfiguracja bota**\nKonfiguracja bota zaczyna się od utworzenia dedykowanego kanału tekstowego, na który po konfiguracji będą wysyłane zastępstwa, a następnie użycia polecenia `/skonfiguruj`, gdzie przejdziesz przez wygodny i intuicyjny konfigurator. W razie jakichkolwiek pytań odsyłam również do Issues na GitHubie.",
						color=discord.Color(0xca4449)
					)
					embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")
					await ograniczWysyłanie(kanał, embed=embed)
					logiKonsoli.info(f"Wiadomość z instrukcjami została wysłana na kanał #{kanał.name} o ID {kanał.id} na serwerze {guild.name} o ID {guild.id}, ponieważ żaden administrator nie odebrał prywatnej wiadomości.")
				except discord.DiscordException as e:
					logiKonsoli.exception(f"Nie można wysłać wiadomości na serwer {guild.name} o ID {guild.id}. Więcej informacji: {e}")