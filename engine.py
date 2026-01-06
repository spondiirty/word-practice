import csv
import json
import os
import re
import sqlite3
import string

from rich.console import Console

from utils import clear_screen, speak_text, safe_input, path


class Item:
	def __init__(self, base_word: str, target_word: str, target_example: str, base_example: str):
		self.base_word = base_word
		self.target_word = target_word
		self.target_example = target_example
		self.base_example = base_example

	@classmethod
	def from_row(cls, row: sqlite3.Row):
		return cls(
			base_word=row['base_word'],
			target_word=row['target_word'],
			target_example=row['target_example'],
			base_example=row['base_example']
		)


class DB:
	def __init__(self, profile):
		self.profile = profile
		self.path = path(f'{profile}.db')

	def __enter__(self):
		self.conn = sqlite3.connect(self.path)
		self.conn.row_factory = sqlite3.Row
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		self.conn.close()

	def execute(self, sql, *args, **kwargs):
		with self.conn:  # auto commit / rollback
			cur = self.conn.execute(sql, *args, **kwargs)
			if cur.description:  # SELECT
				return cur.fetchall()
			return None

	def execute_many(self, sql, *args, **kwargs):
		with self.conn:  # auto commit / rollback
			cur = self.conn.executemany(sql, *args, **kwargs)
			if cur.description:  # SELECT
				return cur.fetchall()
			return None

	@staticmethod
	def touch_db(profile):
		conn = sqlite3.connect(path(f'{profile}.db'))
		with conn:
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS items (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					base_word TEXT NOT NULL,
					target_word TEXT NOT NULL,
					target_example TEXT,
					base_example TEXT
				)
				"""
			)
		with conn:
			conn.execute(
				"""
                CREATE TABLE IF NOT EXISTS batches (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					items TEXT NOT NULL,
					round INTEGER DEFAULT 0,
					last_practiced DATE,
					due_date DATE
                )
				"""
			)
		conn.close()

class Settings:
	def __init__(self, profile):
		self.profile = profile
		self.path = path(f'{profile}.json')

		with open(self.path, 'r', encoding='utf-8') as f:
			self.data = json.load(f)

	def update(self, **kwargs):
		self.data.update(kwargs)
		with open(self.path, 'w', encoding='utf-8') as f:
			json.dump(self.data, f, indent=2)

	@staticmethod
	def create(profile):
		fpath = path(f'{profile}.json')
		if not os.path.exists(fpath):
			# create file with default contents
			with open(fpath, 'w', encoding='utf-8') as f:
				json.dump({
					'profile': profile,
					'word_book': path('malayu_basic.csv'),
					'batch_size': 5,
					'comparison_strategy': 'basic',
					'current_index': 0,
					'intervals': [0, 1, 2, 3, 2, 1, 4],
					'voice_speed': 200
				}, f, indent=2)


class Engine:

	def __init__(self, profile):
		self.console = Console()
		self.profile = profile
		self.settings = Settings(profile)
		DB.touch_db(self.profile)

	def print(self, *args, **kwargs):
		self.console.print(*args, **kwargs)

	def do_today(self):
		self.insert_new_batch()
		for i, batch in enumerate(self.query_next_batch()):
			self.heads_up_display(f'Today\'s practice: Batch {i + 1}')
			batch_items = self.fetch_batch_items(batch)
			self.do_one_batch(batch_items)
			self.mark_batch_complete(batch)
		self.heads_up_display(f'[green]Today\'s practice complete! Good job![/]')

	def do_one_batch(self, batch: list[Item]):
		import random
		remaining = batch[:]
		while remaining:
			random.shuffle(remaining)
			incorrect = []
			for item in remaining:
				correct = self.do_one_word(item)
				if not correct:
					incorrect.append(item)
			remaining = incorrect
		self.heads_up_display(f'Congratulations!\nBatch complete!')

	def do_one_word(self, item):
		clear_screen()
		self.print(f'[cyan]{item.base_word}[/]')
		if self.settings.data.get('show_target_word_hint', False):
			self.print(f'[dim]Hint: {self.get_hint(item.target_word)}[/]')
		ans = safe_input('Answer: ')
		correct = self.compare_answer(ans, item.target_word)

		self.print("")
		if correct:
			self.print("[green]Your answer is correct! [/]")
		else:
			self.print("[red]Not Correct! [/]")
			self.print(f"The correct answer is [green]{item.target_word}[/]")

		self.print(f"\nexample: \n - [yellow]{item.target_example}[/]")
		speak_text(
			item.target_example,
			voice=self.settings.data.get('voice', 'Amira'),
			speed=self.settings.data.get('voice_speed', 200)
		)
		self.print(f" - [cyan]{item.base_example}[/]")
		self.print("\n[blue]press \[enter] to continue...[/]")
		safe_input()
		return correct

	def compare_answer(self, ans: str, target: str, strategy: str = 'basic') -> bool:
		if ans is None or target is None:
			return False

		def normalize_basic(s: str) -> str:
			# lowercase
			s = s.lower()

			# remove punctuation
			s = re.sub(rf"[{re.escape(string.punctuation)}]", "", s)

			# remove all whitespace
			s = re.sub(r"\s+", "", s)

			return s

		if strategy == "basic":
			return normalize_basic(ans) == normalize_basic(target)

		else:
			raise ValueError(f"Unknown strategy: {strategy}")

	def heads_up_display(self, text):
		clear_screen()
		self.print(f'[bold]{text}[/]')
		self.print("\n[blue]press \[enter] to continue...[/]")
		safe_input()

	def fetch_today_batches(self):
		self.insert_new_batch()
		with DB(self.profile) as db:
			data = db.execute(
				f"""
				SELECT id, items, round, last_practiced, due_date 
				FROM batches 
				WHERE due_date <= DATE('now')
				ORDER BY id DESC
				""")

		return data

	def mark_batch_complete(self, batch):
		with DB(self.profile) as db:
			if len(self.settings.data.get('intervals')) == batch['round']:
				db.execute(
					f"""
				DELETE FROM batches  
				WHERE id = ?
				""",
					(batch['id'],)
				)
			else:
				db.execute(
					f"""
					UPDATE batches 
					SET round = round + 1, last_practiced = DATE('now'), due_date = DATE('now', '+{ self.settings.data.get('intervals')[batch['round']]} days') 
					WHERE id = ?
					""",
					(batch['id'],)
				)

	def fetch_batch_items(self, batch):
		with DB(self.profile) as db:
			data = db.execute(
			f"""
			SELECT id, base_word, target_word, target_example, base_example 
			FROM items 
			WHERE id IN ({batch['items']})
			""")

		return [Item.from_row(row) for row in data]

	def insert_new_batch(self):
		settings = self.settings.data
		current_index = settings.get('current_index')
		batch_size = settings.get('batch_size')
		word_book = settings.get('word_book')

		with open(word_book) as word_book_file:
			csv_reader = csv.DictReader(word_book_file)
			rows = list(csv_reader)

		batch_rows = []
		for i in range(current_index, current_index + batch_size):
			rows[i]['id'] = i
			batch_rows.append(rows[i])

		with DB(self.profile) as db:
			db.execute_many(
				f"""
				INSERT INTO items (id, base_word, target_word, target_example, base_example) 
				VALUES (?, ?, ?, ?, ?)
				""",
				[(row['id'], row['base_word'], row['target_word'], row['target_example'], row['base_example']) for row in batch_rows]
			)

		with DB(self.profile) as db:
			item_ids = ','.join(str(row['id']) for row in batch_rows)
			db.execute(
				f"""
				INSERT INTO batches (items, round, last_practiced, due_date) 
				VALUES (?, 0, NULL, DATE('now'))
				""",
				(item_ids,)
			)

		self.settings.update(current_index=current_index + batch_size)

	def query_next_batch(self):
		while True:
			with DB(self.profile) as db:
				data = db.execute(
					f"""
					SELECT id, items, round, last_practiced, due_date 
					FROM batches 
					WHERE due_date <= DATE('now')
					ORDER BY id DESC
					LIMIT 1
					""")

			if not data:
				break

			yield data[0]

	@staticmethod
	def get_hint(target_word):
		res = re.sub(r'\S', '*', target_word)
		return target_word[0] + res[1:]
