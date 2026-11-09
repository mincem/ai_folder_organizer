from lib.gemini_client import configure_gemini, list_generation_models

if __name__ == '__main__':
    configure_gemini()
    for name in list_generation_models():
        print(name)
