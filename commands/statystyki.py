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

# Standardowe biblioteki
import contextlib

# Zewnętrzne biblioteki
import discord

# Wewnętrzne importy
from handlers.configuration import (
	blokadaKonfiguracji,
	konfiguracja
)
from handlers.data import zarządzajPlikiemDanych
from handlers.logging import (
	logiKonsoli,
	logujPolecenia
)
from helpers.helpers import (
	odmieńZastępstwa,
	zwróćNazwyKluczy
)

def ustaw(bot: discord.Client):
	@bot.tree.command(name="statystyki", description="Wyświetl bieżące statystyki zastępstw w tym roku szkolnym dla tego serwera.")
	@discord.app_commands.guild_only()
	async def statystyki(interaction: discord.Interaction):
		try:
			identyfikatorSerwera = interaction.guild.id
			dane = await zarządzajPlikiemDanych(identyfikatorSerwera) or {}
			licznik = int(dane.get("licznik-zastepstw", 0))
			statystyki = dane.get("statystyki-nauczycieli", {}) or {}

			async with blokadaKonfiguracji:
				konfiguracjaSerwera = (konfiguracja.get("serwery", {}) or {}).get(str(identyfikatorSerwera), {}).copy()
			wybraniNauczyciele = konfiguracjaSerwera.get("wybrani-nauczyciele", []) or []
			wybraneKlasy = konfiguracjaSerwera.get("wybrane-klasy", [])

			if licznik == 0:
				embed = discord.Embed(
					title="**Statystyki zastępstw**",
					description="Dla tego serwera od rozpoczęcia roku szkolnego nie odnotowano jeszcze żadnych zastępstw.",
					color=discord.Color(0xca4449)
				)
				embed.set_footer(text="Projekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")
				await interaction.response.send_message(embed=embed)
				return

			if wybraneKlasy and not wybraniNauczyciele:
				embed = discord.Embed(
					title="**Statystyki zastępstw**",
					description=f"Dla tego serwera od rozpoczęcia roku szkolnego dostarczono **{licznik}** {odmieńZastępstwa(licznik)}! Poniżej znajduje się lista nauczycieli z największą liczbą zarejestrowanych zastępstw.",
					color=discord.Color(0xca4449)
				)

				if isinstance(statystyki, dict) and statystyki:
					sortowanie = sorted(statystyki.items(), key=lambda x: (-int(x[1]), x[0]))
					wolneMiejsca = 24 - len(embed.fields)
					if wolneMiejsca > 0:
						for nauczyciel, liczba in sortowanie[:wolneMiejsca]:
							embed.add_field(name=str(nauczyciel), value=f"Liczba zastępstw: {int(liczba)}", inline=True)
				embed.set_footer(text="Projekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")
				await interaction.response.send_message(embed=embed)

			elif (wybraneKlasy and wybraniNauczyciele) or (wybraniNauczyciele and not wybraneKlasy):
				embed = discord.Embed(
					title="**Statystyki zastępstw**",
					description=f"Dla tego serwera od rozpoczęcia roku szkolnego dostarczono **{licznik}** {odmieńZastępstwa(licznik)}! Poniżej znajduje się lista nauczycieli z największą liczbą zarejestrowanych zastępstw. (Pominięto nauczycieli ustawionych w filtrze).",
					color=discord.Color(0xca4449)
				)

				wykluczeni = set()
				for nauczyciel in wybraniNauczyciele:
					wykluczeni |= zwróćNazwyKluczy(nauczyciel)

				pozostali = {}
				if isinstance(statystyki, dict):
					for nazwa, liczba in statystyki.items():
						if not (zwróćNazwyKluczy(nazwa) & wykluczeni):
							pozostali[nazwa] = int(liczba)
				if pozostali:
					sortowanie = sorted(pozostali.items(), key=lambda x: (-int(x[1]), x[0]))
					wolneMiejsca = 24 - len(embed.fields)
					if wolneMiejsca > 0:
						for nauczyciel, liczba in sortowanie[:wolneMiejsca]:
							embed.add_field(name=str(nauczyciel), value=f"Liczba zastępstw: {int(liczba)}", inline=True)
				else:
					embed.add_field(name="Brak danych", value="Nie znaleziono odpowiednich statystyk dla tego serwera.", inline=False)
				embed.set_footer(text="Projekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")
				await interaction.response.send_message(embed=embed)

			else:
				if not wybraneKlasy and not wybraniNauczyciele:
					embed = discord.Embed(
						title="**Polecenie nie zostało wykonane!**",
						description=f"Aby wykonać to polecenie, poproś administratora o skonfigurowanie zastępstw. Jesteś administratorem? Użyj polecenia `/skonfiguruj` i postępuj zgodnie z instrukcjami.",
						color=discord.Color(0xca4449)
					)
					embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")
					await interaction.response.send_message(embed=embed, ephemeral=True)
					logujPolecenia(interaction, success=False, error_message="Zastępstwa nie zostały skonfigurowane.")
					return
			logujPolecenia(interaction, success=True)
		except Exception as e:
			logujPolecenia(interaction, success=False, error_message=str(e))
			logiKonsoli.exception(f"Wystąpił błąd podczas wywołania polecenia /statystyki: {e}")
			with contextlib.suppress(Exception):
				if interaction.response.is_done():
					await interaction.followup.send("Wystąpił błąd podczas wyświetlania statystyk. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)
				else:
					await interaction.response.send_message("Wystąpił błąd podczas wyświetlania statystyk. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)