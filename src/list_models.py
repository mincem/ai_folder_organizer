from lib.gemini_client import create_gemini_client, list_generation_models

if __name__ == '__main__':
    for name in list_generation_models(create_gemini_client()):
        print(name)
