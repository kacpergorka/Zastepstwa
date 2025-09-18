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
import asyncio, copy, discord

# Wewnętrzne importy
from handlers.configuration import (
	blokadaKonfiguracji,
	konfiguracja,
	zapiszKonfiguracje
)
from handlers.data import folderDanych
from handlers.logging import logiKonsoli

# Usuwa serwer z konfiguracji po wyjściu bota z serwera
def ustaw(bot: discord.Client):
	@bot.event
	async def on_guild_remove(guild):
		await usuńSerwerZKonfiguracji(guild.id)

	# Usuwa konfiguracje serwera z pliku konfiguracyjnego
	async def usuńSerwerZKonfiguracji(identyfikatorSerwera: int):
		async with blokadaKonfiguracji:
			serwery = konfiguracja.setdefault("serwery", {})
			if str(identyfikatorSerwera) in serwery:
				del serwery[str(identyfikatorSerwera)]
				logiKonsoli.info(f"Usunięto serwer o ID {identyfikatorSerwera} z pliku konfiguracyjnego.")
			else:
				logiKonsoli.warning(f"Nie znaleziono konfiguracji serwera o ID {identyfikatorSerwera}. Dane nie zostały usunięte.")
			snapshot = copy.deepcopy(konfiguracja)
		await zapiszKonfiguracje(snapshot)
		for rozszerzenie in (".json", ".json.old", ".json.tmp", ".json.bad"):
			ścieżkaZasobów = folderDanych / f"{identyfikatorSerwera}{rozszerzenie}"
			if ścieżkaZasobów.exists():
				try:
					await asyncio.to_thread(ścieżkaZasobów.unlink)
					logiKonsoli.info(f"Usunięto plik zasobów ({ścieżkaZasobów}).")
				except Exception as e:
					logiKonsoli.exception(f"Wystąpił błąd podczas usuwania pliku zasobów ({ścieżkaZasobów}). Więcej informacji: {e}")