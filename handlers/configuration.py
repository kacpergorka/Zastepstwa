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
from pathlib import Path

# Wewnętrzne importy
from handlers.logging import logiKonsoli

# Globalna blokada modyfikacji pliku konfiguracyjnego
blokadaKonfiguracji = asyncio.Lock()

# Ścieżka pliku konfiguracyjnego
ścieżkaKonfiguracji = Path("config.json")

# Wczytywanie pliku konfiguracyjnego
def wczytajKonfiguracje(path=ścieżkaKonfiguracji):
	def uporządkuj(dane: dict, wzorzec: dict) -> dict:
		wynik = {}
		for klucz in wzorzec:
			if klucz in dane:
				wynik[klucz] = dane[klucz]
		for klucz in dane:
			if klucz not in wynik:
				wynik[klucz] = dane[klucz]
		return wynik

	domyślne = {
		"wersja": "2.2.6.0-stable",
		"token": "",
		"koniec-roku-szkolnego": "2026-06-26",
		"serwery": {},
		"szkoły": {
			"01": {
				"nazwa": "Zespół Szkół Przykładowych w Przykładowicach",
				"url": "https://kacpergorka.com/zastepstwa/01",
				"kodowanie": "iso-8859-2",
				"lista-klas": {
					"1": [],
					"2": [],
					"3": [],
					"4": [],
					"5": []
				},
				"lista-nauczycieli": []
			},
			"02": {
				"nazwa": "LXVII Liceum Ogólnokształcące w Przykładowicach",
				"url": "https://kacpergorka.com/zastepstwa/02",
				"kodowanie": "iso-8859-2",
				"lista-klas": {
					"1": [],
					"2": [],
					"3": [],
					"4": []
				},
				"lista-nauczycieli": []
			}
		},
	}
	if not path.exists():
		path.write_text(json.dumps(domyślne, ensure_ascii=False, indent=4), encoding="utf-8")
		logiKonsoli.warning("Utworzono domyślny plik konfiguracyjny. Uzupełnij jego zawartość.")
		return domyślne
	try:
		dane = json.loads(path.read_text(encoding="utf-8"))
		for klucz, wartość in domyślne.items():
			dane.setdefault(klucz, wartość)

		dane = uporządkuj(dane, domyślne)
		path.write_text(json.dumps(dane, ensure_ascii=False, indent=4), encoding="utf-8")
		if dane.get("wersja") != domyślne["wersja"]:
			logiKonsoli.warning(f"Aktualizuję wersję oprogramowania z {dane.get("wersja")} na {domyślne["wersja"]}.")
			dane["wersja"] = domyślne["wersja"]
			path.write_text(json.dumps(dane, ensure_ascii=False, indent=4), encoding="utf-8")
		return dane
	except json.JSONDecodeError as e:
		logiKonsoli.exception(f"Wystąpił błąd podczas wczytywania pliku konfiguracyjnego. Więcej informacji: {e}")
		raise

konfiguracja = wczytajKonfiguracje()

# Zapisywanie pliku konfiguracyjnego
async def zapiszKonfiguracje(konfiguracja):
	tmp = ścieżkaKonfiguracji.with_suffix(".json.tmp")
	def zapisz():
		with open(tmp, "w", encoding="utf-8") as plik:
			json.dump(konfiguracja, plik, ensure_ascii=False, indent=4)
		try:
			if ścieżkaKonfiguracji.exists():
				kopia = ścieżkaKonfiguracji.with_suffix(".json.old")
				with contextlib.suppress(Exception):
					os.remove(str(kopia))
				os.replace(str(ścieżkaKonfiguracji), str(kopia))
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd podczas zapisywania kopii w rozszerzeniu .old dla {ścieżkaKonfiguracji}. Więcej informacji: {e}")
		os.replace(str(tmp), str(ścieżkaKonfiguracji))
	try:
		await asyncio.to_thread(zapisz)
	except Exception as e:
		logiKonsoli.exception(f"Wystąpił błąd podczas zapisywania pliku konfiguracyjnego. Więcej informacji: {e}")