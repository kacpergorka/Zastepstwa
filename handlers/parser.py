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
from collections import defaultdict
import re

# Zewnętrzne biblioteki
from bs4 import BeautifulSoup, NavigableString

# Wewnętrzne importy
from handlers.logging import logiKonsoli
from helpers.helpers import (
	dopasujDoKlasy,
	dopasujDoNauczyciela,
	normalizujTekst,
	wyodrębnijNauczycieli
)

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