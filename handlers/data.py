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
import asyncio, contextlib, json, os
from collections import defaultdict
from pathlib import Path

# Wewnętrzne importy
from handlers.logging import logiKonsoli

# Ścieżka folderu z plikami danych
folderDanych = Path("resources")
folderDanych.mkdir(exist_ok=True)

# Globalna blokada modyfikacji pliku danych per serwer
blokadaPlikuNaSerwer = defaultdict(lambda: asyncio.Lock())

# Zarządza plikami danych serwerów
async def zarządzajPlikiemDanych(identyfikatorSerwera, dane=None):
	identyfikatorSerwera = str(identyfikatorSerwera)
	ścieżkaPliku = folderDanych / f"{identyfikatorSerwera}.json"
	tmp = ścieżkaPliku.with_suffix(".json.tmp")
	async with blokadaPlikuNaSerwer[identyfikatorSerwera]:
		try:
			if dane is not None:
				# Zapisuje plik danych wybranego serwera
				def zapisz():
					with open(tmp, "w", encoding="utf-8") as plik:
						json.dump(dane, plik, ensure_ascii=False, indent=4)
					try:
						if ścieżkaPliku.exists():
							kopia = ścieżkaPliku.with_suffix(".json.old")
							with contextlib.suppress(Exception):
								os.remove(str(kopia))
							os.replace(str(ścieżkaPliku), str(kopia))
					except Exception as e:
						logiKonsoli.exception(f"Wystąpił błąd podczas zapisywania kopii w rozszerzeniu .old dla {ścieżkaPliku}. Więcej informacji: {e}")
					os.replace(str(tmp), str(ścieżkaPliku))
				await asyncio.to_thread(zapisz)
				return True

			# Odczytuje plik danych wybranego serwera
			def odczytaj():
				return ścieżkaPliku.exists()
			if await asyncio.to_thread(odczytaj):
				try:
					def wczytaj():
						return json.loads(ścieżkaPliku.read_text(encoding="utf-8"))
					return await asyncio.to_thread(wczytaj)
				except (json.JSONDecodeError, UnicodeDecodeError) as e:
					logiKonsoli.exception(f"Wystąpił błąd podczas wczytywania pliku danych. Więcej informacji: {e}")
					uszkodzony = ścieżkaPliku.with_suffix(".json.bad")
					try:
						await asyncio.to_thread(os.replace, str(ścieżkaPliku), str(uszkodzony))
						logiKonsoli.exception(f"Uszkodzony plik danych został przeniesiony do {uszkodzony}. Wczytano pustą zawartość.")
					except Exception as e:
						logiKonsoli.exception(f"Wystąpił błąd podczas przenoszenia uszkodzonego pliku danych. Więcej informacji: {e}")
					return {}
			return {}
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd podczas operacji na pliku danych. Więcej informacji: {e}")
			if tmp.exists():
				try:
					tmp.unlink()
				except Exception as e:
					logiKonsoli.exception(f"Nie udało się usunąć pliku tymczasowego ({tmp}). Więcej informacji: {e}")
					pass
			return {}