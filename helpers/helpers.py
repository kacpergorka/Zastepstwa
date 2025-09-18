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
import asyncio, copy, difflib, hashlib, re, unicodedata
from collections import defaultdict
from datetime import datetime

# Wewnętrzne importy
from handlers.configuration import (
	blokadaKonfiguracji,
	konfiguracja,
	zapiszKonfiguracje
)

# Oblicza sumę kontrolną dla wyodrębnionych wpisów zastępstw
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

# Ogranicza interakcje bota w celu obsłużenia rate limitów discorda
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

# Normalizuje tekst (używane w celu prawidłowej filtracji)
def normalizujTekst(tekst: str) -> str:
	if not tekst or not isinstance(tekst, str):
		return ""
	tekst = tekst.strip()
	tekst = unicodedata.normalize("NFKD", tekst)
	tekst = "".join(znak for znak in tekst if not unicodedata.combining(znak))
	tekst = tekst.replace(".", " ")
	tekst = re.sub(r"\s+", " ", tekst)
	return tekst.lower()

# Tworzy zestaw kluczy dopasowań (używane w celu prawidłowej filtracji)
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

# Pobiera słownik wybranego serwera (używane w poleceniu /skonfiguruj)
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

# Usuwa duplikaty z listy (używane w poleceniu /skonfiguruj)
def usuńDuplikaty(sekwencja):
	widziane = set()
	wynik = []
	for element in sekwencja:
		if element not in widziane:
			wynik.append(element)
			widziane.add(element)
	return wynik

# Zapisuje klucze wybranego serwera (używane w poleceniu /skonfiguruj)
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

# Czyści filtry dla danego serwera (używane w poleceniu /skonfiguruj)
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

# Dopasowuje wpisane podczas konfiguracji wpisy do listy w pliku konfiguracyjnym (używane w poleceniu /skonfiguruj)
def dopasujWpisyDoListy(wpisy: list[str], listaDoDopasowania: list[str], cutoff: float = 0.6):
	# Tworzy dwie wersje kluczy normalizacyjnych (używane w celu prawidłowego dopasowania)
	def kluczeNormalizacyjne(tekst: str) -> list[str]:
		tekstNormalizowany = normalizujTekst(tekst)
		brakSpacji = re.sub(r"\s+", "", tekstNormalizowany)
		return [tekstNormalizowany, brakSpacji]

	# Buduje indeksy wyszukiwania do dopasowania tekstu (używane w celu prawidłowego dopasowania)
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

# Pobiera listę klas wybranej szkoły (używane w poleceniu /skonfiguruj)
def pobierzListęKlas(szkoła: str | None = None) -> list[str]:
	suroweDane = ((konfiguracja.get("szkoły") or {}).get(szkoła, {}) or {}).get("lista-klas", {}) if szkoła else konfiguracja.get("lista-klas", {})
	if isinstance(suroweDane, dict):
		return [klasa for grupy in suroweDane.values() for klasa in grupy]
	if isinstance(suroweDane, list):
		return suroweDane
	return []

# Liczy liczbę zastępstw (używane w statystykach zastępstw)
def policzZastępstwa(aktualneWpisyZastępstw) -> int:
	if not aktualneWpisyZastępstw:
		return 0
	try:
		return sum(len(wpisy) for _, wpisy in aktualneWpisyZastępstw)
	except Exception:
		return 0

# Odmienia słowo „zastępstwo” w zależności od liczby zastępstw (używane w poleceniu /statystyki)
def odmieńZastępstwa(licznik: int) -> str:
	if abs(licznik) == 1:
		return "zastępstwo"
	if 11 <= abs(licznik) % 100 <= 14:
		return "zastępstw"
	if abs(licznik) % 10 in (2, 3, 4):
		return "zastępstwa"
	return "zastępstw"

# Pobiera liczbę serwerów, na których znajduje się bot (używane w poleceniu /informacje)
def pobierzLiczbęSerwerów(bot):
	return len(bot.guilds)

# Pobiera czas działania bota bez przerwy (używane w poleceniu /informacje)
def pobierzCzasDziałania(bot):
	czasDziałania = datetime.now() - bot.zaczynaCzas
	dni, reszta = divmod(czasDziałania.total_seconds(), 86400)
	godziny, reszta = divmod(reszta, 3600)
	minuty, sekundy = divmod(reszta, 60)
	return f"**{int(dni)}** dni, **{int(godziny)}** godz., **{int(minuty)}** min. i **{int(sekundy)}** sek."