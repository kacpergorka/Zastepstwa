import discord
from discord.ext import commands
from discord import app_commands
import requests
from bs4 import BeautifulSoup
import json
import os
import asyncio
import logging
from datetime import datetime
import pytz
import random
import hashlib

BOT_VERSION = "0.4.4"

# Czas i strefa czasowa
TIMEZONE = pytz.timezone("Europe/Warsaw") # Twoja strefa czasowa
def get_current_time():
	return datetime.now(TIMEZONE).strftime('%d-%m-%Y %H:%M:%S')

class TimezoneFormatter(logging.Formatter):
	def formatTime(self, record, datefmt=None):
		return get_current_time()

console_logger = logging.getLogger('discord')
console_logger.setLevel(logging.INFO)
command_logger = logging.getLogger('discord.commands')
command_logger.setLevel(logging.INFO)

console_handler = logging.FileHandler('console.log', encoding='utf-8')
console_handler.setLevel(logging.INFO)
command_handler = logging.FileHandler('commands.log', encoding='utf-8')
command_handler.setLevel(logging.INFO)

console_formatter = TimezoneFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
command_formatter = TimezoneFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
command_handler.setFormatter(command_formatter)

console_logger.addHandler(console_handler)
command_logger.addHandler(command_handler)

console_logger.propagate = False
command_logger.propagate = False

# Funkcje odpowiadające za hash
def calculate_hash_from_data(additional_info, entries):
	hash_input = additional_info.strip()	
	for title, entry_list in entries:
		hash_input += title.strip() + ''.join(entry.strip() for entry in entry_list)
	return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

# Załadowanie konfiguracji
def load_config():
	if not os.path.exists('config.json'):
		console_logger.error('Brak pliku konfiguracyjnego.')
		exit(1)
	try:
		with open('config.json') as f:
			config = json.load(f)
			for guild_id in config.get('allowed_guilds', []):
				config.setdefault('guilds', {})[str(guild_id)] = config.get('guilds', {}).get(str(guild_id), {'channel_id': None, 'selected_classes': []})
			return config
	except json.JSONDecodeError as e:
		console_logger.error(f"Błąd podczas wczytywania pliku konfiguracyjnego: {e}")
		exit(1)

# Zapisanie konfiguracji
def save_config(config):
	try:
		with open('config.json', 'w') as f:
			json.dump(config, f, indent=4)
	except IOError as e:
		console_logger.error(f"Błąd podczas zapisywania pliku konfiguracyjnego: {e}")

config = load_config()
TOKEN = config.get('token')
if not TOKEN:
	console_logger.error("Brak tokena bota. Ustaw TOKEN w pliku konfiguracyjnym.")
	exit(1)
GUILD_CONFIG = config.get('guilds', {})
CHECK_INTERVAL = 300 # Czas (w sekundach), jaki bot wyczekuje, by pobrać zawartość strony
URL = 'https://zastepstwa.zse.bydgoszcz.pl/' # link do strony, z której pobierane są informacje
allowed_users = config.get('allowed_users', [])

intents = discord.Intents.default()
intents.message_content = False
intents.guilds = True
intents.messages = False

# Klasa bota
class BOT(commands.Bot):
	def __init__(self):
		super().__init__(command_prefix="!", intents=intents)
	
	async def on_ready(self):
		console_logger.info(f'Zalogowano jako {self.user.name} ({self.user.id})')
		await self.tree.sync()
		console_logger.info("komendy zsynchronizowane.")
		self.loop.create_task(check_for_updates())

bot = BOT()

# Pobieranie zawartości witryny
def fetch_website_content(url):
	console_logger.info(f"Pobieranie URL: {url}")
	try:
		response = requests.get(url, timeout=10)
		response.raise_for_status()
		response.encoding = 'iso-8859-2' # kodowanie strony, z której pobierane są informacje
		return BeautifulSoup(response.text, 'html.parser')
	except requests.Timeout:
		console_logger.error("Przekroczono czas oczekiwania na połączenie.")
	except requests.RequestException as e:
		console_logger.error(f"Nie udało się pobrać URL: {e}")
	return None

# Wyodrębnienie danych z html
def extract_data_from_html(soup, filter_classes, classes_by_grade):
	if soup is None:
		console_logger.error("Brak treści pobranej ze strony.")
		return "", [], {}

	try:
		console_logger.info("Ekstrakcja informacji z HTML.")
		entries = []
		additional_info = ""
		rows = soup.find_all('tr')

		additional_info_cell = next((cell for row in rows for cell in row.find_all('td') if cell.get('class') == ['st0']), None)
		if additional_info_cell:
			additional_info = additional_info_cell.get_text(separator='\n', strip=True)

		current_title = None
		current_entries = []
		no_class_entries_by_teacher = {}

		for row in rows:
			cells = row.find_all('td')

			if len(cells) == 1:
				cell = cells[0]
				if cell.get('bgcolor') == '#69AADE': # W przypadku strony z zastępstwami mojej szkoły, nauczyciel, za którego są zastępstwa, znajduje się w komórce z kolorem #69AADE, więc kiedy bot wykryje ową komórkę, to wczytuje jej zawartość w tytuł embeda, który wysyła podczas aktualizacji. Domyślnie VULCAN ustawia kolor tej komórki na #FFDFBF.
					if current_title and current_entries:
						entries.append((current_title, current_entries))
					current_title = cell.get_text(separator='\n', strip=True)
					current_entries = []
					continue
				if cell.get('class') == ['st0']:
					continue

			if len(cells) == 4:
				lekcja, opis, zastępca, uwagi = (cell.get_text(strip=True) for cell in cells)

				entry_lines = []
				if lekcja and lekcja != 'lekcja':
					entry_lines.append(f"**Lekcja:** {lekcja}")
				if opis and opis != 'opis':
					entry_lines.append(f"**Opis:** {opis}")
				if zastępca and zastępca != 'zastępca':
					entry_lines.append(f"**Zastępca:** {zastępca}")
				elif len(entry_lines) > 0:
					entry_lines.append("**Zastępca:** Brak")
				if uwagi and uwagi != 'uwagi':
					entry_lines.append(f"**Uwagi:** {uwagi}")
				elif len(entry_lines) > 0:
					entry_lines.append("**Uwagi:** Brak")

				entry_text = '\n'.join(entry_lines).strip()

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

# Zarządzanie plikiem danych
def manage_data_file(guild_id, data=None):
	file_path = f'previous_hash_{guild_id}.json'
	try:
		if data is not None:
			with open(file_path, 'w', encoding='utf-8') as file:
				json.dump(data, file, ensure_ascii=False, indent=4)
		else:
			if os.path.exists(file_path):
				with open(file_path, 'r', encoding='utf-8') as file:
					return json.load(file)
			return {}
	except IOError as e:
		console_logger.error(f"Błąd podczas operacji na pliku z danymi: {e}")
		return {}

# Sprawdzanie aktualizacji
async def check_for_updates():
	await bot.wait_until_ready()

	while not bot.is_closed():
		current_time = get_current_time()
		for guild_id_str in config.get('allowed_guilds', []):
			guild_id = int(guild_id_str)
			channel_id = GUILD_CONFIG.get(str(guild_id), {}).get('channel_id')

			if not channel_id:
				console_logger.error(f"Nie ustawiono ID kanału dla serwera {guild_id}.")
				continue

			channel = bot.get_channel(int(channel_id))
			if not channel:
				console_logger.error(f"Nie znaleziono kanału z ID {channel_id} dla serwera {guild_id}.")
				continue

			console_logger.info(f"Sprawdzanie aktualizacji dla serwera {guild_id}.")

			try:
				soup = fetch_website_content(URL)
				if soup is None:
					console_logger.error("Nie udało się pobrać zawartości strony. Pomijanie aktualizacji.")
					continue

				filter_classes = GUILD_CONFIG.get(str(guild_id), {}).get('selected_classes', [])
				additional_info, current_entries, no_class_entries_by_teacher = extract_data_from_html(soup, filter_classes, classes_by_grade)

				previous_data = manage_data_file(guild_id)
				current_hash = calculate_hash_from_data(additional_info, current_entries)
				previous_hash = previous_data.get('hash', '')

				if current_hash != previous_hash:
					console_logger.info("Treść uległa zmianie. Wysyłam nowe aktualizacje.")

					try:
						await send_updates(channel, additional_info, current_entries, no_class_entries_by_teacher, current_time)
						
						new_data = {'hash': current_hash}
						manage_data_file(guild_id, new_data)
					except discord.DiscordException:
						console_logger.error("Nie udało się wysłać wszystkich wiadomości, hash nie zostanie zaktualizowany.")

				else:
					console_logger.info("Treść się nie zmieniła. Brak nowych aktualizacji.")

				await asyncio.sleep(random.uniform(10, 15))
			except Exception as e:
				console_logger.error(f"Błąd podczas przetwarzania aktualizacji: {e}")

		await asyncio.sleep(CHECK_INTERVAL)

async def send_updates(channel, additional_info, current_entries, no_class_entries_by_teacher, current_time):
	try:
		last_message = None

		if additional_info:
			ping_message = "@everyone Zastępstwa zostały zaktualizowane!"
			ping_msg = await channel.send(ping_message)
			console_logger.info("Wiadomość ping wysłana pomyślnie.")
			await asyncio.sleep(2)
			await ping_msg.delete()
			console_logger.info("Wiadomość ping została usunięta.")

			embed = discord.Embed(
				title="**Zastępstwa zostały zaktualizowane!**",
				description=additional_info,
				color=0xca4449
			)
			embed.set_footer(text=f"Czas aktualizacji: {current_time}\nJeżeli widzisz jedynie tę wiadomość, oznacza to, że dla twojej klasy nie ma żadnych zastępstw.")
			last_message = await channel.send(embed=embed)
			console_logger.info("Wiadomość embed z dodatkowymi informacjami wysłana pomyślnie.")

		for title, entries in current_entries:
			embed = discord.Embed(
				title=title,
				description='\n\n'.join(entries),
				color=0xca4449
			)
			embed.set_footer(text=f"Czas aktualizacji: {current_time}\nKażdy nauczyciel, za którego wpisywane są zastępstwa, jest wysyłany w oddzielnej wiadomości.")
			last_message = await channel.send(embed=embed)
			console_logger.info("Wiadomość embed wysłana pomyślnie.")

		if no_class_entries_by_teacher:
			for teacher, entries in no_class_entries_by_teacher.items():
				embed = discord.Embed(
					title=f"{teacher} - **Zastępstwa z nieprzypisanymi klasami!**",
					description='\n\n'.join(entries),
					color=0xca4449
				)
				embed.set_footer(text=f"Czas aktualizacji: {current_time}\nKażdy nauczyciel, za którego wpisywane są zastępstwa, jest wysyłany w oddzielnej wiadomości.")
				last_message = await channel.send(embed=embed)
				console_logger.info("Wiadomość embed z nieprzypisanymi klasami wysłana pomyślnie.")

		if last_message:
			await last_message.add_reaction('❤️')

	except discord.DiscordException as e:
		console_logger.error(f"Błąd podczas wysyłania wiadomości: {e}")
		raise

# Logowanie komend
def log_command(interaction: discord.Interaction, success: bool, error_message: str = None):
	user_id = interaction.user.id
	guild_id = interaction.guild.id
	channel_id = interaction.channel.id
	command_name = interaction.command.name
	
	status = "pomyślnie" if success else "nieudanie"
	error_info = f" Powód: {error_message}" if error_message else ""
	
	log_message = (
		f"[{get_current_time()}] "
		f"Użytkownik: {interaction.user} (ID: {user_id}) "
		f"użył komendy '{command_name}' "
		f"w serwerze '{interaction.guild.name}' (ID: {guild_id}) "
		f"na kanale '{interaction.channel.name}' (ID: {channel_id}). "
		f"Komenda wykonana {status}.{error_info}\n"
	)
	
	command_logger.info(log_message)

# /skonfiguruj
def load_config():
	if os.path.exists('config.json'):
		with open('config.json', 'r') as file:
			return json.load(file)
	return {}

def save_config(config):
	with open('config.json', 'w') as file:
		json.dump(config, file, indent=4)

config = load_config()
GUILD_CONFIG = config.get('guilds', {})

class ClassGroupSelect(discord.ui.Select):
	def __init__(self, classes_by_grade):
		options = [
			discord.SelectOption(label="Klasy pierwsze", value="1", description="Wybierz z klas pierwszych"),
			discord.SelectOption(label="Klasy drugie", value="2", description="Wybierz z klas drugich"),
			discord.SelectOption(label="Klasy trzecie", value="3", description="Wybierz z klas trzecich"),
			discord.SelectOption(label="Klasy czwarte", value="4", description="Wybierz z klas czwartych"),
			discord.SelectOption(label="Klasy piąte", value="5", description="Wybierz z klas piątych"),
		]
		super().__init__(placeholder="Wybierz opcje", min_values=1, max_values=3, options=options)
		self.classes_by_grade = classes_by_grade

	async def callback(self, interaction: discord.Interaction):
		selected_grades = self.values
		all_classes = []
		for grade in selected_grades:
			all_classes.extend(self.classes_by_grade.get(grade, []))
		
		view = ClassDetailView(all_classes)
		await interaction.response.edit_message(
			content="**Wybierz klasy, których zastępstwa będą wysyłane.**",
			view=view
		)

class ClassDetailSelect(discord.ui.Select):
	def __init__(self, classes):
		options = [discord.SelectOption(label=cls, value=cls) for cls in classes]
		super().__init__(placeholder="Wybierz opcje", min_values=1, max_values=len(classes), options=options)

	async def callback(self, interaction: discord.Interaction):
		selected_classes = self.values
		guild_id = str(interaction.guild.id)
		channel_id = GUILD_CONFIG.get(guild_id, {}).get('channel_id')
		
		if guild_id not in GUILD_CONFIG:
			GUILD_CONFIG[guild_id] = {}
		GUILD_CONFIG[guild_id]['selected_classes'] = selected_classes
		save_config(config)

		embed = discord.Embed(title="**Podsumowanie wyborów**", color=0xca4449)
		if channel_id:
			channel = interaction.guild.get_channel(int(channel_id))
			embed.add_field(name="Wybrany kanał:", value=channel.mention if channel else "**Nie znaleziono kanału**")
		else:
			embed.add_field(name="Wybrany kanał:", value="Brak")

		classes_summary = ', '.join(f"**{cls}**" for cls in selected_classes) if selected_classes else "**Brak**"
		classes_summary_footer = ', '.join(f"{cls}" for cls in selected_classes) if selected_classes else "Brak"
		embed.add_field(name="Wybrane klasy:", value=classes_summary)

		embed.set_footer(text=f"Będziesz otrzymywać zastępstwa tylko dla klas: {classes_summary_footer}.")

		await interaction.response.edit_message(
			content="",
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
		if guild_id in GUILD_CONFIG:
			GUILD_CONFIG[guild_id].pop('selected_classes', None)
			save_config(config)

		embed = discord.Embed(title="**Podsumowanie wyborów**", color=0xca4449)
		if 'channel_id' in GUILD_CONFIG.get(guild_id, {}):
			channel_id = GUILD_CONFIG[guild_id]['channel_id']
			channel = interaction.guild.get_channel(int(channel_id))
			embed.add_field(name="Wybrany kanał:", value=channel.mention if channel else "**Nie znaleziono kanału**")
		else:
			embed.add_field(name="Wybrany kanał:", value="**Brak**")

		embed.add_field(name="Wybrane klasy:", value="**Brak**")

		embed.set_footer(text=f"Będziesz otrzymywać zastępstwa wszystkich klas.")

		await interaction.response.edit_message(
			content="",
			embed=embed,
			view=None
		)

class ClassView(discord.ui.View):
	def __init__(self, classes_by_grade):
		super().__init__()
		self.add_item(ClassGroupSelect(classes_by_grade))
		self.add_item(ClearFilterButton())

# Tutaj znajdują się klasy, które filtruje bot. Klasy tutaj wprowadzone można zmienić pod własne zapotrzebowania
classes_by_grade = {
	"1": ["1 A", "1 D", "1 F", "1 H"],
	"2": ["2 A", "2 B", "2 D", "2 E", "2 F", "2 H", "2 I", "2 J"],
	"3": ["3 A", "3 B", "3 D", "3 E", "3 F", "3 H", "3 I", "3 J"],
	"4": ["4 A", "4 B", "4 D", "4 E", "4 F", "4 H", "4 I"],
	"5": ["5 A", "5 B", "5 D", "5 E", "5 F", "5 H", "5 I"],
}

@bot.tree.command(name='skonfiguruj', description='Skonfiguruj bota, który będzie informował o aktualizacji zastępstw. (ADMIN ONLY)')
@app_commands.describe(channel='Kanał, na który będą wysyłane aktualizacje zastępstw.')
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
	try:
		if not interaction.user.guild_permissions.administrator:
			await interaction.response.send_message("Nie masz uprawnień do używania tej komendy.")
			log_command(interaction, success=False, error_message="Brak uprawnień")
			return

		if str(interaction.guild.id) not in config.get('allowed_guilds', []):
			await interaction.response.send_message("Nie masz uprawnień do używania tej komendy na tym serwerze.")
			log_command(interaction, success=False, error_message="Serwer nie jest dozwolony")
			return

		GUILD_CONFIG.setdefault(str(interaction.guild.id), {})['channel_id'] = str(channel.id)
		save_config(config)

		view = ClassView(classes_by_grade)
		await interaction.response.send_message(
			f"**Teraz możesz ustawić zastępstwa dla danych klas, co oznacza, że bot będzie wysyłać Ci na serwer zastępstwa jedynie tych klas, które wybierzesz.**", 
			view=view,
			ephemeral=False
		)

		log_command(interaction, success=True)
		
	except Exception as e:
		log_command(interaction, success=False, error_message=str(e))
		await interaction.response.send_message(f"Wystąpił błąd: {str(e)}", ephemeral=True)
		raise

# /zarządzaj
@bot.tree.command(name='zarządzaj', description='Dodaj lub usuń serwer z listy dozwolonych serwerów. (DEV ONLY)')
@app_commands.describe(dodaj_id='ID serwera, który chcesz dodać do listy dozwolonych serwerów.', usun_id='ID serwera, który chcesz usunąć z listy dozwolonych serwerów.')
async def add_or_remove_server(interaction: discord.Interaction, dodaj_id: str = None, usun_id: str = None):
	try:
		user_id = str(interaction.user.id)

		# Sprawdza, czy użytkownik jest na liście dozwolonych użytkowników
		if user_id not in allowed_users:
			await interaction.response.send_message("Nie masz uprawnień do używania tej komendy.")
			log_command(interaction, success=False, error_message="Brak uprawnień")
			return

		# Sprawdza, czy podano obie opcje
		if dodaj_id and usun_id:
			await interaction.response.send_message("Możesz wybrać tylko jedną z opcji.")
			log_command(interaction, success=False, error_message="Wybrano obie opcje")
			return

		# Sprawdza, czy przynajmniej jedna opcja została podana
		if not dodaj_id and not usun_id:
			await interaction.response.send_message("Musisz wybrać jedną z opcji.")
			log_command(interaction, success=False, error_message="Brak wybranych opcji")
			return

		# Sprawdza, czy ID serwera to tylko cyfry
		guild_id = dodaj_id or usun_id
		if not guild_id.isdigit():
			await interaction.response.send_message(f"Podane ID serwera **({guild_id})** jest nieprawidłowe. ID serwera musi składać się wyłącznie z cyfr.")
			log_command(interaction, success=False, error_message="Nieprawidłowe ID serwera")
			return

		# Obsługa dodania ID serwera
		if dodaj_id:
			if dodaj_id in config.get('allowed_guilds', []):
				await interaction.response.send_message("Ten serwer jest już na liście dozwolonych serwerów.")
				log_command(interaction, success=False, error_message="Serwer już dodany")
			else:
				config['allowed_guilds'].append(dodaj_id)
				config['guilds'][dodaj_id] = {'channel_id': None, 'selected_classes': []}
				save_config(config)
				await interaction.response.send_message(f"Serwer o ID **{dodaj_id}** został dodany do listy dozwolonych serwerów.")
				log_command(interaction, success=True)

		# Obsługa usunięcia ID serwera
		if usun_id:
			if usun_id not in config.get('allowed_guilds', []):
				await interaction.response.send_message("Ten serwer nie znajduje się na liście dozwolonych serwerów.")
				log_command(interaction, success=False, error_message="Serwer nie znaleziony")
			else:
				config['allowed_guilds'].remove(usun_id)
				config['guilds'].pop(usun_id, None)
				save_config(config)
				await interaction.response.send_message(f"Serwer o ID **{usun_id}** został usunięty z listy dozwolonych serwerów.")
				log_command(interaction, success=True)

	except Exception as e:
		log_command(interaction, success=False, error_message=str(e))
		await interaction.response.send_message(f"Wystąpił błąd: {str(e)}", ephemeral=True)
		raise

# Uruchomienie bota
bot.run(TOKEN)