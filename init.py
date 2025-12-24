import sys

from engine import Settings


def main(profile):
	Settings.create(profile)


if __name__ == '__main__':
	main(sys.argv[1] if len(sys.argv) > 1 else 'test')
