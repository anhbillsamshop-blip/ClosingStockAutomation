from converter_core import DEFAULT_OUTPUT_FOLDER, PROFILES, run_profile


INPUT_FOLDER = PROFILES["CLOSING_STOCK"].input_folder
CLOSING_STOCK_PREFIX = PROFILES["CLOSING_STOCK"].prefix
OUTPUT_FOLDER = DEFAULT_OUTPUT_FOLDER


def main():
    return run_profile("CLOSING_STOCK", OUTPUT_FOLDER, INPUT_FOLDER)


if __name__ == "__main__":
    main()
