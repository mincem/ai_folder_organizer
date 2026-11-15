from argparse import ArgumentParser

from lib.command import Command

STARTING_DIRS = []

if __name__ == '__main__':
    parser = ArgumentParser(description='Organizes folders using a prompt.')
    parser.add_argument('--path', help='path to the starting directory')
    parser.add_argument('--country', help='country of the editions, to look up the local publisher (e.g. AR)')
    arguments = parser.parse_args()

    if arguments.path is None:
        for starting_dir in STARTING_DIRS:
            Command(root_folder=starting_dir, country=arguments.country).execute()
    else:
        Command(root_folder=arguments.path, country=arguments.country).execute()
