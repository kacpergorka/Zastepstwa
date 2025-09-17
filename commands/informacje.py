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
from handlers.configuration import konfiguracja
from handlers.logging import (
	logiKonsoli,
	logujPolecenia
)
from helpers.helpers import (
	pobierzCzasDziałania,
	pobierzLiczbęSerwerów
)

def ustaw(bot: discord.Client):
	@bot.tree.command(name="informacje", description="Wyświetl najważniejsze informacje dotyczące bota i jego administratorów")
	async def informacje(interaction: discord.Interaction):
		try:
			embed = discord.Embed(
				title="**Informacje dotyczące bota**",
				description="Otwartoźródłowe oprogramowanie informujące o aktualizacjach zastępstw. W celu skontaktowania się z jednym z administratorów bota, naciśnij jednego z poniżej widniejących. Nastąpi przekierowanie na zewnętrzną stronę internetową.",
				color=discord.Color(0xca4449)
			)
			wersja = konfiguracja.get("wersja")
			embed.add_field(name="Wersja bota:", value=wersja)
			embed.add_field(name="Repozytorium GitHuba:", value=("[kacpergorka/zastepstwa](https://github.com/kacpergorka/zastepstwa)"))
			embed.add_field(name="Administratorzy bota:", value="[Kacper Górka](https://kacpergorka.com/)")
			if pobierzLiczbęSerwerów(bot) == 1:
				embed.add_field(name="Liczba serwerów:", value=(f"Bot znajduje się na **{pobierzLiczbęSerwerów(bot)}** serwerze."))
			else:
				embed.add_field(name="Liczba serwerów:", value=(f"Bot znajduje się na **{pobierzLiczbęSerwerów(bot)}** serwerach."))
			embed.add_field(name="Bot pracuje bez przerwy przez:", value=pobierzCzasDziałania(bot))
			embed.set_footer(text="Projekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")
			await interaction.response.send_message(embed=embed)
			logujPolecenia(interaction, success=True)
		except Exception as e:
			logujPolecenia(interaction, success=False, error_message=str(e))
			logiKonsoli.exception(f"Wystąpił błąd podczas wywołania polecenia /informacje. Więcej informacji: {e}")
			try:
				await interaction.response.send_message(f"Wystąpił błąd. Więcej informacji: {str(e)}", ephemeral=True)
			except Exception:
				pass