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

# Standardowe biblioteki Pythona
import asyncio, contextlib, copy, difflib, hashlib, json, logging, os, re, signal, sys, unicodedata
from collections import defaultdict
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Zewnętrzne biblioteki
import aiohttp, discord, pytz
from bs4 import BeautifulSoup, NavigableString

# Wewnętrzne importy
from assets.ascii import ascii

# Zainicjowanie klasy klienta discorda
class Zastępstwa(discord.Client):
	def __init__(self, *, intents: discord.Intents):
		super().__init__(intents=intents)
		self.tree = discord.app_commands.CommandTree(self)

	async def setup_hook(self):
		try:
			wersja = konfiguracja.get("wersja")
			self.połączenieHTTP = aiohttp.ClientSession(
				timeout=aiohttp.ClientTimeout(total=10),
				headers={"User-Agent": f"Zastepstwa/{wersja} (https://github.com/kacpergorka/zastepstwa)"}
			)
		except Exception as e:
			logiKonsoli.critical(f"Nie udało się utworzyć sesji HTTP. Więcej informacji: {e}")
			raise

	async def close(self):
		for atrybut in ("aktualizacje", "koniecRoku"):
			zadanie = getattr(self, atrybut, None)
			if zadanie and not zadanie.done():
				try:
					zadanie.cancel()
				except Exception as e:
					logiKonsoli.exception(f"Wystąpił błąd podczas zatrzymywania zadania ({atrybut}). Więcej informacji: {e}")
		for atrybut in ("aktualizacje", "koniecRoku"):
			zadanie = getattr(self, atrybut, None)
			if zadanie:
				with contextlib.suppress(asyncio.CancelledError, Exception):
					await zadanie
		if getattr(self, "połączenieHTTP", None):
			try:
				await self.połączenieHTTP.close()
			except Exception as e:
				logiKonsoli.exception(f"Wystąpił błąd podczas zamykania sesji HTTP. Więcej informacji: {e}")
		await super().close()

	async def on_ready(self):
		try:
			self.zaczynaCzas = datetime.now()
			logiKonsoli.info(ascii)
			logiKonsoli.info(f"Zalogowano jako {self.user.name} (ID: {self.user.id}). Czekaj...")
			await self.tree.sync()
			await self.change_presence(
				status=discord.Status.online,
				activity=discord.CustomActivity(name="kacpergorka.com/zastepstwa")
			)
			if not getattr(self, "aktualizacje", None) or self.aktualizacje.done():
				self.aktualizacje = asyncio.create_task(sprawdźAktualizacje())
			else:
				logiKonsoli.info("Zadanie sprawdzające aktualizacje zastępstw jest już uruchomione. Próba ponownego jego uruchomienia została unieważniona.")

			if not getattr(self, "koniecRoku", None) or self.koniecRoku.done():
				self.koniecRoku = asyncio.create_task(sprawdźKoniecRoku())
			else:
				logiKonsoli.info("Zadanie sprawdzające zakończenie roku szkolnego jest już uruchomione. Próba ponownego jego uruchomienia została unieważniona.")
			logiKonsoli.info(f"Wszystkie zadania zostały poprawnie uruchomione. Enjoy!")
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd podczas wywoływania funkcji on_ready. Więcej informacji: {e}")

	def pobierzLiczbęSerwerów(self):
		return len(self.guilds)

	def pobierzCzasDziałania(self):
		czasDziałania = datetime.now() - self.zaczynaCzas
		dni, reszta = divmod(czasDziałania.total_seconds(), 86400)
		godziny, reszta = divmod(reszta, 3600)
		minuty, sekundy = divmod(reszta, 60)
		return f"**{int(dni)}** dni, **{int(godziny)}** godz., **{int(minuty)}** min. i **{int(sekundy)}** sek."

intents = discord.Intents.default()
bot = Zastępstwa(intents=intents)

# Formatowanie strefy czasowej
class FormatStrefyCzasowej(logging.Formatter):
	def formatTime(self, record, datefmt=None):
		daneCzasu = datetime.fromtimestamp(record.created, pytz.timezone("Europe/Warsaw"))
		if datefmt:
			return daneCzasu.strftime(datefmt)
		return daneCzasu.strftime("%d-%m-%Y %H:%M:%S")

# Konfigurowanie logowania
def skonfigurujLogi():
	folderLogów = Path("logs")
	folderLogów.mkdir(exist_ok=True)

	logiKonsoli = logging.getLogger("discord")
	logiKonsoli.setLevel(logging.INFO)
	logiPoleceń = logging.getLogger("discord.commands")
	logiPoleceń.setLevel(logging.DEBUG)

	ścieżkaLogów = folderLogów / "console.log"
	obsługaLogów = RotatingFileHandler(
		filename=ścieżkaLogów,
		encoding="utf-8",
		maxBytes=32 * 1024 * 1024,
		backupCount=30
	)
	formatter = FormatStrefyCzasowej("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
	obsługaLogów.setFormatter(formatter)

	logiKonsoli.addHandler(obsługaLogów)
	logiPoleceń.addHandler(obsługaLogów)
	logiPoleceń.propagate = False
	return logiKonsoli, logiPoleceń

logiKonsoli, logiPoleceń = skonfigurujLogi()

# Logowanie poleceń
def logujPolecenia(interaction: discord.Interaction, success: bool, error_message: str = None):
	status = "pomyślnie" if success else "niepomyślnie"
	informacjaBłędu = f" ({error_message})" if error_message else ""
	opcje = (interaction.data or {}).get("options", []) if interaction and getattr(interaction, "data", None) else []
	użyteArgumenty = "Użyte argumenty: " + ", ".join(f"{opcja.get("name")} ({opcja.get("value")})" for opcja in opcje) + ". " if opcje else ""
	try:
		if getattr(interaction, "guild", None):
			miejsce = (f"na serwerze „{interaction.guild.name}” (ID: {interaction.guild.id}) na kanale tekstowym „#{getattr(interaction.channel, "name", "N/A")}” (ID: {getattr(interaction.channel, "id", "N/A")}). ")
		else:
			miejsce = "w wiadomości prywatnej (DM). "
	except Exception:
		miejsce = ""

	nazwaPolecenia = getattr(getattr(interaction, "command", None), "name", getattr(interaction, "command_name", "unknown"))
	użytkownik = f"{getattr(interaction, "user", "Unknown")}"
	identyfikatorUżytkownika = getattr(getattr(interaction, "user", None), "id", "Unknown")
	wiadomośćLogu = (
		f"Użytkownik: {użytkownik} (ID: {identyfikatorUżytkownika}) "
		f"wywołał polecenie „{nazwaPolecenia}” "
		f"{miejsce}"
		f"{użyteArgumenty}"
		f"Polecenie wykonane {status}.{informacjaBłędu}"
	)
	logiPoleceń.info(wiadomośćLogu)

# Wczytywanie pliku konfiguracyjnego
ścieżkaKonfiguracji = Path("config.json")
blokadaKonfiguracji = asyncio.Lock()

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
		"wersja": "2.2.5.0-stable",
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

# Zarządzanie plikami danych serwerów
folderDanych = Path("resources")
folderDanych.mkdir(exist_ok=True)
blokadaPlikuNaSerwer = defaultdict(lambda: asyncio.Lock())

async def zarządzajPlikiemDanych(identyfikatorSerwera, dane=None):
	identyfikatorSerwera = str(identyfikatorSerwera)
	ścieżkaPliku = folderDanych / f"{identyfikatorSerwera}.json"
	tmp = ścieżkaPliku.with_suffix(".json.tmp")
	async with blokadaPlikuNaSerwer[identyfikatorSerwera]:
		try:
			if dane is not None:
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

# Usuwanie konfiguracji serwera z pliku konfiguracyjnego
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

# Obliczanie sumy kontrolnej
def obliczSumęKontrolną(dane):
	if isinstance(dane, str):
		wejście = dane.strip()
	elif isinstance(dane, list):
		części = []
		for tytuł, wpisy in sorted(dane, key=lambda pozycja: pozycja[0]):
			części.append(tytuł.strip())
			for wpis in sorted(wpisy):
				części.append(wpis.strip())
		wejście = "\n".join(części)
	else:
		wejście = str(dane)
	return hashlib.sha256(wejście.encode("utf-8")).hexdigest()

# Pobieranie zawartości strony internetowej
async def pobierzZawartośćStrony(url, kodowanie=None):
	logiKonsoli.debug(f"Pobieranie zawartości strony ({url}).")
	try:
		async with bot.połączenieHTTP.get(url) as odpowiedź:
			odpowiedź.raise_for_status()
			tekst = await odpowiedź.text(encoding=kodowanie, errors="ignore")
			pętla = asyncio.get_event_loop()
			return await pętla.run_in_executor(None, lambda: BeautifulSoup(tekst, "html.parser"))
	except asyncio.TimeoutError:
		logiKonsoli.warning(f"Przekroczono czas oczekiwania na połączenie ({url}).")
	except aiohttp.ClientError as e:
		logiKonsoli.exception(f"Wystąpił błąd klienta HTTP podczas pobierania strony. Więcej informacji: {e}")
	except Exception as e:
		logiKonsoli.exception(f"Wystąpił błąd podczas pobierania strony. Więcej informacji: {e}")
	return None

# Liczenie liczby zastępstw
def policzZastępstwa(aktualneWpisyZastępstw) -> int:
	if not aktualneWpisyZastępstw:
		return 0
	try:
		return sum(len(wpisy) for _, wpisy in aktualneWpisyZastępstw)
	except Exception:
		return 0

# Odmienianie słowa „zastępstwo” w zależności od liczby zastępstw
def odmieńZastępstwa(licznik: int) -> str:
	if abs(licznik) == 1:
		return "zastępstwo"
	if 11 <= abs(licznik) % 100 <= 14:
		return "zastępstw"
	if abs(licznik) % 10 in (2, 3, 4):
		return "zastępstwa"
	return "zastępstw"

# Normalizacja tekstu
def normalizujTekst(tekst: str) -> str:
	if not tekst or not isinstance(tekst, str):
		return ""
	tekst = tekst.strip()
	tekst = unicodedata.normalize("NFKD", tekst)
	tekst = "".join(ch for ch in tekst if not unicodedata.combining(ch))
	tekst = tekst.replace(".", " ")
	tekst = re.sub(r"\s+", " ", tekst)
	return tekst.lower()

# Tworzenie zestawu kluczy dopasowań
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

# Wyciąganie nazwisk nauczycieli z nagłówka i treści komórki
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

# Dopasowywanie wyodrębnionych nauczycieli do listy filtrowanych
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

# Dopasowywanie wyodrębnionych z wiersza klas do listy filtrowanych
def dopasujDoKlasy(komórkiWiersza: list, wybraneKlasy: list) -> bool:
	if not wybraneKlasy:
		return False

	komórki = komórkiWiersza[:]
	if len(komórki) > 1 and komórki[1]:
		komórki[1] = komórki[1].split("-", 1)[0]

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

# Wyodrębnienie danych z pobranego pliku strony internetowej
def wyodrębnijDane(zawartośćStrony, wybraneKlasy, wybraniNauczyciele=None, listaKlas=None):
	def bezpiecznyTekst(węzeł):
		if węzeł is None:
			return ""

		tmp = BeautifulSoup(str(węzeł), "html.parser")
		try:
			for br in tmp.find_all("br"):
				br.replace_with(NavigableString("\n"))
			for tag in tmp.find_all(["nobr", "blink", "span", "font", "b", "i", "u"]):
				tag.unwrap()
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd podczas rozpakowywania tagów. Więcej informacji: {e}")

		# Normalizacja tekstu
		tekst = tmp.get_text(separator="")
		tekst = tekst.replace("\r\n", "\n").replace("\r", "\n")
		tekst = tekst.replace("\xa0", " ")
		tekst = re.sub(r"[ \t]*\n[ \t]*", "\n", tekst)
		tekst = re.sub(r"[ \t]{2,}", " ", tekst)
		tekst = re.sub(r"\n{3,}", "\n\n", tekst)
		return tekst.strip("\n ")

	def czyKomórkaMaKlasy(komórka, nazwy):
		klasy = komórka.get("class") or []
		if isinstance(klasy, str):
			klasy = [klasy]
		return any(klasa in nazwy for klasa in klasy)

	def czySąZastępstwa(wszystkieWiersze):
		nagłówki = {"lekcja", "opis", "zastępca", "uwagi"}
		for wiersz in wszystkieWiersze:
			komórki = wiersz.find_all("td")
			if len(komórki) >= 4:
				teksty = [bezpiecznyTekst(td).lower() for td in komórki[:4]]
				jestPuste = all(tekst == "" or tekst == "&nbsp;" for tekst in teksty)
				jestNagłówek = set(tekst.strip().lower() for tekst in teksty) <= nagłówki
				if not jestPuste and not jestNagłówek:
					return True
		return False

	if zawartośćStrony is None:
		logiKonsoli.warning("Brak treści pobranej ze strony. Zwracanie pustej zawartości.")
		return "", []
	if wybraniNauczyciele is None:
		wybraniNauczyciele = []
	try:
		informacjeDodatkowe = ""
		wiersze = zawartośćStrony.find_all("tr")

		komórkaSt0 = None
		for wiersz in wiersze:
			for komórka in wiersz.find_all("td"):
				if czyKomórkaMaKlasy(komórka, {"st0"}):
					komórkaSt0 = komórka
					break
			if komórkaSt0:
				break
		if komórkaSt0:
			tekstSt0 = komórkaSt0.get_text(separator="\n", strip=True)
			tekstSt0 = re.sub(r"[ \t]+", " ", tekstSt0)
			tekstSt0 = re.sub(r"\n{3,}", "\n\n", tekstSt0)
			if tekstSt0:
				link = komórkaSt0.find("a")
				if link and link.get("href"):
					tekstLinku = bezpiecznyTekst(link)
					urlLinku = link.get("href")
					bezTekstuSt0 = tekstSt0.replace(tekstLinku, "").strip()
					informacjeDodatkowe = f"{bezTekstuSt0}\n[{tekstLinku}]({urlLinku})".strip()
				else:
					informacjeDodatkowe = tekstSt0

		aktualnyNauczyciel = None
		zgrupowane = defaultdict(list)
		for wiersz in wiersze:
			komórki = wiersz.find_all("td")
			if len(komórki) == 1:
				aktualnyNauczyciel = bezpiecznyTekst(komórki[0])
				continue
			if komórki and (komórki[0].get("class") or []):
				if czyKomórkaMaKlasy(komórki[0], {"st0"}):
					continue
			if len(komórki) >= 4:
				teksty = [bezpiecznyTekst(komórka) for komórka in komórki[:4]]
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
				zastępstwoBezKlasy = False
				if wybraneKlasy:
					pełnyTekst = " ".join(komórkiWiersza)
					if listaKlas:
						znalezionoKlasy = any(re.search(r"\b" + re.escape(normalizujTekst(klasa)) + r"\b", normalizujTekst(pełnyTekst)) for klasa in listaKlas)
						zastępstwoBezKlasy = not znalezionoKlasy
					else:
						if not re.search(r"\d", pełnyTekst):
							zastępstwoBezKlasy = True
				if (wybraneKlasy or wybraniNauczyciele) and (dopasowaneDoKlasy or dopasowaneDoNauczyciela or zastępstwoBezKlasy):
					domyślnyTytuł = aktualnyNauczyciel or ", ".join(wyodrębnieniNauczyciele) or "Ogólne"
					kluczNauczyciela = f"Zastępstwa z nieprzypisanymi klasami!\n{domyślnyTytuł}" if zastępstwoBezKlasy else domyślnyTytuł
					zgrupowane[kluczNauczyciela].append(tekstWpisówZastępstw)

		wpisyZastępstw = [(nauczyciel, zgrupowane[nauczyciel]) for nauczyciel in zgrupowane if zgrupowane[nauczyciel]]
		wpisyZastępstw.sort(key=lambda x: 0 if "Zastępstwa z nieprzypisanymi klasami!" in x[0] else 1)

		if not informacjeDodatkowe:
			maZastępstwa = czySąZastępstwa(wiersze)
			if not maZastępstwa:
				treściSt1 = []
				for wiersz in wiersze:
					for komórka in wiersz.find_all("td"):
						if czyKomórkaMaKlasy(komórka, {"st1"}):
							tekst = bezpiecznyTekst(komórka)
							if tekst and tekst != "&nbsp;":
								treściSt1.append(tekst)
				informacjeDodatkowe = "\n".join(treściSt1).strip()

		if len(wpisyZastępstw) == 0 or len(wpisyZastępstw) > 4:
			logiKonsoli.debug(f"Wyodrębniono {len(wpisyZastępstw)} wpisów.")
		elif len(wpisyZastępstw) == 1:
			logiKonsoli.debug(f"Wyodrębniono {len(wpisyZastępstw)} wpis.")
		elif 2 <= len(wpisyZastępstw) <= 4:
			logiKonsoli.debug(f"Wyodrębniono {len(wpisyZastępstw)} wpisy.")
		return informacjeDodatkowe, wpisyZastępstw
	except Exception as e:
		logiKonsoli.exception(f"Wystąpił błąd podczas przetwarzania HTML. Więcej informacji: {e}")
		return "", []

# Sprawdzanie aktualizacji zastępstw
async def sprawdźAktualizacje():
	await bot.wait_until_ready()
	while not bot.is_closed():
		async with blokadaKonfiguracji:
			szkoły = dict((konfiguracja.get("szkoły") or {}).copy())
			serwery = dict((konfiguracja.get("serwery") or {}).copy())
		if not szkoły:
			logiKonsoli.warning("Brak zdefiniowanych szkół w pliku konfiguracyjnym. Uzupełnij brakujące dane i spróbuj ponownie.")
		else:
			for identyfikatorSzkoły, daneSzkoły in szkoły.items():
				url = (daneSzkoły or {}).get("url")
				if not url:
					logiKonsoli.warning(f"Nie ustawiono URL dla szkoły o ID {identyfikatorSzkoły} w pliku konfiguracyjnym. Uzupełnij brakujące dane i spróbuj ponownie.")
					continue

				zawartośćStrony = await pobierzZawartośćStrony(url, kodowanie=(daneSzkoły or {}).get("kodowanie"))
				if zawartośćStrony is None:
					logiKonsoli.debug(f"Nie udało się pobrać zawartości strony zastępstw szkoły o ID {identyfikatorSzkoły}. Aktualizacja została pominięta.")
					continue

				serweryDoSprawdzenia = [int(identyfikatorSerwera) for identyfikatorSerwera, konfiguracjaSerwera in serwery.items() if (konfiguracjaSerwera or {}).get("szkoła") == identyfikatorSzkoły]
				if not serweryDoSprawdzenia:
					continue
				zadania = [sprawdźSerwer(int(identyfikatorSerwera), zawartośćStrony) for identyfikatorSerwera in serweryDoSprawdzenia]
				await asyncio.gather(*zadania, return_exceptions=True)
		await asyncio.sleep(300)

# Sprawdzanie aktualizacji dla serwerów
blokadaNaSerwer = asyncio.Semaphore(3)
async def sprawdźSerwer(identyfikatorSerwera, zawartośćStrony):
	async with blokadaNaSerwer:
		await sprawdźSerwery(identyfikatorSerwera, zawartośćStrony)

async def sprawdźSerwery(identyfikatorSerwera, zawartośćStrony):
	async with blokadaKonfiguracji:
		konfiguracjaSerwera = (konfiguracja.get("serwery", {}) or {}).get(str(identyfikatorSerwera), {}).copy()

	identyfikatorKanału = konfiguracjaSerwera.get("identyfikator-kanalu")
	if not identyfikatorKanału:
		logiKonsoli.debug(f"Nie ustawiono identyfikatora kanału dla serwera o ID {identyfikatorSerwera}.")
		return
	try:
		kanał = bot.get_channel(int(identyfikatorKanału))
	except (TypeError, ValueError):
		logiKonsoli.warning(f"Nieprawidłowy identyfikator kanału {identyfikatorKanału} dla serwera o ID {identyfikatorSerwera}.")
		return
	if not kanał:
		logiKonsoli.warning(f"Nie znaleziono kanału o ID {identyfikatorKanału} dla serwera o ID {identyfikatorSerwera}.")
		return

	logiKonsoli.debug(f"Sprawdzanie aktualizacji dla serwera o ID {identyfikatorSerwera}.")
	try:
		wybraneKlasy = konfiguracjaSerwera.get("wybrane-klasy", [])
		wybraniNauczyciele = konfiguracjaSerwera.get("wybrani-nauczyciele", [])
		listaKlas = pobierzListęKlas(konfiguracjaSerwera.get("szkoła"))
		informacjeDodatkowe, aktualneWpisyZastępstw = wyodrębnijDane(zawartośćStrony, wybraneKlasy, wybraniNauczyciele, listaKlas)

		sumaKontrolnaAktualnychInformacjiDodatkowych = obliczSumęKontrolną(informacjeDodatkowe)
		sumaKontrolnaAktualnychWpisówZastępstw = obliczSumęKontrolną(aktualneWpisyZastępstw)

		poprzednieDane = await zarządzajPlikiemDanych(identyfikatorSerwera)
		if not isinstance(poprzednieDane, dict):
			poprzednieDane = {}
		sumaKontrolnaPoprzednichInformacjiDodatkowych = poprzednieDane.get("suma-kontrolna-informacji-dodatkowych", "")
		sumaKontrolnaPoprzednichWpisówZastępstw = poprzednieDane.get("suma-kontrolna-wpisow-zastepstw", "")

		if sumaKontrolnaAktualnychInformacjiDodatkowych != sumaKontrolnaPoprzednichInformacjiDodatkowych or sumaKontrolnaAktualnychWpisówZastępstw != sumaKontrolnaPoprzednichWpisówZastępstw:
			if sumaKontrolnaAktualnychWpisówZastępstw == sumaKontrolnaPoprzednichWpisówZastępstw:
				logiKonsoli.info(f"Treść informacji dodatkowych uległa zmianie dla serwera o ID {identyfikatorSerwera}. Zostaną wysłane zaktualizowane informacje.")
			else:
				logiKonsoli.info(f"Treść zastępstw uległa zmianie dla serwera o ID {identyfikatorSerwera}. Zostaną wysłane zaktualizowane zastępstwa.")
			try:
				aktualnyCzas = datetime.now(pytz.timezone("Europe/Warsaw")).strftime("%d-%m-%Y %H:%M:%S")
				if sumaKontrolnaAktualnychInformacjiDodatkowych != sumaKontrolnaPoprzednichInformacjiDodatkowych and sumaKontrolnaAktualnychWpisówZastępstw == sumaKontrolnaPoprzednichWpisówZastępstw:
					await wyślijAktualizacje(kanał, identyfikatorSerwera, informacjeDodatkowe, None, aktualnyCzas)
				elif sumaKontrolnaAktualnychInformacjiDodatkowych == sumaKontrolnaPoprzednichInformacjiDodatkowych and sumaKontrolnaAktualnychWpisówZastępstw != sumaKontrolnaPoprzednichWpisówZastępstw:
					await wyślijAktualizacje(kanał, identyfikatorSerwera, informacjeDodatkowe, aktualneWpisyZastępstw, aktualnyCzas)
				else:
					await wyślijAktualizacje(kanał, identyfikatorSerwera, informacjeDodatkowe, aktualneWpisyZastępstw, aktualnyCzas)

				poprzedniLicznik = int(poprzednieDane.get("licznik-zastepstw", 0))
				if sumaKontrolnaAktualnychWpisówZastępstw != sumaKontrolnaPoprzednichWpisówZastępstw:
					przyrost = policzZastępstwa(aktualneWpisyZastępstw) if aktualneWpisyZastępstw else 0
					nowyLicznik = poprzedniLicznik + przyrost

					statystykiNauczycieli = poprzednieDane.get("statystyki-nauczycieli", {}) or {}
					if not isinstance(statystykiNauczycieli, dict):
						statystykiNauczycieli = {}

					for tytuł, wpisy in (aktualneWpisyZastępstw or []):
						nazwa = (tytuł or "").strip() or "Ogólne"
						if normalizujTekst(nazwa) == "ogolne":
							continue
						klucz = nazwa.split("\n", 1)[-1].split("/", 1)[0].strip()
						statystykiNauczycieli[klucz] = int(statystykiNauczycieli.get(klucz, 0)) + len(wpisy)
				else:
					nowyLicznik = poprzedniLicznik
					statystykiNauczycieli = poprzednieDane.get("statystyki-nauczycieli", {}) or {}
					if not isinstance(statystykiNauczycieli, dict):
						statystykiNauczycieli = {}

				noweDane = {
					"suma-kontrolna-informacji-dodatkowych": sumaKontrolnaAktualnychInformacjiDodatkowych,
					"suma-kontrolna-wpisow-zastepstw": sumaKontrolnaAktualnychWpisówZastępstw,
					"licznik-zastepstw": nowyLicznik,
					"statystyki-nauczycieli": statystykiNauczycieli,
					"ostatni-raport": poprzednieDane.get("ostatni-raport", "")
				}
				await zarządzajPlikiemDanych(identyfikatorSerwera, noweDane)
			except discord.DiscordException as e:
				logiKonsoli.exception(f"Nie udało się wysłać wszystkich wiadomości dla serwera o ID {identyfikatorSerwera}, suma kontrolna nie zostanie zaktualizowana. Więcej informacji: {e}")
		else:
			logiKonsoli.debug(f"Treść nie uległa zmianie dla serwera o ID {identyfikatorSerwera}. Brak nowych aktualizacji.")
	except Exception as e:
		logiKonsoli.exception(f"Wystąpił błąd podczas przetwarzania aktualizacji dla serwera o ID {identyfikatorSerwera}. Więcej informacji: {e}")

# Ograniczenie interakcji bota w celu obsłużenia rate limitów discorda
blokadaNaKanał = defaultdict(lambda: asyncio.Lock())
async def ograniczWysyłanie(kanał, *args, **kwargs):
	async with blokadaNaKanał[kanał.id]:
		msg = await kanał.send(*args, **kwargs)
		return msg

async def ograniczUsuwanie(wiadomość):
	async with blokadaNaKanał[wiadomość.channel.id]:
		await wiadomość.delete()

async def ograniczReagowanie(wiadomość, emoji):
	async with blokadaNaKanał[wiadomość.channel.id]:
		await wiadomość.add_reaction(emoji)

# Wysyłanie aktualizacji zastępstw
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
				if "Zastępstwa z nieprzypisanymi klasami!" in tytuł:
					tekstZastępstw = tekstZastępstw + "\n\n**Informacja o tej wiadomości:**\nTe zastępstwa nie posiadają dołączonej klasy, więc zweryfikuj czy przypadkiem nie dotyczą one Ciebie!"

				embed = discord.Embed(
					title=f"**{tytuł}**",
					description=tekstZastępstw,
					color=discord.Color(0xca4449)
				)
				if not "Zastępstwa z nieprzypisanymi klasami!" in tytuł:
					embed.set_footer(text="Każdy nauczyciel, którego dotyczą zastępstwa pasujące do Twoich filtrów, zostanie załączany w oddzielnej wiadomości.")
				else:
					embed.set_footer(text="Każdy nauczyciel, którego dotyczą zastępstwa z nieprzypisanymi klasami, zostanie załączany w oddzielnej wiadomości.")
				ostatniaWiadomość = await ograniczWysyłanie(kanał, embed=embed)

		if ostatniaWiadomość and not "Zastępstwa z nieprzypisanymi klasami!" in tytuł:
			await ograniczReagowanie(ostatniaWiadomość, "❤️")
	except discord.DiscordException as e:
		logiKonsoli.exception(f"Wystąpił błąd podczas wysyłania wiadomości dla serwera o ID {identyfikatorSerwera}. Więcej informacji: {e}")
	except Exception as e:
		logiKonsoli.exception(f"Wystąpił nieoczekiwany błąd podczas wysyłania wiadomości dla serwera o ID {identyfikatorSerwera}. Więcej informacji: {e}")

# Sprawdzanie daty zakończenia roku szkolnego w celu wysłania rocznych statystyk
async def sprawdźKoniecRoku():
	await bot.wait_until_ready()
	while not bot.is_closed():
		try:
			async with blokadaKonfiguracji:
				dataZakończeniaRoku = (konfiguracja.get("koniec-roku-szkolnego") or "").strip()
				serwery = list((konfiguracja.get("serwery", {}) or {}).keys())
			if not dataZakończeniaRoku:
				logiKonsoli.warning("Nie ustawiono daty zakończenia roku szkolnego w pliku konfiguracyjnym. Uzupełnij brakujące dane i spróbuj ponownie.")
				await asyncio.sleep(3600)
				continue

			daneCzasu = None
			for formatCzasu in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
				try:
					daneCzasu = datetime.strptime(dataZakończeniaRoku, formatCzasu)
					break
				except ValueError:
					continue
			if daneCzasu is None:
				logiKonsoli.error(f"Niepoprawny format daty zakończenia roku szkolnego w pliku konfiguracyjnyn ({dataZakończeniaRoku}). Oczekiwane formaty: YYYY-MM-DD lub YYYY-MM-DD HH:MM:SS.")
				await asyncio.sleep(3600)
				continue
			if len(dataZakończeniaRoku) == 10:
				daneCzasu = daneCzasu.replace(hour=0, minute=0, second=0)
			koniecRoku = pytz.timezone("Europe/Warsaw").localize(daneCzasu)

			aktualnyCzas = datetime.now(pytz.timezone("Europe/Warsaw"))
			if aktualnyCzas >= koniecRoku:
				for identyfikatorSerwera in serwery:
					identyfikatorSerwera = int(identyfikatorSerwera)
					try:
						async with blokadaKonfiguracji:
							konfiguracjaSerwera = (konfiguracja.get("serwery", {}) or {}).get(str(identyfikatorSerwera), {}).copy()
						identyfikatorKanału = konfiguracjaSerwera.get("identyfikator-kanalu")
						if not identyfikatorKanału:
							continue
						kanał = bot.get_channel(int(identyfikatorKanału))
						if not kanał:
							continue

						dane = await zarządzajPlikiemDanych(identyfikatorSerwera) or {}
						ostatniRaport = (dane.get("ostatni-raport") or "").strip()
						licznik = int(dane.get("licznik-zastepstw", 0))
						if licznik == 0:
							dane["ostatni-raport"] = dataZakończeniaRoku
							dane["licznik-zastepstw"] = 0
							dane["statystyki-nauczycieli"] = {}
							for klucz in ("suma-kontrolna-informacji-dodatkowych", "suma-kontrolna-wpisow-zastepstw"):
								if klucz not in dane:
									dane[klucz] = ""
							await zarządzajPlikiemDanych(identyfikatorSerwera, dane)
							continue
						if ostatniRaport == dataZakończeniaRoku:
							continue

						wybraniNauczyciele = konfiguracjaSerwera.get("wybrani-nauczyciele", [])
						wybraneKlasy = konfiguracjaSerwera.get("wybrane-klasy", [])
						if wybraneKlasy and not wybraniNauczyciele:
							if kanał.permissions_for(kanał.guild.me).mention_everyone:
								wzmianka = await ograniczWysyłanie(kanał, "@everyone Podsumowanie roku szkolnego!", allowed_mentions=discord.AllowedMentions(everyone=True))
								await asyncio.sleep(5)
								try:
									await ograniczUsuwanie(wzmianka)
								except Exception:
									pass
							else:
								logiKonsoli.warning(f"Brak uprawnień do używania @everyone dla serwera o ID {identyfikatorSerwera}. Wzmianka została pominięta.")

							embed = discord.Embed(
								title="**Podsumowanie roku szkolnego!**",
								description=f"Dla tego serwera w tym roku szkolnym dostarczono **{licznik}** {odmieńZastępstwa(licznik)}! Poniżej znajduje się lista nauczycieli z największą liczbą zarejestrowanych zastępstw.",
								color=discord.Color(0xca4449)
							)

							statystyki = dane.get("statystyki-nauczycieli", {}) or {}
							if isinstance(statystyki, dict) and statystyki:
								sortowanie = sorted(statystyki.items(), key=lambda x: (-int(x[1]), x[0]))
								wolneMiejsca = 24 - len(embed.fields)
								if wolneMiejsca > 0:
									for nauczyciel, liczba in sortowanie[:wolneMiejsca]:
										embed.add_field(name=str(nauczyciel), value=f"Liczba zastępstw: {int(liczba)}", inline=True)
							embed.set_footer(text="Udanych i bezpiecznych wakacji!\nProjekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")
							await ograniczWysyłanie(kanał, embed=embed)

						elif (wybraneKlasy and wybraniNauczyciele) or (wybraniNauczyciele and not wybraneKlasy):
							if kanał.permissions_for(kanał.guild.me).mention_everyone:
								wzmianka = await ograniczWysyłanie(kanał, "@everyone Podsumowanie roku szkolnego!", allowed_mentions=discord.AllowedMentions(everyone=True))
								await asyncio.sleep(5)
								try:
									await ograniczUsuwanie(wzmianka)
								except Exception:
									pass
							else:
								logiKonsoli.warning(f"Brak uprawnień do używania @everyone dla serwera {identyfikatorSerwera}. Wzmianka została pominięta.")

							embed = discord.Embed(
								title="**Podsumowanie roku szkolnego!**",
								description=f"Dla tego serwera w tym roku szkolnym dostarczono **{licznik}** {odmieńZastępstwa(licznik)}! Poniżej znajduje się lista nauczycieli z największą liczbą zarejestrowanych zastępstw. (Pominięto nauczycieli ustawionych w filtrze).",
								color=discord.Color(0xca4449)
							)

							statystyki = dane.get("statystyki-nauczycieli", {}) or {}
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
							embed.set_footer(text="Udanych i bezpiecznych wakacji!\nProjekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")
							await ograniczWysyłanie(kanał, embed=embed)

						dane["ostatni-raport"] = dataZakończeniaRoku
						dane["licznik-zastepstw"] = 0
						dane["statystyki-nauczycieli"] = {}
						for klucz in ("suma-kontrolna-informacji-dodatkowych", "suma-kontrolna-wpisow-zastepstw"):
							if klucz not in dane:
								dane[klucz] = ""
						await zarządzajPlikiemDanych(identyfikatorSerwera, dane)
					except Exception as e:
						logiKonsoli.exception(f"Wystąpił błąd podczas raportowania statystyk zastępstw na koniec roku dla serwera o ID {identyfikatorSerwera}. Więcej informacji: {e}")
			await asyncio.sleep(24 * 3600)
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił nieoczekiwany błąd podczas sprawdzania, czy nastąpiło zakończenie roku szkolnego. Więcej informacji: {e}")
			await asyncio.sleep(3600)

# Usuwanie serwera z konfiguracji po wyjściu bota z serwera
@bot.event
async def on_guild_remove(guild):
	await usuńSerwerZKonfiguracji(guild.id)

# Wysyłanie instrukcji konfiguracji administratorom serwera
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

# Polecenie /skonfiguruj
def pobierzSłownikSerwera(identyfikatorSerwera: str) -> dict:
	identyfikatorSerwera = str(identyfikatorSerwera)
	serwery = konfiguracja.setdefault("serwery", {})
	dane = serwery.setdefault(identyfikatorSerwera, {})
	if "identyfikator-kanalu" not in dane:
		dane["identyfikator-kanalu"] = None
	if "szkoła" not in dane:
		dane["szkoła"] = None
	if "wybrane-klasy" not in dane or not isinstance(dane.get("wybrane-klasy"), list):
		dane["wybrane-klasy"] = list(dane.get("wybrane-klasy") or [])
	if "wybrani-nauczyciele" not in dane or not isinstance(dane.get("wybrani-nauczyciele"), list):
		dane["wybrani-nauczyciele"] = list(dane.get("wybrani-nauczyciele") or [])
	serwery[identyfikatorSerwera] = dane
	return dane

async def zapiszKluczeSerwera(identyfikatorSerwera: str, dane: dict):
	identyfikatorSerwera = str(identyfikatorSerwera)
	lokalneDane = dict(dane or {})
	async with blokadaKonfiguracji:
		serwery = konfiguracja.setdefault("serwery", {}) or {}
		daneSerwera = pobierzSłownikSerwera(identyfikatorSerwera)
		poprzedniaSzkoła = daneSerwera.get("szkoła")
		aktualnaSzkoła = lokalneDane.get("szkoła") if "szkoła" in lokalneDane else None
		if aktualnaSzkoła not in (None, "") and poprzedniaSzkoła and poprzedniaSzkoła != aktualnaSzkoła:
			daneSerwera.pop("wybrane-klasy", None)
			daneSerwera.pop("wybrani-nauczyciele", None)
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
			wartość = lokalneDane.pop("identyfikator-kanalu")
			if wartość not in (None, "", []):
				daneSerwera["identyfikator-kanalu"] = str(wartość)
		if "szkoła" in lokalneDane:
			wartość = lokalneDane.pop("szkoła")
			if wartość not in (None, ""):
				daneSerwera["szkoła"] = wartość
		for klucz, wartość in lokalneDane.items():
			if wartość is not None:
				daneSerwera[klucz] = wartość
		serwery[identyfikatorSerwera] = daneSerwera
		konfiguracja["serwery"] = serwery
		snapshot = copy.deepcopy(konfiguracja)
	await zapiszKonfiguracje(snapshot)

async def wyczyśćFiltry(identyfikatorSerwera: str):
	identyfikatorSerwera = str(identyfikatorSerwera)
	async with blokadaKonfiguracji:
		daneSerwera = pobierzSłownikSerwera(identyfikatorSerwera)
		daneSerwera["identyfikator-kanalu"] = None
		daneSerwera["szkoła"] = None
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
			mapaKluczy[klucz].append(element)
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
			kandydat = normalizowaneDoOryginalnych[normaKandydata][0]
			sugestie[wpis] = kandydat
		else:
			nieZnaleziono.append(wpis)
	return idealneDopasowania, sugestie, nieZnaleziono

def pobierzListęKlas(szkoła: str | None = None) -> list[str]:
	suroweDane = ((konfiguracja.get("szkoły") or {}).get(szkoła, {}) or {}).get("lista-klas", {}) if szkoła else konfiguracja.get("lista-klas", {})
	if isinstance(suroweDane, dict):
		return [klasa for grupy in suroweDane.values() for klasa in grupy]
	if isinstance(suroweDane, list):
		return suroweDane
	return []

class WidokPonownegoWprowadzania(discord.ui.View):
	def __init__(self, typDanych: str, listaDoDopasowania: list[str], wiadomość: discord.Message, identyfikatorKanału: str, szkoła: str, timeout: float = 120.0):
		super().__init__(timeout=timeout)
		self.typDanych = typDanych
		self.lista = listaDoDopasowania
		self.wiadomość = wiadomość
		self.identyfikatorKanału = identyfikatorKanału
		self.szkoła = szkoła

	@discord.ui.button(label="Wprowadź ponownie", style=discord.ButtonStyle.secondary)
	async def wprowadźPonownie(self, interaction: discord.Interaction, button: discord.ui.Button):
		try:
			await interaction.response.send_modal(ModalWybierania(self.typDanych, self.lista, self.wiadomość, self.identyfikatorKanału, self.szkoła))
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd po naciśnięciu przycisku „Wprowadź ponownie” (w class WidokPonownegoWprowadzania) dla {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
			with contextlib.suppress(Exception):
				await interaction.followup.send("Wystąpił błąd podczas otwierania formularza. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)

class WidokAkceptacjiSugestii(discord.ui.View):
	def __init__(self, typDanych: str, identyfikatorSerwera: str, idealneDopasowania: list[str], sugestie: dict[str, str], listaDoDopasowania: list[str], wiadomość: discord.Message, identyfikatorKanału: str, szkoła: str, timeout: float = 120.0):
		super().__init__(timeout=timeout)
		self.typDanych = typDanych
		self.identyfikatorSerwera = identyfikatorSerwera
		self.idealneDopasowania = idealneDopasowania[:]
		self.sugestie = sugestie.copy()
		self.lista = listaDoDopasowania
		self.wiadomość = wiadomość
		self.identyfikatorKanału = identyfikatorKanału
		self.szkoła = szkoła

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
			await zapiszKluczeSerwera(self.identyfikatorSerwera, {"identyfikator-kanalu": self.identyfikatorKanału, "szkoła": self.szkoła, kluczFiltru: finalne})
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd po naciśnięciu przycisku „Akceptuj sugestie” dla {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
			with contextlib.suppress(Exception):
				await interaction.followup.send("Wystąpił błąd podczas akceptacji danych. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)

		konfiguracjaSerwera = pobierzSłownikSerwera(str(interaction.guild.id))
		kanał = f"<#{konfiguracjaSerwera["identyfikator-kanalu"]}>" if konfiguracjaSerwera.get("identyfikator-kanalu") else "Brak"
		klasy = ", ".join(re.sub(r"(\d)\s+([A-Za-z])", r"\1\2", klasa) for klasa in konfiguracjaSerwera.get("wybrane-klasy", [])) or "Brak"
		nauczyciele = ", ".join(f"{nauczyciel}" for nauczyciel in konfiguracjaSerwera.get("wybrani-nauczyciele", [])) or "Brak"
		identyfikatorSzkoły = konfiguracjaSerwera.get("szkoła")
		nazwaSzkoły = konfiguracja["szkoły"].get(identyfikatorSzkoły, {}).get("nazwa", identyfikatorSzkoły)

		embed = discord.Embed(
			title="**Zapisano wprowadzone dane!**",
			description=f"Aktualna konfiguracja Twojego serwera dla szkoły **{nazwaSzkoły}** została wyświetlona poniżej.",
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
			await interaction.response.send_modal(ModalWybierania(self.typDanych, self.lista, self.wiadomość, self.identyfikatorKanału, self.szkoła))
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd po naciśnięciu przycisku „Wprowadź ponownie” (w class WidokAkceptacjiSugestii) dla {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
			with contextlib.suppress(Exception):
				await interaction.followup.send("Wystąpił błąd podczas otwierania formularza. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)

class ModalWybierania(discord.ui.Modal):
	def __init__(self, typDanych: str, listaDoDopasowania: list[str], wiadomość: discord.Message, identyfikatorKanału: str, szkoła: str):
		super().__init__(title="Wprowadź dane do formularza")
		self.typDanych = typDanych
		self.lista = listaDoDopasowania
		self.wiadomość = wiadomość
		self.identyfikatorKanału = identyfikatorKanału
		self.szkoła = szkoła

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
					title="**Nie znaleziono wprowadzonych danych**",
					description=(
						"Nie znaleziono odpowiadających wpisów dla następujących danych:\n"
						+ "\n".join(f"- **{wprowadzoneDane}**" for wprowadzoneDane in nieZnaleziono)
						+ "\n\nSpróbuj ponownie, naciskając przycisk **Wprowadź ponownie**."
					),
					color=discord.Color(0xca4449),
				)
				embed.set_footer(text="Projekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")
				view = WidokPonownegoWprowadzania(self.typDanych, self.lista, self.wiadomość, self.identyfikatorKanału, self.szkoła)
				await interaction.response.defer()
				await self.wiadomość.edit(embed=embed, view=view)
				return

			if sugestie:
				opis = ""
				if idealneDopasowania:
					opis += "**Znalezione dokładne dopasowania:**\n" + ", ".join(f"**{dopasowanie}**" for dopasowanie in idealneDopasowania) + "\n\n"
				opis += "**Proponowane dopasowania:**\n"
				for oryginalne, sugestia in sugestie.items():
					opis += f"- **{oryginalne}**  →  **{sugestia}**\n"
				opis += "\nJeśli akceptujesz propozycje, naciśnij przycisk **Akceptuj sugestie**. Jeśli chcesz wpisać ponownie, naciśnij przycisk **Wprowadź ponownie**."

				embed = discord.Embed(
					title=f"Sugestie dopasowania wprowadzonych danych",
					description=opis,
					color=discord.Color(0xca4449),
				)
				embed.set_footer(text="Projekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")
				view = WidokAkceptacjiSugestii(self.typDanych, identyfikatorSerwera, idealneDopasowania, sugestie, self.lista, self.wiadomość, self.identyfikatorKanału, self.szkoła)
				await interaction.response.defer()
				await self.wiadomość.edit(embed=embed, view=view)
				return

			finalne = usuńDuplikaty(idealneDopasowania)
			kluczFiltru = "wybrane-klasy" if self.typDanych == "klasy" else "wybrani-nauczyciele"
			await zapiszKluczeSerwera(identyfikatorSerwera, {"identyfikator-kanalu": self.identyfikatorKanału, "szkoła": self.szkoła, kluczFiltru: finalne})

			konfiguracjaSerwera = pobierzSłownikSerwera(str(interaction.guild.id))
			kanał = f"<#{konfiguracjaSerwera["identyfikator-kanalu"]}>" if konfiguracjaSerwera.get("identyfikator-kanalu") else "Brak"
			klasy = ", ".join(re.sub(r"(\d)\s+([A-Za-z])", r"\1\2", klasa) for klasa in konfiguracjaSerwera.get("wybrane-klasy", [])) or "Brak"
			nauczyciele = ", ".join(f"{nauczyciel}" for nauczyciel in konfiguracjaSerwera.get("wybrani-nauczyciele", [])) or "Brak"
			identyfikatorSzkoły = konfiguracjaSerwera.get("szkoła")
			nazwaSzkoły = konfiguracja["szkoły"].get(identyfikatorSzkoły, {}).get("nazwa", identyfikatorSzkoły)

			embed = discord.Embed(
				title="**Zapisano wprowadzone dane!**",
				description=f"Aktualna konfiguracja Twojego serwera dla szkoły **{nazwaSzkoły}** została wyświetlona poniżej.",
				color=discord.Color(0xca4449)
			)
			embed.add_field(name="Kanał tekstowy:", value=kanał)
			embed.add_field(name="Wybrane klasy:", value=klasy)
			embed.add_field(name="Wybrani nauczyciele:", value=nauczyciele)
			embed.set_footer(text="Projekt licencjonowany na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")
			await interaction.response.defer()
			await self.wiadomość.edit(embed=embed, view=None)
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd po naciśnięciu przycisku wysyłającego dane do zapisu (on_submit) dla {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
			with contextlib.suppress(Exception):
				await interaction.response.send_message("Wystąpił błąd podczas przetwarzania danych. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)

class PrzyciskUczeń(discord.ui.Button):
	def __init__(self, identyfikatorKanału: str, szkoła: str):
		super().__init__(label="Uczeń", style=discord.ButtonStyle.primary)
		self.identyfikatorKanału = identyfikatorKanału
		self.szkoła = szkoła

	async def callback(self, interaction: discord.Interaction):
		listaKlas = pobierzListęKlas(self.szkoła)
		if listaKlas == []:
			embed = discord.Embed(
				title="**Opcja niedostępna!**",
				description="Ta opcja nie jest dostępna w Twojej szkole. W razie pytań skontaktuj się z administratorem bota.",
				color=discord.Color(0xca4449),
			)
			embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")
			await interaction.response.send_message(embed=embed, ephemeral=True)
		else:
			try:
				await interaction.response.send_modal(ModalWybierania("klasy", listaKlas, interaction.message, self.identyfikatorKanału, self.szkoła))
			except Exception as e:
				logiKonsoli.exception(f"Wystąpił błąd po naciśnięciu przycisku „Uczeń” dla użytkownika {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
				with contextlib.suppress(Exception):
					await interaction.followup.send("Wystąpił błąd podczas otwierania formularza. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)

class PrzyciskNauczyciel(discord.ui.Button):
	def __init__(self, identyfikatorKanału: str, szkoła: str):
		super().__init__(label="Nauczyciel", style=discord.ButtonStyle.primary)
		self.identyfikatorKanału = identyfikatorKanału
		self.szkoła = szkoła

	async def callback(self, interaction: discord.Interaction):
		listaNauczycieli = ((konfiguracja.get("szkoły") or {}).get(self.szkoła, {}) or {}).get("lista-nauczycieli", [])
		if listaNauczycieli == []:
			embed = discord.Embed(
				title="**Opcja niedostępna!**",
				description="Ta opcja nie jest dostępna w Twojej szkole. W razie pytań skontaktuj się z administratorem bota.",
				color=discord.Color(0xca4449),
			)
			embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")
			await interaction.response.send_message(embed=embed, ephemeral=True)
		else:
			try:
				await interaction.response.send_modal(ModalWybierania("nauczyciele", listaNauczycieli, interaction.message, self.identyfikatorKanału, self.szkoła))
			except Exception as e:
				logiKonsoli.exception(f"Wystąpił błąd po naciśnięciu przycisku „Nauczyciel” dla użytkownika {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
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
				title="**Wyczyszczono konfigurację serwera**",
				description="Twój serwer nie będzie otrzymywał powiadomień z nowymi zastępstwami do czasu ponownej ich konfiguracji.",
				color=discord.Color(0xca4449),
			)
			embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")
			await interaction.response.edit_message(embed=embed, view=None)
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd po naciśnięciu przycisku „Wyczyść filtry” dla {interaction.user} na serwerze {interaction.guild}. Więcej informacji: {e}")
			with contextlib.suppress(Exception):
				await interaction.followup.send("Wystąpił błąd podczas przetwarzania danych. Spróbuj ponownie lub skontaktuj się z administratorem bota.", ephemeral=True)

class WidokGłówny(discord.ui.View):
	def __init__(self, identyfikatorKanału: str, szkoła: str):
		super().__init__()
		self.add_item(PrzyciskUczeń(identyfikatorKanału, szkoła))
		self.add_item(PrzyciskNauczyciel(identyfikatorKanału, szkoła))
		self.add_item(PrzyciskWyczyśćFiltry())

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

# Polecenie /statystyki
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

# Polecenie /informacje
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
	logiKonsoli.info("Przechwycono Ctrl+C. Trwa zatrzymywanie bota...")
	bot.loop.call_soon_threadsafe(lambda: asyncio.create_task(bot.close()))
signal.signal(signal.SIGINT, wyłączBota)
if hasattr(signal, "SIGTERM"):
	signal.signal(signal.SIGTERM, wyłączBota)
if hasattr(signal, "SIGBREAK"):
	signal.signal(signal.SIGBREAK, wyłączBota)

# Uruchomienie bota
token = os.getenv("ZASTEPSTWA")
if not token:
	token = konfiguracja.get("token")
	if not token:
		logiKonsoli.critical("Nie znaleziono tokena bota. Utwórz zmienną środowiskową z zawartością tokena o nazwie „ZASTEPSTWA” lub uzupełnij plik konfiguracyjny.")
		sys.exit(1)
try:
	bot.run(token)
except discord.LoginFailure as e:
	logiKonsoli.critical(f"Nieprawidłowy token bota. Więcej informacji: {e}")
	raise
except Exception as e:
	logiKonsoli.exception(f"Wystąpił krytyczny błąd podczas uruchamiania bota. Więcej informacji: {e}")