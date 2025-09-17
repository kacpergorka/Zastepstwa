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

# Wewnętrzne importy
from handlers.configuration import (
	blokadaKonfiguracji,
	konfiguracja,
	zapiszKonfiguracje
)

# Normalizacja tekstu
def normalizujTekst(tekst: str) -> str:
	if not tekst or not isinstance(tekst, str):
		return ""
	tekst = tekst.strip()
	tekst = unicodedata.normalize("NFKD", tekst)
	tekst = "".join(znak for znak in tekst if not unicodedata.combining(znak))
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
def dopasujDoNauczyciela(wyodrębnieniNauczyciele: set, wybraniNauczyciele: list) -> bool:
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

# Pobieranie słownika wybranego serwera
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

# Zapisywanie kluczy wybranego serwera
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

# Czyszczenie filtrów dla danego serwera
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

# Tworzenie dwóch wersji kluczy normalizacyjnych
def kluczeNormalizacyjne(tekst: str) -> list[str]:
	tekstNormalizowany = normalizujTekst(tekst)
	brakSpacji = re.sub(r"\s+", "", tekstNormalizowany)
	return [tekstNormalizowany, brakSpacji]

# Usuwanie duplikatów z listy
def usuńDuplikaty(sekwencja):
	widziane = set()
	wynik = []
	for element in sekwencja:
		if element not in widziane:
			wynik.append(element)
			widziane.add(element)
	return wynik

# Budowanie indeksów wyszukiwania do dopasowania tekstu
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

# Dopasowywanie wpisanych podczas konfiguracji wpisów do listy w pliku konfiguracyjnym
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

# Pobieranie listy klas wybranej szkoły
def pobierzListęKlas(szkoła: str | None = None) -> list[str]:
	suroweDane = ((konfiguracja.get("szkoły") or {}).get(szkoła, {}) or {}).get("lista-klas", {}) if szkoła else konfiguracja.get("lista-klas", {})
	if isinstance(suroweDane, dict):
		return [klasa for grupy in suroweDane.values() for klasa in grupy]
	if isinstance(suroweDane, list):
		return suroweDane
	return []

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