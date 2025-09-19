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
import asyncio, contextlib, os, signal, sys
from datetime import datetime

# Zewnętrzne biblioteki
import aiohttp, discord, pytz

# Wewnętrzne importy
from assets.ascii import ascii
from commands import (
	informacje,
	skonfiguruj,
	statystyki
)
from events import (
	join,
	remove
)
from handlers.configuration import (
	blokadaKonfiguracji,
	konfiguracja
)
from handlers.data import zarządzajPlikiemDanych
from handlers.logging import logiKonsoli
from handlers.notifications import wyślijAktualizacje
from handlers.parser import (
	pobierzZawartośćStrony,
	wyodrębnijDane
)
from helpers.helpers import (
	normalizujTekst,
	obliczSumęKontrolną,
	odmieńZastępstwa,
	ograniczUsuwanie,
	ograniczWysyłanie,
	pobierzListęKlas,
	policzZastępstwa,
	zwróćNazwyKluczy,
)

# Domyślne ustawienia, działania i operacje bota
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
				logiKonsoli.info("Zadanie sprawdzające aktualizacje zastępstw jest już uruchomione. Próba ponownego jego uruchomienia została zatrzymana.")

			if not getattr(self, "koniecRoku", None) or self.koniecRoku.done():
				self.koniecRoku = asyncio.create_task(sprawdźKoniecRoku())
			else:
				logiKonsoli.info("Zadanie sprawdzające zakończenie roku szkolnego jest już uruchomione. Próba ponownego jego uruchomienia została zatrzymana.")
			logiKonsoli.info(f"Wszystkie zadania zostały poprawnie uruchomione. Enjoy!")
		except Exception as e:
			logiKonsoli.exception(f"Wystąpił błąd podczas wywoływania funkcji on_ready. Więcej informacji: {e}")

# Konfiguracja uprawnień bota
intents = discord.Intents.default()
bot = Zastępstwa(intents=intents)

# Import poleceń i eventów do synchronizacji
informacje.ustaw(bot)
skonfiguruj.ustaw(bot)
statystyki.ustaw(bot)
join.ustaw(bot)
remove.ustaw(bot)

# Sprawdza aktualizacje zastępstw
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

				zawartośćStrony = await pobierzZawartośćStrony(bot, url, kodowanie=(daneSzkoły or {}).get("kodowanie"))
				if zawartośćStrony is None:
					logiKonsoli.debug(f"Nie udało się pobrać zawartości strony zastępstw szkoły o ID {identyfikatorSzkoły}. Aktualizacja została pominięta.")
					continue

				serweryDoSprawdzenia = [int(identyfikatorSerwera) for identyfikatorSerwera, konfiguracjaSerwera in serwery.items() if (konfiguracjaSerwera or {}).get("szkoła") == identyfikatorSzkoły]
				if not serweryDoSprawdzenia:
					continue
				zadania = [sprawdźSerwer(int(identyfikatorSerwera), zawartośćStrony) for identyfikatorSerwera in serweryDoSprawdzenia]
				await asyncio.gather(*zadania, return_exceptions=True)
		await asyncio.sleep(300)

# Sprawdza aktualizacje per serwer
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

# Sprawdza datę zakończenia roku szkolnego (używane w celu wysłania całorocznego podsumowania statystyk zastępstw)
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

# Wyłącza bota w bezpieczny sposób
def wyłączBota(*_):
	logiKonsoli.info("Przechwycono Ctrl+C. Trwa zatrzymywanie bota...")
	bot.loop.call_soon_threadsafe(lambda: asyncio.create_task(bot.close()))
signal.signal(signal.SIGINT, wyłączBota)
if hasattr(signal, "SIGTERM"):
	signal.signal(signal.SIGTERM, wyłączBota)
if hasattr(signal, "SIGBREAK"):
	signal.signal(signal.SIGBREAK, wyłączBota)

# Uruchamia bota
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