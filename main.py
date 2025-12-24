import sys

from rich.console import Console
from prompt_toolkit import prompt

from engine import Item, Engine
from utils import clear_screen, speak_text


def print_screen(content: str):
	clear_screen()
	console = Console()
	console.print(content)
	i = prompt("Answer: ")
	console.print("[green]Great! [/]")
	speak_text("Apa khabar? Ini suara Bahasa Melayu.")
	console.print("\n[blue]press \[enter] to continue...[/]")
	t = prompt()


def main():
	item = Item(
		base_word="Hello!",
		target_word="Hai!",
		base_example="Good morning!",
		target_example="Selamat pagi!"
	)
	engine = Engine('y')
	while True:
		correct = engine.do_one_word(item)


def main2(profile):
	engine = Engine(profile)
	engine.do_today()


if __name__ == '__main__':
	main2(sys.argv[1] if len(sys.argv) > 1 else 'test')
