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
import asyncio

# Zewnętrzne biblioteki
import discord

# Wewnętrzne importy
from handlers.logging import logiKonsoli
from helpers.helpers import (
	ograniczReagowanie,
	ograniczUsuwanie,
	ograniczWysyłanie
)

# Wysyła aktualizacje zastępstw
async def wyślijAktualizacje(kanał, identyfikatorSerwera, informacjeDodatkowe, aktualneWpisyZastępstw, aktualnyCzas):
	opisTylkoDlaInformacjiDodatkowych = f"**Informacje dodatkowe zastępstw:**\n{informacjeDodatkowe}\n\n**Informacja o tej wiadomości:**\nTa wiadomość zawiera informacje dodatkowe umieszczone nad zastępstwami. Nie znaleziono dla Ciebie żadnych zastępstw pasujących do Twoich filtrów."
	opisDlaInformacjiDodatkowych = f"**Informacje dodatkowe zastępstw:**\n{informacjeDodatkowe}\n\n**Informacja o tej wiadomości:**\nTa wiadomość zawiera informacje dodatkowe umieszczone nad zastępstwami. Wszystkie zastępstwa znajdują się pod tą wiadomością."
	try:
		ostatniaWiadomość = None
		if informacjeDodatkowe and not aktualneWpisyZastępstw:
			embed = discord.Embed(
				title="**Zastępstwa zostały zaktualizowane!**",
				description=opisTylkoDlaInformacjiDodatkowych,
				color=discord.Color(0xca4449)
			)
			embed.set_footer(text=f"Czas aktualizacji: {aktualnyCzas}\nStworzone z ❤️ przez Kacpra Górkę!")
			await ograniczWysyłanie(kanał, embed=embed)

		elif (informacjeDodatkowe and aktualneWpisyZastępstw) or (aktualneWpisyZastępstw):
			if kanał.permissions_for(kanał.guild.me).mention_everyone:
				wzmianka = await ograniczWysyłanie(kanał, "@everyone Zastępstwa zostały zaktualizowane!", allowed_mentions=discord.AllowedMentions(everyone=True))
				await asyncio.sleep(5)
				try:
					await ograniczUsuwanie(wzmianka)
				except Exception:
					pass
			else:
				logiKonsoli.warning(f"Brak uprawnień do używania @everyone dla serwera o ID {identyfikatorSerwera}. Wzmianka została pominięta.")

			embed = discord.Embed(
				title="**Zastępstwa zostały zaktualizowane!**",
				description=opisDlaInformacjiDodatkowych,
				color=discord.Color(0xca4449)
			)
			embed.set_footer(text=f"Czas aktualizacji: {aktualnyCzas}\nStworzone z ❤️ przez Kacpra Górkę!")
			await ograniczWysyłanie(kanał, embed=embed)

			for tytuł, wpisyZastępstw in aktualneWpisyZastępstw:
				tekstZastępstw = "\n\n".join(wpisyZastępstw)
				if "Zastępstwa bez dołączonych klas!" in tytuł:
					tekstZastępstw = tekstZastępstw + "\n\n**Informacja o tej wiadomości:**\nTe zastępstwa nie posiadają dołączonej klasy, więc zweryfikuj czy przypadkiem nie dotyczą one Ciebie!"

				embed = discord.Embed(
					title=f"**{tytuł}**",
					description=tekstZastępstw,
					color=discord.Color(0xca4449)
				)
				if not "Zastępstwa bez dołączonych klas!" in tytuł:
					embed.set_footer(text="Każdy nauczyciel, którego dotyczą zastępstwa pasujące do Twoich filtrów, zostanie załączany w oddzielnej wiadomości.")
				else:
					embed.set_footer(text="Każdy nauczyciel, którego dotyczą zastępstwa bez dołączonej klasy, zostanie załączany w oddzielnej wiadomości.")
				ostatniaWiadomość = await ograniczWysyłanie(kanał, embed=embed)

		if ostatniaWiadomość and not "Zastępstwa bez dołączonych klas!" in tytuł:
			await ograniczReagowanie(ostatniaWiadomość, "❤️")
	except discord.DiscordException as e:
		logiKonsoli.exception(f"Wystąpił błąd podczas wysyłania wiadomości dla serwera o ID {identyfikatorSerwera}. Więcej informacji: {e}")
	except Exception as e:
		logiKonsoli.exception(f"Wystąpił nieoczekiwany błąd podczas wysyłania wiadomości dla serwera o ID {identyfikatorSerwera}. Więcej informacji: {e}")