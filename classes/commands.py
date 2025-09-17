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
import contextlib, re

# Zewnętrzne biblioteki
import discord

# Wewnętrzne importy
from handlers.configuration import konfiguracja
from handlers.logging import logiKonsoli
from helpers.helpers import (
	dopasujWpisyDoListy,
	pobierzListęKlas,
	pobierzSłownikSerwera,
	usuńDuplikaty,
	wyczyśćFiltry,
	zapiszKluczeSerwera
)

# Widok ponownego wprowadzania (polecenie /skonfiguruj)
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

# Widok akceptacji sugestii (polecenie /skonfiguruj)
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

# Modal wybierania (polecenie /skonfiguruj)
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

# Przycisk „Uczeń” (polecenie /skonfiguruj)
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

# Przycisk „Nauczyciel” (polecenie /skonfiguruj)
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

# Przycisk „Wyczyść filtry” (polecenie /skonfiguruj)
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

# Widok główny (polecenie /skonfiguruj)
class WidokGłówny(discord.ui.View):
	def __init__(self, identyfikatorKanału: str, szkoła: str):
		super().__init__()
		self.add_item(PrzyciskUczeń(identyfikatorKanału, szkoła))
		self.add_item(PrzyciskNauczyciel(identyfikatorKanału, szkoła))
		self.add_item(PrzyciskWyczyśćFiltry())