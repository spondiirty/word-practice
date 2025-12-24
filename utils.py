import os

from prompt_toolkit import prompt
from prompt_toolkit.styles import Style

CUR_FILE = os.path.abspath(__file__)
CUR_DIR = os.path.dirname(CUR_FILE)


def path(path: str):
	return os.path.join(CUR_DIR, path)


def clear_screen():
	# Clear the terminal screen (cross-platform)
	os.system('cls' if os.name == 'nt' else 'clear')


def speak_text(text: str, voice: str = "Amira", speed=200):
	"""Use the system's text-to-speech to speak the given text."""
	import subprocess

	subprocess.run([
		"say",
		"-v", voice,
		"-r", str(speed),
		text
	])


style = Style.from_dict({
	'prompt': 'ansiwhite',
	'': 'ansiyellow',
})


def safe_input(prompt_text: str | None = None) -> str:
	try:
		return prompt(prompt_text, style=style)
	except EOFError:
		return ""
