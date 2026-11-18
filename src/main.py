from argparse import ArgumentParser

from lib.ai_request import AIRequest
from lib.ai_service import AIService
from lib.command import Command
from lib.confirmation import Confirmer
from lib.logger import Logger
from lib.metadata_cache import MetadataCache

STARTING_DIRS = []


def organize(root_folder: str, country: str | None, ai_service: AIService):
    # The metadata cache lives in each root folder, and the logger counts the renames of one run
    logger = Logger()
    metadata_cache = MetadataCache(root_folder)
    ai_request = AIRequest(ai_service, logger)
    confirmer = Confirmer(metadata_cache, country)
    Command(root_folder, country, ai_request, confirmer, metadata_cache, logger).execute()


def main():
    parser = ArgumentParser(description='Organizes folders using a prompt.')
    parser.add_argument('--path', help='path to the starting directory')
    parser.add_argument('--country', help='country of the editions, to look up the local publisher (e.g. AR)')
    arguments = parser.parse_args()

    # Shared by all the folders, so the AI client is set up once
    ai_service = AIService()
    for folder in [arguments.path] if arguments.path is not None else STARTING_DIRS:
        organize(folder, arguments.country, ai_service)


if __name__ == '__main__':
    main()
