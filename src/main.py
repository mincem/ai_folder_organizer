from argparse import ArgumentParser

from lib.ai_service import AIService
from lib.command import Command
from lib.logger import Logger
from lib.metadata_cache import MetadataCache

STARTING_DIRS = []


def organize(root_folder: str, country: str | None, ai_service: AIService):
    # The metadata cache lives in each root folder, and the logger counts the renames of one run
    Command(root_folder, country, ai_service, MetadataCache(root_folder), Logger()).execute()


if __name__ == '__main__':
    parser = ArgumentParser(description='Organizes folders using a prompt.')
    parser.add_argument('--path', help='path to the starting directory')
    parser.add_argument('--country', help='country of the editions, to look up the local publisher (e.g. AR)')
    arguments = parser.parse_args()

    # Shared by all the folders, so the AI client is set up once
    ai_service = AIService()
    for folder in [arguments.path] if arguments.path is not None else STARTING_DIRS:
        organize(folder, arguments.country, ai_service)
