# Standardowe biblioteki Pythona
import json
import os
import logging
import logging.handlers
import asyncio
from datetime import datetime
import random
import hashlib

# Zewnętrzne biblioteki
import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import pytz

# Zmienne
BOT_VERSION = "1.3.5-stable"
TIMEZONE = pytz.timezone("Europe/Warsaw")	# Strefa czasowa dla logów.
CHECK_INTERVAL = 300						# Czas (w sekundach) jaki bot wyczekuje, aby ponownie sprawdzić aktualizacje.
URL = "https://zastepstwa.zse.bydgoszcz.pl/"# URL do pobierania zastępstw.
ENCODING = "iso-8859-2"						# Kodowanie strony, z której pobierane są informacje. Jeżeli kodowanie nie będzie zgodne z tym na stronie, to bot będzie niepoprawnie wysyłał zastępstwa!
TEACHERS_CELL_COLOR = "#69AADE"				# W przypadku strony z zastępstwami mojej szkoły, nauczyciel, za którego są zastępstwa, znajduje się w komórce z kolorem #69AADE, więc bot wczytuje jej zawartość w tytuł embeda, który wysyła podczas aktualizacji. Domyślnie ustawiony kolor przez VULCAN to #FFDFBF, ale radzę sprawdzić indywidualnie.
EMBEDS_COLOR = discord.Color(0xca4449)		# Kolor embedów, które wysyła bot.
BOT_ADMINISTRATORS = f"[Kacper Górka](https://www.instagram.com/kacperekyea/)"	# Administratorzy bota oraz ich kontakt. Informacje tutaj, jak i w niższych zmiennych wprowadzone, będą wyświetlać się w komendzie `/informacje`.
GITHUB_REPOSITORY = "https://github.com/kacpergorka/Zastepstwa"					# URL do repozytorium GitHuba. JEŻELI NIE WPROWADZASZ W KODZIE ZMIAN INNYCH NIŻ PRZEZNACZONA KONFIGURACJA, NIE ZMIENIAJ TEJ ZMIENNEJ!
SHORT_GITHUB_REPOSITORY = "kacpergorka/zastepstwa"								# Skrócona wersja repozytorium GitHuba. JEŻELI NIE WPROWADZASZ W KODZIE ZMIAN INNYCH NIŻ PRZEZNACZONA KONFIGURACJA, NIE ZMIENIAJ TEJ ZMIENNEJ!
GITHUB_ISSUES = "https://github.com/kacpergorka/Zastepstwa/issues"				# URL do issues na GitHubie. JEŻELI NIE WPROWADZASZ W KODZIE ZMIAN INNYCH NIŻ PRZEZNACZONA KONFIGURACJA, NIE ZMIENIAJ TEJ ZMIENNEJ!
classes_by_grade = {
	"1": ["1 A", "1 D", "1 F", "1 H"],
	"2": ["2 A", "2 B", "2 D", "2 E", "2 F", "2 H", "2 I", "2 J"],
	"3": ["3 A", "3 B", "3 D", "3 E", "3 F", "3 H", "3 I", "3 J"],
	"4": ["4 A", "4 B", "4 D", "4 E", "4 F", "4 H", "4 I"],
	"5": ["5 A", "5 B", "5 D", "5 E", "5 F", "5 H", "5 I"]
	}	# Tutaj znajdują się klasy, które filtruje bot. Klasy tutaj wprowadzone można zmienić pod własne zapotrzebowania.

# Konfiguracja logów
class TimezoneFormatter(logging.Formatter):
	def formatTime(self, record, datefmt=None):
		return datetime.now(TIMEZONE).strftime("%d-%m-%Y %H:%M:%S")

def setup_logging():
	console_logger = logging.getLogger("discord")
	console_logger.setLevel(logging.DEBUG)
	commands_logger = logging.getLogger("discord.commands")
	commands_logger.setLevel(logging.DEBUG)
	
	console_handler = logging.handlers.RotatingFileHandler(
	filename="console.log",
	encoding="utf-8")
	console_handler.setLevel(logging.DEBUG)

	commands_handler = logging.handlers.RotatingFileHandler(
	filename="commands.log",
	encoding="utf-8")
	commands_handler.setLevel(logging.DEBUG)
	
	formatter = TimezoneFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
	console_handler.setFormatter(formatter)
	commands_handler.setFormatter(formatter)
	
	console_logger.addHandler(console_handler)
	commands_logger.addHandler(commands_handler)

	return console_logger, commands_logger

console_logger, commands_logger = setup_logging()

# Pobieranie aktualnego czasu
def get_current_time():
	return datetime.now(TIMEZONE).strftime("%d-%m-%Y %H:%M:%S")

# Kalkulacja hashu
def calculate_hash_from_data(data):
	if isinstance(data, str):
		hash_input = data.strip()
	
	elif isinstance(data, list):
		hash_input = ""
		for title, entry_list in data:
			hash_input += title.strip() + "".join(entry.strip() for entry in entry_list)

	elif isinstance(data, dict):
		hash_input = ""
		for key, value in data.items():
			hash_input += key.strip() + "".join(entry.strip() for entry in value)

	else:
		hash_input = str(data)

	return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

# Obsługa konfiguracji
def load_config():
	if not os.path.exists("config.json"):
		console_logger.error("Brak pliku konfiguracyjnego.")
		exit(1)
	try:
		with open("config.json", "r") as file:
			config = json.load(file)
			for guild_id in config.get("allowed_guilds", []):
				config.setdefault("guilds", {}).setdefault(str(guild_id), {"channel_id": None, "selected_classes": []})
			return config
	except json.JSONDecodeError as e:
		console_logger.error(f"Błąd podczas wczytywania pliku konfiguracyjnego: {e}")
		exit(1)

# Zmienne globalne
config = load_config()
guild_config = config.get("guilds", {})

# Zapisanie konfiguracji
def save_config(config):
	try:
		with open("config.json", "w") as f:
			json.dump(config, f, indent=4)
	except IOError as e:
		console_logger.error(f"Błąd podczas zapisywania pliku konfiguracyjnego: {e}")

# Pobieranie i przetwarzanie danych z witryny
def fetch_website_content(url):
	console_logger.info(f"Pobieranie URL: {url}")
	try:
		response = requests.get(url, timeout=10)
		response.raise_for_status()
		response.encoding = ENCODING 
		return BeautifulSoup(response.text, "html.parser")
	except requests.Timeout as e:
		console_logger.warning(f"Przekroczono czas oczekiwania na połączenie. Więcej informacji: {e}")
	except requests.RequestException as e:
		console_logger.error(f"Nie udało się pobrać URL: {e}")
	return None

def extract_data_from_html(soup, filter_classes, classes_by_grade):
	if soup is None:
		console_logger.warning("Brak treści pobranej ze strony.")
		return "", [], {}

	try:
		entries = []
		additional_info = ""
		rows = soup.find_all("tr")

		# Ekstrakcja dodatkowych informacji
		additional_info_cell = next((cell for row in rows for cell in row.find_all("td") if cell.get("class") == ["st0"]), None)
		if additional_info_cell:
			link_tag = additional_info_cell.find("a")
			if link_tag and link_tag.get("href"):
				link_text = link_tag.get_text(strip=True)
				link_url = link_tag["href"]
				additional_info_text = additional_info_cell.get_text(separator="\n", strip=True).replace(link_text, "").strip()
				additional_info = f"{additional_info_text}\n[{link_text}]({link_url})"
			else:
				additional_info = additional_info_cell.get_text(separator="\n", strip=True)

		current_title = None
		current_entries = []
		no_class_entries_by_teacher = {}

		for row in rows:
			cells = row.find_all("td")

			if len(cells) == 1:
				cell = cells[0]
				if cell.get("bgcolor") == TEACHERS_CELL_COLOR:
					if current_title and current_entries:
						entries.append((current_title, current_entries))
					current_title = cell.get_text(separator="\n", strip=True)
					current_entries = []
					continue
				if cell.get("class") == ["st0"]:
					continue

			# Wyodrębnianie danych zastępstw
			if len(cells) == 4:
				lekcja, opis, zastępca, uwagi = (cell.get_text(strip=True) for cell in cells)

				entry_lines = []
				if lekcja and lekcja != "lekcja":
					entry_lines.append(f"**Lekcja:** {lekcja}")
				elif len(entry_lines) > 0:
					entry_lines.append("**Lekcja:** Brak")
				if opis and opis != "opis":
					entry_lines.append(f"**Opis:** {opis}")
				elif len(entry_lines) > 0:
					entry_lines.append("**Opis:** Brak")
				if zastępca and zastępca != "zastępca":
					entry_lines.append(f"**Zastępca:** {zastępca}")
				elif len(entry_lines) > 0:
					entry_lines.append("**Zastępca:** Brak")
				if uwagi and uwagi != "uwagi":
					entry_lines.append(f"**Uwagi:** {uwagi}")
				elif len(entry_lines) > 0:
					entry_lines.append("**Uwagi:** Brak")

				entry_text = "\n".join(entry_lines).strip()
				if entry_text:
					if not filter_classes:
						current_entries.append(entry_text)
					else:
						if not any(cls in entry_text for grade_classes in classes_by_grade.values() for cls in grade_classes):
							if current_title not in no_class_entries_by_teacher:
								no_class_entries_by_teacher[current_title] = []
							no_class_entries_by_teacher[current_title].append(entry_text)
						elif any(cls in entry_text for cls in filter_classes):
							current_entries.append(entry_text)

		if current_title and current_entries:
			entries.append((current_title, current_entries))

		console_logger.info(f"Wyodrębniono {len(entries)} wpis(ów) z przypisanymi klasami.")
		console_logger.info(f"Wyodrębniono {len(no_class_entries_by_teacher)} wpis(ów) bez przypisanych klas.")
		return additional_info, entries, no_class_entries_by_teacher
	except Exception as e:
		console_logger.error(f"Błąd podczas przetwarzania HTML: {e}")
		return "", [], {}

# Obsługa plików danych
def manage_data_file(guild_id, data=None):
	file_path = f"previous_hash_{guild_id}.json"
	try:
		if data is not None:
			with open(file_path, "w", encoding="utf-8") as file:
				json.dump(data, file, ensure_ascii=False, indent=4)
		else:
			if os.path.exists(file_path):
				with open(file_path, "r", encoding="utf-8") as file:
					return json.load(file)
			return {}
	except IOError as e:
		console_logger.error(f"Błąd podczas operacji na pliku z danymi: {e}")
		return {}
	
# Główna klasa i logika
class BOT(commands.Bot):
	def __init__(self):
		intents = discord.Intents.default()
		intents.guilds = True
		intents.members = True 
		super().__init__(command_prefix="", intents=intents)
		self.start_time = None
	
	async def on_ready(self):
		console_logger.info(f"Zalogowano jako {self.user.name} ({self.user.id})")
		await self.tree.sync()
		self.loop.create_task(check_for_updates())
		self.start_time = datetime.now()
		
	def get_server_count(self):
		return len(self.guilds)

	def get_uptime(self):
		if self.start_time is None:
			return "Bot nie jest jeszcze gotowy."

		uptime_duration = datetime.now() - self.start_time
		days, remainder = divmod(uptime_duration.total_seconds(), 86400)
		hours, remainder = divmod(remainder, 3600)
		minutes, seconds = divmod(remainder, 60)

		return f"**{int(days)}**d, **{int(hours)}**h, **{int(minutes)}**m i **{int(seconds)}**s."

bot = BOT()

# Funkcja wysyłająca instrukcję administratorom serwera
@bot.event
async def on_guild_join(guild):
	admins = [member for member in guild.members if member.guild_permissions.administrator and not member.bot]
	for admin in admins:
		embed = discord.Embed(
			title="**Cześć! Nadszedł czas na skonfigurowanie bota!**",
			description=f"**Informacja wstępna:**\nBot został dodany do serwera **{guild.name}**, a z racji, że jesteś jego administratorem, to dostajesz tę wiadomość.\n\n**Ważne informacje:**\nNa początek musisz upewnić się, że serwer, do którego dołączył bot, jest dodany do listy dozwolonych serwerów. W razie wątpliwości czy serwer na takiej liście się znajduje, skontaktuj się z administratorem bota. Wszystkie ważne informacje dotyczące funkcjonalności bota oraz jego administratorów znajdziesz, używając komendy `/informacje`.\n\n> **Jeżeli znajdziesz lub doświadczysz jakiegokolwiek błędu, [utwórz issue]({GITHUB_ISSUES}). Jest to bardzo ważne dla prawidłowego funkcjonowania bota!**\n\n**Konfiguracja bota:**\nKonfiguracja bota zaczyna się od utworzenia dedykowanego kanału tekstowego, na który będą wysyłane zastępstwa, a następnie użycia komendy `/skonfiguruj`, gdzie zostaniesz przeprowadzony przez wygodny i prosty konfigurator. W razie jakichkolwiek pytań odsyłam również do issues na GitHubie.",
			color=EMBEDS_COLOR
		)
		embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

		try:
			await admin.send(embed=embed)
			console_logger.info(f"Wiadomość z instrukcjami została wysłana do {admin.name}, który jest administratorem na serwerze {guild.name}.")
		except discord.Forbidden as e:
			console_logger.error(f"Nie można wysłać wiadomości do {admin.name}, który jest administratorem na serwerze {guild.name}. Więcej informacji: {e}")

# Funkcja sprawdzająca aktualizacje
async def check_for_updates():
	await bot.wait_until_ready()
	while not bot.is_closed():
		current_time = get_current_time()
		for guild_id_str in config.get("allowed_guilds", []):
			guild_id = int(guild_id_str)
			channel_id = guild_config.get(str(guild_id), {}).get("channel_id")
			channel = bot.get_channel(int(channel_id))
			previous_data = manage_data_file(guild_id)
			
			if not channel_id:
				console_logger.warning(f"Nie ustawiono ID kanału dla serwera {guild_id}.")
				continue
			if not channel:
				console_logger.warning(f"Nie znaleziono kanału z ID {channel_id} dla serwera {guild_id}.")
				continue
			console_logger.info(f"Sprawdzanie aktualizacji dla serwera {guild_id}.")

			try:
				soup = fetch_website_content(URL)
				if soup is None:
					console_logger.warning("Nie udało się pobrać zawartości strony. Pomijanie aktualizacji.")
					continue

				filter_classes = guild_config.get(str(guild_id), {}).get("selected_classes", [])
				additional_info, current_entries, no_class_entries_by_teacher = extract_data_from_html(soup, filter_classes, classes_by_grade)

				# Kalkulacja hashu nowo pobranych danych
				current_additional_info_hash = calculate_hash_from_data(additional_info)
				current_entries_hash = calculate_hash_from_data(current_entries)
				current_no_class_entries_by_teacher_hash = calculate_hash_from_data(no_class_entries_by_teacher)

				# Pobieranie starego hashu z pliku danych
				previous_additional_info_hash = previous_data.get("additional_info_hash", "")
				previous_entries_hash = previous_data.get("entries_hash", "")
				previous_no_class_entries_by_teacher_hash = previous_data.get("no_class_entries_by_teacher_hash", "")

				# Porównywanie nowego hashu ze starym hashem
				additional_info_changed = current_additional_info_hash != previous_additional_info_hash
				entries_changed = current_entries_hash != previous_entries_hash
				no_class_entries_by_teacher_changed = current_no_class_entries_by_teacher_hash != previous_no_class_entries_by_teacher_hash

				if additional_info_changed or entries_changed or no_class_entries_by_teacher_changed:
					console_logger.info("Treść uległa zmianie. Wysyłam nowe aktualizacje.")
					try:
						if additional_info_changed and not entries_changed and not no_class_entries_by_teacher_changed:
							await send_updates(channel, additional_info, None, None, current_time)

						elif entries_changed or no_class_entries_by_teacher_changed:
							await send_updates(channel, additional_info, current_entries, no_class_entries_by_teacher, current_time)

						new_data = {
							"additional_info_hash": current_additional_info_hash,
							"entries_hash": current_entries_hash,
							"no_class_entries_by_teacher_hash": current_no_class_entries_by_teacher_hash
						}
						manage_data_file(guild_id, new_data)
					except discord.DiscordException as e:
						console_logger.error(f"Nie udało się wysłać wszystkich wiadomości, hash nie zostanie zaktualizowany. Więcej informacji: {e}")
				else:
					console_logger.info("Treść się nie zmieniła. Brak nowych aktualizacji.")

				await asyncio.sleep(random.uniform(10, 15))
			except Exception as e:
				console_logger.error(f"Błąd podczas przetwarzania aktualizacji: {e}")

		await asyncio.sleep(CHECK_INTERVAL)

# Funkcja wysyłająca aktualizacje
async def send_updates(channel, additional_info, current_entries, no_class_entries_by_teacher, current_time):
	description_only_for_additional_info = f"**Dodatkowe informacje zastępstw:**\n{additional_info}\n\n**Informacja o tej wiadomości:**\nW tej wiadomości znajdują się informacje dodatkowe, które zostały umieszczone przed zastępstwami. Nie znaleziono dla twojej klasy żadnych zastępstw, więc nie dostaniesz powiadomienia."
	description_for_additional_info = f"**Dodatkowe informacje zastępstw:**\n{additional_info}\n\n**Informacja o tej wiadomości:**\nW tej wiadomości znajdują się informacje dodatkowe, które zostały umieszczone przed zastępstwami. Wszystkie zastępstwa znajdują się pod tą wiadomością."
	description_for_entries = "\n### Informacja o tej wiadomości:\nTe zastępstwa nie posiadają dołączonej klasy, więc zweryfikuj czy przypadkiem nie dotyczą one Ciebie!"

	try:
		last_message = None
		if additional_info and not current_entries and not no_class_entries_by_teacher:
			embed = discord.Embed(
				title="**Zastępstwa zostały zaktualizowane!**",
				description=description_only_for_additional_info,
				color=EMBEDS_COLOR
			)
			embed.set_footer(text=f"Czas aktualizacji: {current_time}\nStworzone z ❤️ przez Kacpra Górkę!")
			await channel.send(embed=embed)

		elif (additional_info and no_class_entries_by_teacher and not current_entries) or (no_class_entries_by_teacher and not current_entries):
			ping_message = "@everyone Zastępstwa zostały zaktualizowane!"
			ping_msg = await channel.send(ping_message)
			await asyncio.sleep(5)
			await ping_msg.delete()

			embed = discord.Embed(
				title="**Zastępstwa zostały zaktualizowane!**",
				description=description_for_additional_info,
				color=EMBEDS_COLOR
			)
			embed.set_footer(text=f"Czas aktualizacji: {current_time}\nStworzone z ❤️ przez Kacpra Górkę!")
			await channel.send(embed=embed)

			for teacher, entries in no_class_entries_by_teacher.items():
				embed = discord.Embed(
					title=f"**{teacher} - Zastępstwa z nieprzypisanymi klasami! (:exclamation:)**",
					description="\n\n".join(entries) + description_for_entries,
					color=EMBEDS_COLOR
				)
				embed.set_footer(text="Każdy kolejny nauczyciel, za którego wpisywane są zastępstwa, jest załączany w oddzielnej wiadomości.")
				await channel.send(embed=embed)

		elif (additional_info and current_entries) or (current_entries):
			ping_message = "@everyone Zastępstwa zostały zaktualizowane!"
			ping_msg = await channel.send(ping_message)
			await asyncio.sleep(5)
			await ping_msg.delete()

			embed = discord.Embed(
				title="**Zastępstwa zostały zaktualizowane!**",
				description=description_for_additional_info,
				color=EMBEDS_COLOR
			)
			embed.set_footer(text=f"Czas aktualizacji: {current_time}\nStworzone z ❤️ przez Kacpra Górkę!")
			await channel.send(embed=embed)

			if no_class_entries_by_teacher:
				for teacher, entries in no_class_entries_by_teacher.items():
					embed = discord.Embed(
						title=f"**{teacher} - Zastępstwa z nieprzypisanymi klasami! (:exclamation:)**",
						description="\n\n".join(entries) + description_for_entries,
						color=EMBEDS_COLOR
					)
					embed.set_footer(text="Każdy kolejny nauczyciel, za którego wpisywane są zastępstwa, jest załączany w oddzielnej wiadomości.")
					await channel.send(embed=embed)

			for title, entries in current_entries:
				embed = discord.Embed(
					title=f"**{title}**",
					description="\n\n".join(entries),
					color=EMBEDS_COLOR
				)
				embed.set_footer(text="Każdy kolejny nauczyciel, za którego wpisywane są zastępstwa, jest załączany w oddzielnej wiadomości.")
				last_message = await channel.send(embed=embed)

		if last_message:
			await last_message.add_reaction("❤️")

	except discord.DiscordException as e:
		console_logger.error(f"Błąd podczas wysyłania wiadomości: {e}")
		raise

# Logowanie komend
def log_command(interaction: discord.Interaction, success: bool, error_message: str = None):
	status = "pomyślnie" if success else "niepomyślnie"
	error_info = f" ({error_message})" if error_message else ""
	log_message = (
		f"Użytkownik: {interaction.user} (ID: {interaction.user.id}) "
		f"użył komendy '{interaction.command.name}' "
		f"w serwerze '{interaction.guild.name}' (ID: {interaction.guild.id}) "
		f"na kanale '{interaction.channel.name}' (ID: {interaction.channel.id}). "
		f"Komenda wykonana {status}.{error_info}"
	)
	commands_logger.info(log_message)

# /skonfiguruj
class ClassGroupSelect(discord.ui.Select):
	def __init__(self, classes_by_grade):
		options = [
			discord.SelectOption(label="Klasy pierwsze", value="1", description="Wybierz kategorię z klasami pierwszymi"),
			discord.SelectOption(label="Klasy drugie", value="2", description="Wybierz kategorię z klasami drugimi"),
			discord.SelectOption(label="Klasy trzecie", value="3", description="Wybierz kategorię z klasami trzecimi"),
			discord.SelectOption(label="Klasy czwarte", value="4", description="Wybierz kategorię z klasami czwartymi"),
			discord.SelectOption(label="Klasy piąte", value="5", description="Wybierz kategorię z klasami piątymi"),
		]
		super().__init__(placeholder="Wybierz kategorie", min_values=1, max_values=3, options=options)
		self.classes_by_grade = classes_by_grade

	async def callback(self, interaction: discord.Interaction):
		all_classes = []
		for grade in self.values:
			all_classes.extend(self.classes_by_grade.get(grade, []))
		
		view = ClassDetailView(all_classes)
		embed = discord.Embed(
			title="**Dalsza konfiguracja**",
			description="Teraz wybierz klasy, których zastępstwa mają być wysyłane na wybrany przez ciebie kanał.",
			color=EMBEDS_COLOR
			)
		embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

		await interaction.response.edit_message(
			embed=embed,
			view=view
			)

class ClassDetailSelect(discord.ui.Select):
	def __init__(self, classes):
		options = [discord.SelectOption(label=cls, value=cls) for cls in classes]
		super().__init__(placeholder="Wybierz klasy", min_values=1, max_values=len(classes), options=options)

	async def callback(self, interaction: discord.Interaction):
		guild_id = str(interaction.guild.id)
		channel_id = guild_config.get(guild_id, {}).get("channel_id")
		
		if guild_id not in guild_config:
			guild_config[guild_id] = {}
		guild_config[guild_id]["selected_classes"] = self.values
		save_config(config)

		embed = discord.Embed(title="**Podsumowanie Twoich wyborów**", color=EMBEDS_COLOR)
		if channel_id:
			channel = interaction.guild.get_channel(int(channel_id))
			embed.add_field(name="Wybrany kanał:", value=channel.mention if channel else "**Nie znaleziono kanału**")
		else:
			embed.add_field(name="Wybrany kanał:", value="**Brak**")

		classes_summary = ", ".join(f"**{cls}**" for cls in self.values) if self.values else "**Brak**"
		embed.add_field(name="Wybrane klasy:", value=classes_summary)
		embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

		await interaction.response.edit_message(
			embed=embed,
			view=None
		)

class ClassDetailView(discord.ui.View):
	def __init__(self, classes):
		super().__init__()
		self.add_item(ClassDetailSelect(classes))

class ClearFilterButton(discord.ui.Button):
	def __init__(self):
		super().__init__(label="Wysyłaj wszystkie zastępstwa", style=discord.ButtonStyle.secondary)

	async def callback(self, interaction: discord.Interaction):
		guild_id = str(interaction.guild.id)
		if guild_id in guild_config:
			guild_config[guild_id].pop("selected_classes", None)
			save_config(config)

		embed = discord.Embed(title="**Podsumowanie Twoich wyborów**", color=EMBEDS_COLOR)
		if "channel_id" in guild_config.get(guild_id, {}):
			channel_id = guild_config[guild_id]["channel_id"]
			channel = interaction.guild.get_channel(int(channel_id))
			embed.add_field(name="Wybrany kanał:", value=channel.mention if channel else "**Nie znaleziono kanału**")
		else:
			embed.add_field(name="Wybrany kanał:", value="**Brak**")

		embed.add_field(name="Wybrane klasy:", value="**Wszystkie**")
		embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

		await interaction.response.edit_message(
			embed=embed,
			view=None
		)

class ClassView(discord.ui.View):
	def __init__(self, classes_by_grade):
		super().__init__()
		self.add_item(ClassGroupSelect(classes_by_grade))
		self.add_item(ClearFilterButton())

@bot.tree.command(name="skonfiguruj", description="Skonfiguruj bota, który będzie informował o aktualizacji zastępstw.")
@app_commands.describe(channel="Kanał, na który będą wysyłane aktualizacje zastępstw.")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
	try:
		if not interaction.user.guild_permissions.administrator:
			embed = discord.Embed(
				title="**Polecenie nie zostało wykonane!**",
				description="Nie masz uprawnień do używania tej komendy, komendę tą może użyć wyłącznie administrator serwera. Jeżeli uważasz, że wystąpił błąd, skontaktuj się z administratorem bota. Wszystkie potrzebne informacje znajdziesz, używając komendy `/informacje`.",
				color=EMBEDS_COLOR
				)
			embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

			await interaction.response.send_message(embed=embed)
			log_command(interaction, success=False, error_message="Brak uprawnień.")
			return

		if str(interaction.guild.id) not in config.get("allowed_guilds", []):
			embed = discord.Embed(
				title="**Polecenie nie zostało wykonane!**",
				description="Nie masz uprawnień do używania tej komendy na tym serwerze, skontaktuj się z administratorem bota. Wszystkie potrzebne informacje znajdziesz, używając komendy `/informacje`.",
				color=EMBEDS_COLOR
				)
			embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

			await interaction.response.send_message(embed=embed)
			log_command(interaction, success=False, error_message="Ten serwer nie znajduje się na liście dozwolonych serwerów.")
			return

		guild_config.setdefault(str(interaction.guild.id), {})["channel_id"] = str(channel.id)
		save_config(config)

		view = ClassView(classes_by_grade)
		embed = discord.Embed(
			title="**Ważna informacja! (:exclamation:)**",
			description="Teraz musisz dokonać wyboru, czy chcesz dostawać zastępstwa dla wszystkich klas, czy może dla klas wybranych przez Ciebie. Jeżeli postanowiłeś, że chcesz wybrać niestandardowe klasy, wybierz kategorie z ich przedziałem, w przeciwnym razie naciśnij przycisk.",
			color=EMBEDS_COLOR
			)
		embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

		await interaction.response.send_message(
			embed=embed,
			view=view
			)
		log_command(interaction, success=True)
		
	except Exception as e:
		log_command(interaction, success=False, error_message=str(e))
		await interaction.response.send_message(f"Wystąpił błąd: {str(e)}", ephemeral=True)
		raise

# /zarządzaj
@bot.tree.command(name="zarządzaj", description="Dodaj lub usuń serwer z listy dozwolonych serwerów.")
@app_commands.describe(dodaj_id="ID serwera, który chcesz dodać do listy dozwolonych serwerów.", usun_id="ID serwera, który chcesz usunąć z listy dozwolonych serwerów.")
async def add_or_remove_server(interaction: discord.Interaction, dodaj_id: str = None, usun_id: str = None):
	try:
		# Sprawdza, czy użytkownik jest na liście dozwolonych użytkowników
		if str(interaction.user.id) not in config.get("allowed_users", []):
			embed = discord.Embed(
				title="**Polecenie nie zostało wykonane!**",
				description="Nie masz uprawnień do używania tej komendy, tej komendy może użyć wyłącznie uprawniona osoba. Jeżeli jesteś administartorem serwera i chcesz skonfigurować bota, użyj komendy `/skonfiguruj`. Jeżeli uważasz, że wystąpił błąd, skontaktuj się z administratorem bota. Wszystkie potrzebne informacje znajdziesz, używając komendy `/informacje`.",
				color=EMBEDS_COLOR
				)
			embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

			await interaction.response.send_message(embed=embed)
			log_command(interaction, success=False, error_message="Brak uprawnień.")
			return

		# Sprawdza, czy podano obie opcje
		if dodaj_id and usun_id:
			embed = discord.Embed(
				title="**Polecenie nie zostało wykonane!**",
				description="Wykonana operacja jest niepoprawna. Możesz wybrać tylko jedną z obu dostępnych opcji.",
				color=EMBEDS_COLOR
				)
			embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

			await interaction.response.send_message(embed=embed)
			log_command(interaction, success=False, error_message="Wybrano obie opcje w jednej komendzie.")
			return

		# Sprawdza, czy przynajmniej jedna opcja została podana
		if not dodaj_id and not usun_id:
			embed = discord.Embed(
				title="**Polecenie nie zostało wykonane!**",
				description="Wykonana operacja jest niepoprawna. Musisz wybrać co najmniej jedną z obu dostępnych opcji.",
				color=EMBEDS_COLOR
				)
			embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

			await interaction.response.send_message(embed=embed)
			log_command(interaction, success=False, error_message="Nie wybrano żadnej z obu opcji.")
			return

		# Sprawdza, czy ID serwera to tylko cyfry
		guild_id = dodaj_id or usun_id
		if not guild_id.isdigit():
			embed = discord.Embed(
				title="**Polecenie nie zostało wykonane!**",
				description=f"Podane ID serwera (`{guild_id}`) jest nieprawidłowe. ID serwera musi składać się wyłącznie z cyfr.",
				color=EMBEDS_COLOR
				)
			embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

			await interaction.response.send_message(embed=embed)
			log_command(interaction, success=False, error_message="Nieprawidłowe ID serwera.")
			return

		# Obsługa dodania ID serwera
		if dodaj_id and not usun_id:
			if dodaj_id in config.get("allowed_guilds", []):
				embed = discord.Embed(
					title="**Polecenie nie zostało wykonane!**",
					description="Wykonana operacja jest niepoprawna. Ten serwer znajduję się już na liście dozwolonych serwerów.",
					color=EMBEDS_COLOR
					)
				embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

				await interaction.response.send_message(embed=embed)
				log_command(interaction, success=False, error_message="Ten serwer znajduję się już na liście dozwolonych serwerów.")
			else:
				config["allowed_guilds"].append(dodaj_id)
				config["guilds"][dodaj_id] = {"channel_id": None, "selected_classes": []}
				save_config(config)

				embed = discord.Embed(
					title="**Polecenie wykonane pomyślnie!**",
					description=f"Serwer o ID `{dodaj_id}` został pomyślnie dodany do listy dozwolonych serwerów.",
					color=EMBEDS_COLOR
					)
				embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

				await interaction.response.send_message(embed=embed)
				log_command(interaction, success=True)

		# Obsługa usunięcia ID serwera
		if usun_id and not dodaj_id:
			if usun_id not in config.get("allowed_guilds", []):
				embed = discord.Embed(
					title="**Polecenie nie zostało wykonane!**",
					description="Wykonana operacja jest niepoprawna. Ten serwer nie znajduje się na liście dozwolonych serwerów.",
					color=EMBEDS_COLOR
					)
				embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

				await interaction.response.send_message(embed=embed)
				log_command(interaction, success=False, error_message="Ten serwer nie znajduje się na liście dozwolonych serwerów.")
			else:
				config["allowed_guilds"].remove(usun_id)
				config["guilds"].pop(usun_id, None)
				save_config(config)

				embed = discord.Embed(
					title="**Polecenie wykonane pomyślnie!**",
					description=f"Serwer o ID `{usun_id}` został pomyślnie usunięty z listy dozwolonych serwerów.",
					color=EMBEDS_COLOR
					)
				embed.set_footer(text="Stworzone z ❤️ przez Kacpra Górkę!")

				await interaction.response.send_message(embed=embed)
				log_command(interaction, success=True)

	except Exception as e:
		log_command(interaction, success=False, error_message=str(e))
		await interaction.response.send_message(f"Wystąpił błąd: {str(e)}", ephemeral=True)
		raise

# /informacje
@bot.tree.command(name="informacje", description="Wyświetl najważniejsze informacje dotyczące bota.")
async def informacje(interaction: discord.Interaction):
	try:
		embed = discord.Embed(
			title="**Informacje dotyczące bota**",
			description="Otwarto źródłowe oprogramowanie Informujące o aktualizacji zastępstw. Aby skontaktować się z administratorem bota, wystarczy, że klikniesz jednego z nich.",
			color=EMBEDS_COLOR
		)
		embed.add_field(name="Wersja bota:", value=BOT_VERSION)
		embed.add_field(name="Repozytorium GitHuba:", value=(f"[{SHORT_GITHUB_REPOSITORY}]({GITHUB_REPOSITORY})"))
		embed.add_field(name="Administratorzy bota:", value=BOT_ADMINISTRATORS)
		embed.add_field(name="Ilość serwerów:", value=(f"Bot znajduję się na **{bot.get_server_count()}** serwerach."))
		embed.add_field(name="Bot pracuje bez przerwy przez:", value=bot.get_uptime())
		if str(interaction.guild.id) in config.get("allowed_guilds", []):
			embed.add_field(name="Czy ten serwer jest dozwolony?", value=("Tak, jest."))
		else:
			embed.add_field(name="Czy ten serwer jest dozwolony?", value=("Nie, nie jest."))
		embed.set_footer(text="Projekt ten licencjonowany jest na podstawie licencji MIT. Stworzone z ❤️ przez Kacpra Górkę!")

		await interaction.response.send_message(embed=embed)
		log_command(interaction, success=True)
	except Exception as e:
		log_command(interaction, success=False, error_message=str(e))
		await interaction.response.send_message(f"Wystąpił błąd: {str(e)}", ephemeral=True)
		raise

# Uruchomienie bota
if not config.get("token"):
	console_logger.error("Brak tokena bota. Ustaw TOKEN w pliku konfiguracyjnym.")
	exit(1)
bot.run(config.get("token"))