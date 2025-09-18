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
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Zewnętrzne biblioteki
import discord

# Wewnętrzne importy
from classes.timezone import FormatStrefyCzasowej

# Konfiguruje globalne logowanie
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

# Konfiguruje logowanie poleceń
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