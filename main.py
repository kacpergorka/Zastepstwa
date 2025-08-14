# Standardowe biblioteki Pythona
import asyncio
from collections import defaultdict
import contextlib
import copy
from datetime import datetime
import difflib
import hashlib
import json
import logging
import logging.handlers
import os
from pathlib import Path
import re
import signal
import sys
import unicodedata

# Zewnętrzne biblioteki
import aiohttp
import discord
from discord import app_commands
import pytz
from bs4 import BeautifulSoup

class zastępstwa(discord.Client):
	def __init__(self, *, intents: discord.Intents):
		super().__init__(intents=intents)
		self.tree = app_commands.CommandTree(self)

	async def setup_hook(self):
		try:
			self.połączenie_http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
		except Exception as e:
			logiKonsoli.critical(f"Nie udało się utworzyć sesji HTTP. Więcej informacji: {e}")

	async def close(self):
		if getattr(self, "połączenie_http", None):
			try:
				await self.połączenie_http.close()
			except Exception as e:
				logiKonsoli.exception(f"Wystąpił błąd podczas zamykania sesji HTTP. Więcej informacji: {e}")
		await super().close()

	async def on_ready(self):
		try:
			self.start_time = datetime.now()
			logiKonsoli.info(f"Zalogowano jako {self.user.name} (ID: {self.user.id}).")
			await self.tree.sync()
			asyncio.create_task(sprawdźAktualizacje())
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd podczas wywoływania funkcji on_ready. Więcej informacji: {e}")

	def pobierzLiczbęSerwerów(self):
		return len(self.guilds)

	def pobierzCzasDziałania(self):
		czasDziałania = datetime.now() - self.start_time
		dni, reszta = divmod(czasDziałania.total_seconds(), 86400)
		godziny, reszta = divmod(reszta, 3600)
		minuty, sekundy = divmod(reszta, 60)

		return f"**{int(dni)}**d, **{int(godziny)}**h, **{int(minuty)}**m i **{int(sekundy)}**s."

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
bot = zastępstwa(intents=intents)

# Konfiguracja logowania
class formatStrefyCzasowej(logging.Formatter):
	def formatTime(self, record, datefmt=None):
		dt = datetime.fromtimestamp(record.created, pytz.timezone("Europe/Warsaw"))
		if datefmt:
			return dt.strftime(datefmt)
		return dt.strftime("%d-%m-%Y %H:%M:%S")

def skonfigurujLogi():
	folderLogów = Path("Logs")
	folderLogów.mkdir(exist_ok=True)

	logiKonsoli = logging.getLogger("discord")
	logiKonsoli.setLevel(logging.INFO)
	logiPoleceń = logging.getLogger("discord.commands")
	logiPoleceń.setLevel(logging.DEBUG)

	ścieżkaLogów = folderLogów / "console.log"

	obsługaLogów = logging.handlers.RotatingFileHandler(
		filename=ścieżkaLogów,
		encoding="utf-8",
		maxBytes=32 * 1024 * 1024,
		backupCount=31
	)

	formatter = formatStrefyCzasowej("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
	obsługaLogów.setFormatter(formatter)

	logiKonsoli.addHandler(obsługaLogów)
	logiPoleceń.addHandler(obsługaLogów)

	return logiKonsoli, logiPoleceń

logiKonsoli, logiPoleceń = skonfigurujLogi()

def logujPolecenia(interaction: discord.Interaction, success: bool, error_message: str = None):
	status = "pomyślnie" if success else "niepomyślnie"
	informacjaBłędu = f" ({error_message})" if error_message else ""

	opcje = []
	try:
		opcje = (interaction.data or {}).get("options", []) if interaction and getattr(interaction, "data", None) else []
	except Exception:
		opcje = []

	if opcje:
		użyteArgumenty = "Użyte argumenty: " + ", ".join(f"{opcja.get('name')} ({opcja.get('value')}). " for opcja in opcje)
	else:
		użyteArgumenty = ""

	try:
		if getattr(interaction, "guild", None):
			miejsce = (
				f"w serwerze '{interaction.guild.name}' (ID: {interaction.guild.id}) "
				f"na kanale '{getattr(interaction.channel, 'name', 'N/A')}' (ID: {getattr(interaction.channel, 'id', 'N/A')}). "
			)
		else:
			miejsce = "w wiadomości prywatnej (DM). "
	except Exception:
		miejsce = ""

	nazwaPolecenia = getattr(getattr(interaction, "command", None), "name", getattr(interaction, "command_name", "unknown"))
	użytkownik = f"{getattr(interaction, 'user', 'Unknown')}"
	identyfikatorUżytkownika = getattr(getattr(interaction, "user", None), "id", "Unknown")

	wiadomośćLogu = (
		f"Użytkownik: {użytkownik} (ID: {identyfikatorUżytkownika}) "
		f'użył komendy "{nazwaPolecenia}" '
		f"{miejsce}"
		f"{użyteArgumenty}"
		f"Komenda wykonana {status}.{informacjaBłędu}"
	)
	logiPoleceń.info(wiadomośćLogu)

# Zarządzanie plikiem konfiguracyjnym
ścieżkaKonfiguracji = Path("config.json")
blokadaKonfiguracji = asyncio.Lock()

def wczytajKonfiguracje(path=ścieżkaKonfiguracji):
	if not path.exists():
		default = {
			"wersja": "2.0.1-stable",
			"url": "",
			"kodowanie": "",
			"token": "",
			"serwery": {},
			"lista-klas": {
				"1": [],
				"2": [],
				"3": [],
				"4": [],
				"5": []
			},
			"lista-nauczycieli": []
		}
		path.write_text(json.dumps(default, ensure_ascii=False, indent=4), encoding="utf-8")
		logiKonsoli.warning("Utworzono domyślny config.json. Uzupełnij plik konfiguracyjny.")
		return default

	try:
		dane = json.loads(path.read_text(encoding="utf-8"))
		dane.setdefault("serwery", {})
		return dane
	except json.JSONDecodeError as e:
		logiKonsoli.exception(f"Wystąpił błąd podczas wczytywania config.json. Więcej informacji: {e}")
		raise

konfiguracja = wczytajKonfiguracje()

async def zapiszKonfiguracje(konfiguracja):
	tmp = ścieżkaKonfiguracji.with_suffix(".json.tmp")

	def zapisz():
		with open(tmp, "w", encoding="utf-8") as plik:
			json.dump(konfiguracja, plik, ensure_ascii=False, indent=4)
		os.replace(str(tmp), str(ścieżkaKonfiguracji))

	try:
		await asyncio.to_thread(zapisz)
	except Exception as e:
		logiKonsoli.exception(f"Wystąpił błąd podczas zapisywania pliku konfiguracyjnego. Więcej informacji: {e}")

async def usuńSerwerZKonfiguracji(identyfikatorSerwera: int):
	async with blokadaKonfiguracji:
		serwery = konfiguracja.setdefault("serwery", {})
		if str(identyfikatorSerwera) in serwery:
			del serwery[str(identyfikatorSerwera)]
			logiKonsoli.info(f"Usunięto serwer o ID {identyfikatorSerwera} z pliku config.json.")
		else:
			logiKonsoli.warning(f"Nie znaleziono konfiguracji serwera o ID {identyfikatorSerwera}. Dane nie zostały usunięte.")

		snapshot = copy.deepcopy(konfiguracja)

	await zapiszKonfiguracje(snapshot)

	ścieżkaZasobów = folderDanych / f"{identyfikatorSerwera}.json"
	if ścieżkaZasobów.exists():
		try:
			await asyncio.to_thread(ścieżkaZasobów.unlink)
			logiKonsoli.info(f"Usunięto plik zasobów: {ścieżkaZasobów}.")
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd podczas usuwania pliku zasobów: {ścieżkaZasobów}. Więcej informacji: {e}")

# Obliczanie hashu
def obliczHash(dane):
	if isinstance(dane, str):
		wejścieHash = dane.strip()

	elif isinstance(dane, list):
		części = []
		for tytuł, wpisy in sorted(dane, key=lambda pozycja: pozycja[0]):
			części.append(tytuł.strip())
			for wpis in sorted(wpisy):
				części.append(wpis.strip())
		wejścieHash = "\n".join(części)

	else:
		wejścieHash = str(dane)
	return hashlib.sha256(wejścieHash.encode("utf-8")).hexdigest()

# Pobieranie zawartości witryny
async def pobierzZawartośćWitryny(url):
	logiKonsoli.debug(f"Pobieranie URL: {url}")
	try:
		async with bot.połączenie_http.get(url) as response:
			response.raise_for_status()
			kodowanie = konfiguracja.get("kodowanie")
			text = await response.text(encoding=kodowanie, errors="ignore")
			return BeautifulSoup(text, "html.parser")
	except asyncio.TimeoutError as e:
		logiKonsoli.warning(f"Przekroczono czas oczekiwania na połączenie. Więcej informacji: {e}")
	except aiohttp.ClientError as e:
		logiKonsoli.exception(f"Wystąpił błąd klienta HTTP podczas pobierania strony. Więcej informacji: {e}")
	except Exception as e:
		logiKonsoli.exception(f"Wystąpił błąd podczas pobierania strony. Więcej informacji: {e}")
	return None

# Normalizacja tekstu i klucze dopasowań
def normalizujTekst(tekst: str) -> str:
	if not tekst or not isinstance(tekst, str):
		return ""
	tekst = tekst.strip()
	tekst = unicodedata.normalize("NFKD", tekst)
	tekst = "".join(ch for ch in tekst if not unicodedata.combining(ch))
	tekst = tekst.replace(".", " ")
	tekst = re.sub(r"\s+", " ", tekst)
	return tekst.lower()

def zwróćNazwyKluczy(nazwa: str) -> set:
	norma = normalizujTekst(nazwa)
	if not norma:
		return set()
	części = norma.split()
	klucze = {norma}
	if części:
		klucze.add(części[-1])
	if len(części) >= 1:
		klucze.add(f"{części[0][0]} {części[-1]}")
		klucze.add(f"{części[0][0]}{części[-1]}")
	return klucze

def wyodrębnijNauczycieli(nazwaNagłówka: str, komórkaZastępcy: str) -> set:
	wyodrębnieniNauczyciele = set()
	if nazwaNagłówka and nazwaNagłówka.strip():
		wyodrębnieniNauczyciele.add(nazwaNagłówka.strip())
	if komórkaZastępcy and komórkaZastępcy.strip():
		części = re.split(r"[,\n;/&]| i | I ", komórkaZastępcy)
		for nauczyciel in części:
			nauczyciel = nauczyciel.strip()
			if nauczyciel and nauczyciel != "&nbsp;":
				wyodrębnieniNauczyciele.add(nauczyciel)
	return wyodrębnieniNauczyciele

def dopasujNauczyciela(wyodrębnieniNauczyciele: set, wybraniNauczyciele: list) -> bool:
	if not wybraniNauczyciele:
		return False
	zbiórKluczy = set()
	for dopasowanie in wyodrębnieniNauczyciele:
		zbiórKluczy |= zwróćNazwyKluczy(dopasowanie)
	kluczeWybranychNauczycieli = set()
	for nauczyciel in wybraniNauczyciele:
		kluczeWybranychNauczycieli |= zwróćNazwyKluczy(nauczyciel)
	return bool(zbiórKluczy & kluczeWybranychNauczycieli)

def dopasujDoKlasy(komórkiWiersza: list, wybraneKlasy: list) -> bool:
	if not wybraneKlasy:
		return False

	komórki = komórkiWiersza[:]

	if len(komórki) > 1 and komórki[1]:
		komórki[1] = komórki[1].split('-', 1)[0]

	tekst = " ".join(komórka or "" for komórka in komórki)
	tekst = normalizujTekst(tekst)
	tekst = re.sub(r"[\(\)]", " ", tekst)
	tekst = re.sub(r"\s+", " ", tekst)
	for klasa in wybraneKlasy:
		normaKlasy = normalizujTekst(klasa)
		części = normaKlasy.split()
		wzór = r"\b" + r"\s*".join(map(re.escape, części)) + r"\b"
		if re.search(wzór, tekst):
			return True
	return False

# Wyodrębnienie danych z pobranego pliku witryny
def wyodrębnijDane(zawartośćStrony, wybraneKlasy, wybraniNauczyciele=None):
	if zawartośćStrony is None:
		logiKonsoli.warning("Brak treści pobranej ze strony.")
		return "", []
	if wybraniNauczyciele is None:
		wybraniNauczyciele = []
	try:
		informacjeDodatkowe = ""
		wiersze = zawartośćStrony.find_all("tr")

		# Ekstrakcja dodatkowych informacji
		komórkaDodatkowychInformacji = None
		for wiersz in wiersze:
			for komórka in wiersz.find_all("td"):
				klasy = komórka.get("class") or []
				if isinstance(klasy, str):
					klasy = [klasy]
				if "st0" in klasy:
					komórkaDodatkowychInformacji = komórka
					break
			if komórkaDodatkowychInformacji:
				break

		if komórkaDodatkowychInformacji:
			link = komórkaDodatkowychInformacji.find("a")
			if link and link.get("href"):
				tekstLinku = link.get_text(strip=True)
				urlLinku = link["href"]
				tekstDodatkowychInformacji = komórkaDodatkowychInformacji.get_text(separator="\n", strip=True).replace(tekstLinku, "").strip()
				informacjeDodatkowe = f"{tekstDodatkowychInformacji}\n[{tekstLinku}]({urlLinku})"
			else:
				informacjeDodatkowe = komórkaDodatkowychInformacji.get_text(separator="\n", strip=True)

		aktualnyNauczyciel = None
		zgrupowane = defaultdict(list)

		for wiersz in wiersze:
			komórki = wiersz.find_all("td")

			if len(komórki) == 1:
				aktualnyNauczyciel = komórki[0].get_text(separator="\n", strip=True)
				continue

			if komórki and (komórki[0].get("class") or []):
				klasyPierwszejKomórkiWiersza = komórki[0].get("class")
				if isinstance(klasyPierwszejKomórkiWiersza, str):
					klasyPierwszejKomórkiWiersza = [klasyPierwszejKomórkiWiersza]
				if "st0" in klasyPierwszejKomórkiWiersza:
					continue

			if len(komórki) >= 4:
				teksty = [komórka.get_text(strip=True) for komórka in komórki[:4]]
				lekcja, opis, zastępca, uwagi = teksty
				pola = [lekcja, opis, zastępca, uwagi]
				etykiety = ["Lekcja", "Opis", "Zastępca", "Uwagi"]

				def wyodrębnijPrzydatne(wartość, etykieta):
					return bool(wartość and wartość.lower() != etykieta.lower())

				if not any(wyodrębnijPrzydatne(wartość, etykieta) for wartość, etykieta in zip(pola, etykiety)):
					continue

				wierszeWpisówZastępstw = []
				for wartość, etykieta in zip(pola, etykiety):
					if wyodrębnijPrzydatne(wartość, etykieta):
						wierszeWpisówZastępstw.append(f"**{etykieta}:** {wartość}")
					else:
						wierszeWpisówZastępstw.append(f"**{etykieta}:** Brak")

				tekstWpisówZastępstw = "\n".join(wierszeWpisówZastępstw).strip()
				if not tekstWpisówZastępstw:
					continue

				komórkiWiersza = [lekcja, opis, zastępca, uwagi]
				dopasowaneDoKlasy = dopasujDoKlasy(komórkiWiersza, wybraneKlasy)
				wyodrębnieniNauczyciele = wyodrębnijNauczycieli(aktualnyNauczyciel, zastępca)
				dopasowaneDoNauczyciela = dopasujNauczyciela(wyodrębnieniNauczyciele, wybraniNauczyciele)

				if (wybraneKlasy or wybraniNauczyciele) and (dopasowaneDoKlasy or dopasowaneDoNauczyciela):
					kluczNauczyciela = aktualnyNauczyciel or ", ".join(wyodrębnieniNauczyciele) or "Ogólne"
					zgrupowane[kluczNauczyciela].append(tekstWpisówZastępstw)

		wpisyZastępstw = [(nauczyciel, zgrupowane[nauczyciel]) for nauczyciel in zgrupowane if zgrupowane[nauczyciel]]
		logiKonsoli.debug(f"Wyodrębniono {len(wpisyZastępstw)} wpis(ów).")
		return informacjeDodatkowe, wpisyZastępstw

	except Exception as e:
		logiKonsoli.exception(f"Wystąpił błąd podczas przetwarzania HTML. Więcej informacji: {e}")
		return "", []

# Obsługa plików danych
folderDanych = Path("Resources")
folderDanych.mkdir(exist_ok=True)

async def zarządzajPlikiemDanych(identyfikatorSerwera, dane=None):
	ścieżkaPliku = folderDanych / f"{identyfikatorSerwera}.json"
	tmp = ścieżkaPliku.with_suffix(".json.tmp")

	try:
		if dane is not None:
			def zapisz():
				with open(tmp, "w", encoding="utf-8") as plik:
					json.dump(dane, plik, ensure_ascii=False, indent=4)
				os.replace(str(tmp), str(ścieżkaPliku))
			await asyncio.to_thread(zapisz)
			return True

		def odczytaj():
			return ścieżkaPliku.exists()
		if await asyncio.to_thread(odczytaj):
			try:
				def wczytaj():
					return json.loads(ścieżkaPliku.read_text(encoding="utf-8"))
				return await asyncio.to_thread(wczytaj)
			except (json.JSONDecodeError, UnicodeDecodeError) as e:
				logiKonsoli.exception(f"Wystąpił błąd podczas wczytywania pliku. Więcej informacji: {e}")
				uszkodzony = ścieżkaPliku.with_suffix(".json.bad")
				try:
					await asyncio.to_thread(os.replace, str(ścieżkaPliku), str(uszkodzony))
					logiKonsoli.exception(f"Uszkodzony plik danych przeniesiony do: {uszkodzony}. Została wczytana pusta zawartość.")
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
				logiKonsoli.exception(f"Nie udało się usunąć pliku tymczasowego: {tmp}. Więcej informacji: {e}")
		return {}

# Sprawdzanie aktualizacji
async def sprawdźAktualizacje():
	await bot.wait_until_ready()
	while not bot.is_closed():
		url = konfiguracja.get("url")
		zawartośćStrony = await pobierzZawartośćWitryny(url)
		if zawartośćStrony is None:
			logiKonsoli.warning("Nie udało się pobrać zawartości strony. Pomijanie aktualizacji.")
		else:
			async with blokadaKonfiguracji:
				serwery = list((konfiguracja.get("serwery", {}) or {}).keys())
			zadania = [sprawdźSerwer(int(identyfikatorSerwera), zawartośćStrony) for identyfikatorSerwera in serwery]
			await asyncio.gather(*zadania, return_exceptions=True)
		await asyncio.sleep(300)

async def sprawdźSerwer(identyfikatorSerwera, zawartośćStrony):
	async with blokadaKonfiguracji:
		konfiguracjaSerwera = (konfiguracja.get("serwery", {}) or {}).get(str(identyfikatorSerwera), {}).copy()
	identyfikatorKanału = konfiguracjaSerwera.get("identyfikator-kanalu")

	if not identyfikatorKanału:
		logiKonsoli.warning(f"Nie ustawiono ID kanału dla serwera o ID {identyfikatorSerwera}.")
		return

	try:
		kanał = bot.get_channel(int(identyfikatorKanału))
	except (TypeError, ValueError):
		logiKonsoli.warning(f"Nieprawidłowy identyfikator kanału '{identyfikatorKanału}' dla serwera o ID {identyfikatorSerwera}.")
		return

	if not kanał:
		logiKonsoli.warning(f"Nie znaleziono kanału z ID {identyfikatorKanału} dla serwera o ID {identyfikatorSerwera}.")
		return

	logiKonsoli.debug(f"Sprawdzanie aktualizacji dla serwera o ID {identyfikatorSerwera}.")
	try:
		wybraneKlasy = konfiguracjaSerwera.get("wybrane-klasy", [])
		wybraniNauczyciele = konfiguracjaSerwera.get("wybrani-nauczyciele", [])
		informacjeDodatkowe, aktualneWpisyZastępstw = wyodrębnijDane(zawartośćStrony, wybraneKlasy, wybraniNauczyciele)

		hashAktualnychInformacjiDodatkowych = obliczHash(informacjeDodatkowe)
		hashAktualnychWpisówZastępstw = obliczHash(aktualneWpisyZastępstw)

		poprzednieDane = await zarządzajPlikiemDanych(identyfikatorSerwera)
		if not isinstance(poprzednieDane, dict):
			poprzednieDane = {}
		hashPoprzednichInformacjiDodatkowych = poprzednieDane.get("hash-informacji-dodatkowych", "")
		hashPoprzednichWpisówZastępstw = poprzednieDane.get("hash-wpisow-zastepstw", "")

		if hashAktualnychInformacjiDodatkowych != hashPoprzednichInformacjiDodatkowych or hashAktualnychWpisówZastępstw != hashPoprzednichWpisówZastępstw:
			if hashAktualnychInformacjiDodatkowych != hashPoprzednichInformacjiDodatkowych and hashAktualnychWpisówZastępstw == hashPoprzednichWpisówZastępstw:
				logiKonsoli.info(f"Treść informacji dodatkowych uległa zmianie dla serwera o ID {identyfikatorSerwera}. Wysyłam nowe aktualizacje.")
			else:
				logiKonsoli.info(f"Treść zastępstw uległa zmianie dla dla serwera o ID {identyfikatorSerwera}.")
			try:
				aktualnyCzas = datetime.now(pytz.timezone("Europe/Warsaw")).strftime("%d-%m-%Y %H:%M:%S")
				if hashAktualnychInformacjiDodatkowych != hashPoprzednichInformacjiDodatkowych and hashAktualnychWpisówZastępstw == hashPoprzednichWpisówZastępstw:
					await wyślijAktualizacje(kanał, informacjeDodatkowe, None, aktualnyCzas)
				elif hashAktualnychInformacjiDodatkowych == hashPoprzednichInformacjiDodatkowych and hashAktualnychWpisówZastępstw != hashPoprzednichWpisówZastępstw:
					await wyślijAktualizacje(kanał, informacjeDodatkowe, aktualneWpisyZastępstw, aktualnyCzas)
				else:
					await wyślijAktualizacje(kanał, informacjeDodatkowe, aktualneWpisyZastępstw, aktualnyCzas)

				noweDane = {"hash-informacji-dodatkowych": hashAktualnychInformacjiDodatkowych, "hash-wpisow-zastepstw": hashAktualnychWpisówZastępstw}

				await zarządzajPlikiemDanych(identyfikatorSerwera, noweDane)
			except discord.DiscordException as e:
				logiKonsoli.exception(f"Nie udało się wysłać wszystkich wiadomości dla serwera o ID {identyfikatorSerwera}, hash nie zostanie zaktualizowany. Więcej informacji: {e}")
		else:
			logiKonsoli.debug(f"Treść się nie zmieniła dla serwera o ID {identyfikatorSerwera}. Brak nowych aktualizacji.")
	except Exception as e:
		logiKonsoli.exception(f"Wystąpił błąd podczas przetwarzania aktualizacji dla serwera o ID {identyfikatorSerwera}. Więcej informacji: {e}")

# Wysyłanie aktualizacji zastępstw
async def wyślijAktualizacje(kanał, informacjeDodatkowe, aktualneWpisyZastępstw, aktualnyCzas):
	opisTylkoDlaInformacjiDodatkowych = f"**Informacje dodatkowe zastępstw:**\n{informacjeDodatkowe}\n\n**Informacja o tej wiadomości:**\nW tej wiadomości znajdują się informacje dodatkowe, które zostały umieszczone przed zastępstwami. Nie znaleziono dla Ciebie żadnych zastępstw pasujących do filtru, więc nie dostaniesz powiadomienia o aktualizacji."
	opisDlaInformacjiDodatkowych = f"**Informacje dodatkowe zastępstw:**\n{informacjeDodatkowe}\n\n**Informacja o tej wiadomości:**\nW tej wiadomości znajdują się informacje dodatkowe, które zostały umieszczone przed zastępstwami. Wszystkie zastępstwa znajdują się pod tą wiadomością."

	try:
		ostatniaWiadomość = None
		if informacjeDodatkowe and not aktualneWpisyZastępstw:
			embed = discord.Embed(
				title="**Zastępstwa zostały zaktualizowane!**",
				description=opisTylkoDlaInformacjiDodatkowych,
				color=discord.Color(0xca4449)
			)
			embed.set_footer(text=f"Czas aktualizacji: {aktualnyCzas}\nStworzone z ❤️ przez Kacpra Górkę!")
			await kanał.send(embed=embed)

		elif (informacjeDodatkowe and aktualneWpisyZastępstw) or (aktualneWpisyZastępstw):
			if kanał.permissions_for(kanał.guild.me).mention_everyone:
				wyślijPing = await kanał.send("@everyone Zastępstwa zostały zaktualizowane!", allowed_mentions=discord.AllowedMentions(everyone=True))
				await asyncio.sleep(5)
				try:
					await wyślijPing.delete()
				except Exception:
					pass
			else:
				logiKonsoli.warning("Brak pozwolenia na @everyone. Ping został pominięty.")

			embed = discord.Embed(
				title="**Zastępstwa zostały zaktualizowane!**",
				description=opisDlaInformacjiDodatkowych,
				color=discord.Color(0xca4449)
			)
			embed.set_footer(text=f"Czas aktualizacji: {aktualnyCzas}\nStworzone z ❤️ przez Kacpra Górkę!")
			await kanał.send(embed=embed)

			for tytuł, wpisyZastępstw in aktualneWpisyZastępstw:
				embed = discord.Embed(
					title=f"**{tytuł}**",
					description="\n\n".join(wpisyZastępstw),
					color=discord.Color(0xca4449)
				)
				embed.set_footer(text="Każdy nauczyciel, za którego wpisane są zastępstwa pasujące do Twojego filtru, zostanie załączany w oddzielnej wiadomości.")
				ostatniaWiadomość = await kanał.send(embed=embed)

		if ostatniaWiadomość:
			await ostatniaWiadomość.add_reaction("❤️")
	except discord.DiscordException as e:
		logiKonsoli.exception(f"Wystąpił błąd podczas wysyłania wiadomości. Więcej informacji: {e}")
	except Exception as e:
		logiKonsoli.exception(f"Wystąpił niespodziewany błąd podczas wysyłania wiadomości. Więcej informacji: {e}")

# Usuwanie serwera z konfiguracji po wyjściu bota z serwera
@bot.event
async def on_guild_remove(guild):
	await usuńSerwerZKonfiguracji(guild.id)

# Wysyłanie instrukcji konfiguracji administratorom serwera
@bot.event
async def on_guild_join(guild):
	embedWysłanyNaDm = discord.Embed(
		title="**Cześć! Nadszedł czas na skonfigurowanie bota!**",
		description=f"**Informacja wstępna**\nBot został dodany do serwera **{guild.name}**, a z racji, że jesteś jego administratorem, to dostajesz tę wiadomość. Wszystkie ważne informacje dotyczące bota oraz jego administratorów znajdziesz, używając polecenia `/informacje`.\n\n> **Jeżeli znajdziesz, doświadczysz jakiegokolwiek błędu lub chcesz zgłosić swoją propozycję, [utwórz issue](https://github.com/kacpergorka/Zastepstwa/issues). Jest to bardzo ważne dla prawidłowego funkcjonowania bota!**\n\n**Konfiguracja bota**\nKonfiguracja bota zaczyna się od utworzenia dedykowanego kanału tekstowego, na który po konfiguracji będą wysyłane zastępstwa, a następnie użycia polecenia `/skonfiguruj`, gdzie zostaniesz przeprowadzony przez wygodny i intuicyjny konfigurator. W razie jakichkolwiek pytań odsyłam również do issues na GitHubie.",
		color=discord.Color(0xca4449)
	)
	embedWysłanyNaDm.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

	embedWysłanyNaSerwer = discord.Embed(
		title="**Cześć! Nadszedł czas na skonfigurowanie bota!**",
		description=f"**Informacja wstępna**\nBot został dodany do serwera **{guild.name}**, a z racji, że żaden administrator tego serwera nie ma włączonych wiadomości prywatnych, to wiadomość ta zostaje dostarczona na serwer. Wszystkie ważne informacje dotyczące bota oraz jego administratorów znajdziesz, używając polecenia `/informacje`.\n\n> **Jeżeli znajdziesz, doświadczysz jakiegokolwiek błędu lub chcesz zgłosić swoją propozycję, [utwórz issue](https://github.com/kacpergorka/Zastepstwa/issues). Jest to bardzo ważne dla prawidłowego funkcjonowania bota!**\n\n**Konfiguracja bota**\nKonfiguracja bota zaczyna się od utworzenia dedykowanego kanału tekstowego, na który po konfiguracji będą wysyłane zastępstwa, a następnie użycia polecenia `/skonfiguruj`, gdzie zostaniesz przeprowadzony przez wygodny i intuicyjny konfigurator. W razie jakichkolwiek pytań odsyłam również do issues na GitHubie.",
		color=discord.Color(0xca4449)
	)
	embedWysłanyNaSerwer.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

	administratorzy = [członek for członek in guild.members if członek.guild_permissions.administrator and not członek.bot]
	dostarczoneWiadomości = 0

	for administrator in administratorzy:
		try:
			await administrator.send(embed=embedWysłanyNaDm)
			dostarczoneWiadomości += 1
			logiKonsoli.info(f"Wiadomość z instrukcjami została wysłana do {administrator.name}, który jest administratorem na serwerze {guild.name}.")
		except discord.Forbidden as e:
			logiKonsoli.warning(f"Nie można wysłać wiadomości do {administrator.name}, który jest administratorem na serwerze {guild.name}. Więcej informacji: {e}")
	if dostarczoneWiadomości == 0 and guild.text_channels:
		kanał = discord.utils.get(guild.text_channels, permissions__send_messages=True)
		try:
			await kanał.send(embed=embedWysłanyNaSerwer)
			logiKonsoli.info(f"Wiadomość z instrukcjami została wysłana na kanał #{kanał.name} o ID {kanał.id} na serwerze {guild.name}, ponieważ żaden administrator nie odebrał prywatnej wiadomości.")
		except discord.DiscordException as e:
				logiKonsoli.exception(f"Nie można wysłać wiadomości na serwer {guild.name}. Więcej informacji: {e}")

# /skonfiguruj
def pobierzSłownikSerwera(identyfikatorSerwera: str) -> dict:
	serwery = konfiguracja.setdefault("serwery", {})
	if identyfikatorSerwera not in serwery:
		serwery[identyfikatorSerwera] = {
			"identyfikator-kanalu": None,
			"wybrane-klasy": [],
			"wybrani-nauczyciele": []
		}
	else:
		dane = serwery[identyfikatorSerwera]
		serwery[identyfikatorSerwera] = {
			"identyfikator-kanalu": dane.get("identyfikator-kanalu"),
			"wybrane-klasy": dane.get("wybrane-klasy", []),
			"wybrani-nauczyciele": dane.get("wybrani-nauczyciele", [])
		}
	return serwery[identyfikatorSerwera]

async def zapiszKluczeSerwera(identyfikatorSerwera: str, dane: dict):
	identyfikatorSerwera = str(identyfikatorSerwera)
	lokalneDane = dict(dane)

	async with blokadaKonfiguracji:
		daneSerwera = pobierzSłownikSerwera(identyfikatorSerwera)

		for klucz in ("wybrane-klasy", "wybrani-nauczyciele"):
			if klucz in lokalneDane:
				nowy = lokalneDane.pop(klucz)
				istnieje = daneSerwera.get(klucz) or []
				if not isinstance(istnieje, list):
					istnieje = list(istnieje)

				if nowy is None:
					nowaLista = []
				elif isinstance(nowy, list):
					nowaLista = nowy
				else:
					nowaLista = [nowy]

				nowaLista = [str(element) for element in nowaLista if element is not None]
				daneSerwera[klucz] = usuńDuplikaty(istnieje + nowaLista)

		if "identyfikator-kanalu" in lokalneDane:
			daneSerwera["identyfikator-kanalu"] = lokalneDane.pop("identyfikator-kanalu")

		for klucz, wartość in lokalneDane.items():
			daneSerwera[klucz] = wartość

		snapshot = copy.deepcopy(konfiguracja)

	await zapiszKonfiguracje(snapshot)

async def wyczyśćFiltry(identyfikatorSerwera: str):
	identyfikatorSerwera = str(identyfikatorSerwera)
	async with blokadaKonfiguracji:
		daneSerwera = pobierzSłownikSerwera(identyfikatorSerwera)
		daneSerwera["identyfikator-kanalu"] = None
		daneSerwera["wybrane-klasy"] = []
		daneSerwera["wybrani-nauczyciele"] = []
		snapshot = copy.deepcopy(konfiguracja)
	await zapiszKonfiguracje(snapshot)

def kluczeNormalizacyjne(tekst: str) -> list[str]:
	tekstNormalizowany = normalizujTekst(tekst)
	brakSpacji = re.sub(r"\s+", "", tekstNormalizowany)
	return [tekstNormalizowany, brakSpacji]

def usuńDuplikaty(sekwencja):
	widziane = set()
	wynik = []
	for element in sekwencja:
		if element not in widziane:
			wynik.append(element)
			widziane.add(element)
	return wynik

def zbudujIndeks(listaDoDopasowania: list[str]):
	mapaKluczy = defaultdict(list)
	normalizowaneDoOryginalnych = defaultdict(list)
	listaNormalizowanych = []

	for element in listaDoDopasowania:
		pełnaNorma = re.sub(r"\s+", "", normalizujTekst(element))
		normalizowaneDoOryginalnych[pełnaNorma].append(element)
		listaNormalizowanych.append(pełnaNorma)
		for klucz in kluczeNormalizacyjne(element):
			mapaKluczy [klucz].append(element)

	return mapaKluczy , normalizowaneDoOryginalnych, listaNormalizowanych

def dopasujWpisyDoListy(wpisy: list[str], listaDoDopasowania: list[str], cutoff: float = 0.6):
	mapaKluczy , normalizowaneDoOryginalnych, listaNormalizowanych = zbudujIndeks(listaDoDopasowania)

	idealneDopasowania = []
	sugestie = {}
	nieZnaleziono = []

	for wpis in wpisy:
		kluczeWpisu = kluczeNormalizacyjne(wpis)
		znalezioneIdealneDopasowania = None
		for klucz in kluczeWpisu:
			if klucz in mapaKluczy :
				znalezioneIdealneDopasowania = mapaKluczy [klucz][0]
				break
		if znalezioneIdealneDopasowania:
			if znalezioneIdealneDopasowania not in idealneDopasowania:
				idealneDopasowania.append(znalezioneIdealneDopasowania)
			continue

		# Dopasowanie przybliżone
		normaWpisu = re.sub(r"\s+", "", normalizujTekst(wpis))
		normaKandydatów = difflib.get_close_matches(normaWpisu, listaNormalizowanych, n=1, cutoff=cutoff)
		if normaKandydatów:
			normaKandydata = normaKandydatów[0]
			kandydant = normalizowaneDoOryginalnych[normaKandydata][0]
			sugestie[wpis] = kandydant
		else:
			nieZnaleziono.append(wpis)

	return idealneDopasowania, sugestie, nieZnaleziono

def pobierzListęKlas() -> list[str]:
	suroweDane = konfiguracja.get("lista-klas", {})
	if isinstance(suroweDane, dict):
		return [klasa for grupy in suroweDane.values() for klasa in grupy]
	if isinstance(suroweDane, list):
		return suroweDane
	return []

class WidokPonownegoWprowadzania(discord.ui.View):
	def __init__(self, typDanych: str, listaDoDopasowania: list[str], wiadomość: discord.Message, identyfikatorKanału: str, timeout: float = 120.0):
		super().__init__(timeout=timeout)
		self.typDanych = typDanych
		self.lista = listaDoDopasowania
		self.wiadomość = wiadomość
		self.identyfikatorKanału = identyfikatorKanału

	@discord.ui.button(label="Wprowadź ponownie", style=discord.ButtonStyle.secondary)
	async def wprowadźPonownie(self, interaction: discord.Interaction, button: discord.ui.Button):
		try:
			await interaction.response.send_modal(ModalWybierania(self.typDanych, self.lista, self.wiadomość, self.identyfikatorKanału))
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd po kliknięciu przycisku 'Wprowadź ponownie' (w class WidokPonownegoWprowadzania) dla {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
			with contextlib.suppress(Exception):
				await interaction.followup.send("Wystąpił błąd podczas otwierania formularza. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)

class WidokAkceptacjiSugestii(discord.ui.View):
	def __init__(self, typDanych: str, identyfikatorSerwera: str, idealneDopasowania: list[str], sugestie: dict[str, str], listaDoDopasowania: list[str], wiadomość: discord.Message, identyfikatorKanału: str, timeout: float = 120.0):
		super().__init__(timeout=timeout)
		self.typDanych = typDanych
		self.identyfikatorSerwera = identyfikatorSerwera
		self.idealneDopasowania = idealneDopasowania[:]
		self.sugestie = sugestie.copy()
		self.lista = listaDoDopasowania
		self.wiadomość = wiadomość
		self.identyfikatorKanału = identyfikatorKanału

	@discord.ui.button(label="Akceptuj sugestie", style=discord.ButtonStyle.success)
	async def akceptujSugestie(self, interaction: discord.Interaction, button: discord.ui.Button):
		try:
			finalne = []
			for dopasowanie in self.idealneDopasowania:
				if dopasowanie not in finalne:
					finalne.append(dopasowanie)
			for sugestia in self.sugestie.values():
				if sugestia not in finalne:
					finalne.append(sugestia)
			finalne = usuńDuplikaty(finalne)

			kluczFiltru = "wybrane-klasy" if self.typDanych == "klasy" else "wybrani-nauczyciele"
			await zapiszKluczeSerwera(self.identyfikatorSerwera, {"identyfikator-kanalu": self.identyfikatorKanału, kluczFiltru: finalne})
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd po kliknięciu przycisku 'Akceptuj sugestie' dla {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
			with contextlib.suppress(Exception):
				await interaction.followup.send("Wystąpił błąd podczas akceptacji danych. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)


		konfiguracjaSerwera = pobierzSłownikSerwera(str(interaction.guild.id))

		kanał = f"<#{konfiguracjaSerwera['identyfikator-kanalu']}>" if konfiguracjaSerwera.get("identyfikator-kanalu") else "Brak"
		klasy = ", ".join(re.sub(r'(\d)\s+([A-Z])', r'\1\2', klasa) for klasa in konfiguracjaSerwera.get("wybrane-klasy", [])) or "Brak"
		nauczyciele = ", ".join(f"{nauczyciel}" for nauczyciel in konfiguracjaSerwera.get("wybrani-nauczyciele", [])) or "Brak"

		embed = discord.Embed(
			title="Zapisano wprowadzone dane",
			description="Wprowadzone dane zostały dodane do konfiguracji. Aktualna konfiguracja twojego serwera została wyświetlona poniżej.",
			color=discord.Color(0xca4449)
		)

		embed.add_field(name="Kanał tekstowy:", value=kanał)
		embed.add_field(name="Wybrane klasy:", value=klasy)
		embed.add_field(name="Wybrani nauczyciele:", value=nauczyciele)
		embed.set_footer(text="Projekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")
		await interaction.response.edit_message(embed=embed, view=None)

	@discord.ui.button(label="Wprowadź ponownie", style=discord.ButtonStyle.secondary)
	async def wprowadźPonownie(self, interaction: discord.Interaction, button: discord.ui.Button):
		try:
			await interaction.response.send_modal(ModalWybierania(self.typDanych, self.lista, self.wiadomość, self.identyfikatorKanału))
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd po kliknięciu przycisku 'Wprowadź ponownie' (w class WidokAkceptacjiSugestii) dla {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
			with contextlib.suppress(Exception):
				await interaction.followup.send("Wystąpił błąd podczas otwierania formularza. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)

class ModalWybierania(discord.ui.Modal):
	def __init__(self, typDanych: str, listaDoDopasowania: list[str], wiadomość: discord.Message, identyfikatorKanału: str):
		super().__init__(title="Wprowadź dane do formularza")
		self.typDanych = typDanych
		self.lista = listaDoDopasowania
		self.wiadomość = wiadomość
		self.identyfikatorKanału = identyfikatorKanału

		placeholder = "np. 1A, 2D, 3F" if typDanych == "klasy" else "np. A. Kowalski, W. Nowak"
		label = "Wprowadź klasy (oddzielaj przecinkami)." if typDanych == "klasy" else "Wprowadź nauczycieli (oddzielaj przecinkami)."

		self.pole = discord.ui.TextInput(
			label=label,
			style=discord.TextStyle.long,
			placeholder=placeholder,
		)
		self.add_item(self.pole)

	async def on_submit(self, interaction: discord.Interaction):
		try:
			identyfikatorSerwera = str(interaction.guild.id)
			suroweDane = self.pole.value
			wpisy = [element.strip() for element in re.split(r",|;", suroweDane) if element.strip()]

			idealneDopasowania, sugestie, nieZnaleziono = dopasujWpisyDoListy(wpisy, self.lista, cutoff=0.6)

			if nieZnaleziono:
				embed = discord.Embed(
					title="Nie znaleziono wprowadzonych danych",
					description=(
						"Nie znaleziono odpowiadających wpisów dla następujących danych:\n"
						+ "\n".join(f"- **{wprowadzoneDane}**" for wprowadzoneDane in nieZnaleziono)
						+ "\n\nProszę spróbować ponownie, naciskając przycisk **Wprowadź ponownie**."
					),
					color=discord.Color(0xca4449),
				)
				embed.set_footer(text="Projekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")
				view = WidokPonownegoWprowadzania(self.typDanych, self.lista, self.wiadomość, self.identyfikatorKanału)
				await interaction.response.defer()
				await self.wiadomość.edit(embed=embed, view=view)
				return

			if sugestie:
				opis = ""
				if idealneDopasowania:
					opis += "**Znalezione dokładne dopasowania:**\n" + ", ".join(f"**{dopasowanie}**" for dopasowanie in idealneDopasowania) + "\n\n"
				opis += "**Proponowane dopasowania:**\n"
				for orginalne, sugestia in sugestie.items():
					opis += f"- **{orginalne}**  →  **{sugestia}**\n"
				opis += "\nJeśli akceptujesz propozycje, naciśnij przycisk **Akceptuj sugestie**. Jeśli chcesz wpisać ponownie, naciśnij przycisk **Wprowadź ponownie**."

				embed = discord.Embed(
					title=f"Sugestie dopasowania wprowadzonych danych",
					description=opis,
					color=discord.Color(0xca4449),
				)
				embed.set_footer(text="Projekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")
				view = WidokAkceptacjiSugestii(self.typDanych, identyfikatorSerwera, idealneDopasowania, sugestie, self.lista, self.wiadomość, self.identyfikatorKanału)
				await interaction.response.defer()
				await self.wiadomość.edit(embed=embed, view=view)
				return

			finalne = usuńDuplikaty(idealneDopasowania)

			kluczFiltru = "wybrane-klasy" if self.typDanych == "klasy" else "wybrani-nauczyciele"
			await zapiszKluczeSerwera(identyfikatorSerwera, {"identyfikator-kanalu": self.identyfikatorKanału, kluczFiltru: finalne})

			konfiguracjaSerwera = pobierzSłownikSerwera(str(interaction.guild.id))

			kanał = f"<#{konfiguracjaSerwera['identyfikator-kanalu']}>" if konfiguracjaSerwera.get("identyfikator-kanalu") else "Brak"
			klasy = ", ".join(re.sub(r'(\d)\s+([A-Z])', r'\1\2', klasa) for klasa in konfiguracjaSerwera.get("wybrane-klasy", [])) or "Brak"
			nauczyciele = ", ".join(f"{nauczyciel}" for nauczyciel in konfiguracjaSerwera.get("wybrani-nauczyciele", [])) or "Brak"

			embed = discord.Embed(
				title="Zapisano wprowadzone dane",
				description="Wprowadzone dane zostały dodane do konfiguracji. Aktualna konfiguracja twojego serwera została wyświetlona poniżej.",
				color=discord.Color(0xca4449)
			)

			embed.add_field(name="Kanał tekstowy:", value=kanał)
			embed.add_field(name="Wybrane klasy:", value=klasy)
			embed.add_field(name="Wybrani nauczyciele:", value=nauczyciele)
			embed.set_footer(text="Projekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")

			await interaction.response.defer()
			await self.wiadomość.edit(embed=embed, view=None)
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd po kliknięciu przycisku wysyłającego dane do zapisu (on_submit) dla {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
			with contextlib.suppress(Exception):
				await interaction.response.send_message("Wystąpił błąd podczas przetwarzania danych. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)

class PrzyciskUczeń(discord.ui.Button):
	def __init__(self, identyfikatorKanału: str):
		super().__init__(label="Uczeń", style=discord.ButtonStyle.primary)
		self.identyfikatorKanału = identyfikatorKanału

	async def callback(self, interaction: discord.Interaction):
		try:
			listaKlas = pobierzListęKlas()
			await interaction.response.send_modal(ModalWybierania("klasy", listaKlas, interaction.message, self.identyfikatorKanału))
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd po kliknięciu przycisku 'Uczeń' dla {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
			with contextlib.suppress(Exception):
				await interaction.followup.send("Wystąpił błąd podczas otwierania formularza. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)

class PrzyciskNauczyciel(discord.ui.Button):
	def __init__(self, identyfikatorKanału: str):
		super().__init__(label="Nauczyciel", style=discord.ButtonStyle.primary)
		self.identyfikatorKanału = identyfikatorKanału

	async def callback(self, interaction: discord.Interaction):
		try:
			listaNauczycieli = konfiguracja.get("lista-nauczycieli", [])
			await interaction.response.send_modal(ModalWybierania("nauczyciele", listaNauczycieli, interaction.message, self.identyfikatorKanału))
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd po kliknięciu przycisku 'Nauczyciel' dla {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
			with contextlib.suppress(Exception):
				await interaction.followup.send("Wystąpił błąd podczas otwierania formularza. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)

class PrzyciskWyczyśćFiltry(discord.ui.Button):
	def __init__(self):
		super().__init__(label="Wyczyść filtry", style=discord.ButtonStyle.danger)

	async def callback(self, interaction: discord.Interaction):
		try:
			identyfikatorSerwera = str(interaction.guild.id)
			await wyczyśćFiltry(identyfikatorSerwera)

			embed = discord.Embed(
				title="Wyczyszczono konfigurację serwera",
				description="Twój serwer nie będzie dostawał powiadomień z nowymi zastępstwami do czasu ponownej ich konfiguracji.",
				color=discord.Color(0xca4449),
			)
			embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")
			await interaction.response.edit_message(embed=embed, view=None)
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd po kliknięciu przycisku 'Wyczyść filtry' dla {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
			with contextlib.suppress(Exception):
				await interaction.followup.send("Wystąpił błąd podczas przetwarzania danych. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)

class widokGłówny(discord.ui.View):
	def __init__(self, identyfikatorKanału: str):
		super().__init__()
		self.add_item(PrzyciskUczeń(identyfikatorKanału))
		self.add_item(PrzyciskNauczyciel(identyfikatorKanału))
		self.add_item(PrzyciskWyczyśćFiltry())

@bot.tree.command(name="skonfiguruj", description="Skonfiguruj bota, ustawiając kanał tekstowy i filtrację zastępstw.")
@app_commands.guild_only()
@app_commands.describe(kanał="Kanał tekstowy, na który będą wysyłane powiadomienia z zastępstwami.")
async def skonfiguruj(interaction: discord.Interaction, kanał: discord.TextChannel):
	try:
		if not interaction.user.guild_permissions.administrator:
			embed = discord.Embed(
				title="**Polecenie nie zostało wykonane!**",
				description="Nie masz uprawnień do używania tej komendy. Może jej użyć wyłącznie administrator serwera.",
				color=discord.Color(0xca4449),
			)
			embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")
			await interaction.response.send_message(embed=embed, ephemeral=True)
			logujPolecenia(interaction, success=False, error_message="Brak uprawnień.")
			return

		view = widokGłówny(identyfikatorKanału=str(kanał.id))
		embed = discord.Embed(
			title="**Skonfiguruj filtrację zastępstw**",
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

# /informacje
@bot.tree.command(name="informacje", description="Wyświetl najważniejsze informacje dotyczące bota i ich administratorów.")
async def informacje(interaction: discord.Interaction):
	try:
		embed = discord.Embed(
			title="**Informacje dotyczące bota**",
			description="Otwartoźródłowe oprogramowanie informujące o aktualizacji zastępstw. W celu skontaktowania się z administratorem bot, kliknij jednego z poniżej widniejących. Zostaniesz przeniesiony/a do zewnętrznej witryny internetowej.",
			color=discord.Color(0xca4449)
		)
		wersja = konfiguracja.get("wersja")
		embed.add_field(name="Wersja bota:", value=wersja)
		embed.add_field(name="Repozytorium GitHuba:", value=("[kacpergorka/zastepstwa](https://github.com/kacpergorka/Zastepstwa)"))
		embed.add_field(name="Administratorzy bota:", value="[Kacper Górka](https://kacpergorka.com/)")
		if bot.pobierzLiczbęSerwerów() == 1:
			embed.add_field(name="Liczba serwerów:", value=(f"Bot znajduje się na **{bot.pobierzLiczbęSerwerów()}** serwerze."))
		else:
			embed.add_field(name="Liczba serwerów:", value=(f"Bot znajduje się na **{bot.pobierzLiczbęSerwerów()}** serwerach."))
		embed.add_field(name="Bot pracuje bez przerwy przez:", value=bot.pobierzCzasDziałania())
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

# Wyłączanie bota
def wyłączBota(*_):
	logiKonsoli.info("Przechwycono Ctrl + C. Zatrzymywanie bota...")
	bot.loop.call_soon_threadsafe(lambda: asyncio.create_task(bot.close()))

signal.signal(signal.SIGINT, wyłączBota)
if hasattr(signal, "SIGTERM"):
	signal.signal(signal.SIGTERM, wyłączBota)
if hasattr(signal, "SIGBREAK"):
	signal.signal(signal.SIGBREAK, wyłączBota)

# Uruchomienie bota
if not konfiguracja.get("token"):
	logiKonsoli.critical("Brak tokena bota. Ustaw token w pliku konfiguracyjnym.")
	sys.exit(1)
try:
	bot.run(konfiguracja.get("token"))
except discord.LoginFailure as e:
	logiKonsoli.critical(f"Nieprawidłowy token bota. Więcej informacji: {e}")
	raise
except Exception as e:
	logiKonsoli.exception(f"Wystąpił krytyczny błąd uruchomienia bota. Więcej informacji: {e}")