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
import aiohttp, asyncio, re
from collections import defaultdict

# Zewnętrzne biblioteki
from bs4 import BeautifulSoup, NavigableString

# Wewnętrzne importy
from handlers.logging import logiKonsoli
from helpers.helpers import (
	normalizujTekst,
	zwróćNazwyKluczy
)

# Pobiera zawartość strony internetowej
async def pobierzZawartośćStrony(bot, url, kodowanie=None):
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

# Wyodrębnia dane z pobranego pliku strony internetowej
def wyodrębnijDane(zawartośćStrony, wybraneKlasy, wybraniNauczyciele=None, listaKlas=None):
	# Czyści i normalizuje zawartości pobranego pliku strony internetowej
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

	# Sprawdza, czy dana komórka ma przynajmniej jedną interesującą nas klasę
	def czyKomórkaMaKlasy(komórka, nazwy):
		klasy = komórka.get("class") or []
		if isinstance(klasy, str):
			klasy = [klasy]
		return any(klasa in nazwy for klasa in klasy)

	# Sprawdza, czy w tabeli HTML istnieje przynajmniej jeden wiersz z realnym zastępstwem
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

	# Wyciąga nazwiska nauczycieli z nagłówka i treści komórki
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

	# Dopasowuje wyodrębnionych nauczycieli do listy filtrowanych
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

	# Dopasowuje wyodrębnionych z wiersza klas do listy filtrowanych
	def dopasujDoKlasy(komórkiWiersza: list, wybraneKlasy: list) -> bool:
		if not wybraneKlasy:
			return False

		komórki = komórkiWiersza[:]
		if len(komórki) > 1 and komórki[1]:
			komórki[1] = komórki[1].split("-", 1)[0]
		if len(komórki) >= 4 and komórki[3]:
			komórki[3] = re.sub(r"\d+\s*h\s*lek\.?", "", komórki[3], flags=re.IGNORECASE)

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
				dopasowaneDoNauczyciela = dopasujDoNauczyciela(wyodrębnieniNauczyciele, wybraniNauczyciele)
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
					kluczNauczyciela = f"Zastępstwa bez dołączonych klas!\n{domyślnyTytuł}" if zastępstwoBezKlasy else domyślnyTytuł
					zgrupowane[kluczNauczyciela].append(tekstWpisówZastępstw)

		wpisyZastępstw = [(nauczyciel, zgrupowane[nauczyciel]) for nauczyciel in zgrupowane if zgrupowane[nauczyciel]]
		wpisyZastępstw.sort(key=lambda x: 0 if "Zastępstwa bez dołączonych klas!" in x[0] else 1)

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