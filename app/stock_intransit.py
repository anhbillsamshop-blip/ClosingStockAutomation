from converter_core import DEFAULT_OUTPUT_FOLDER, PROFILES, run_profile


INPUT_FOLDER = PROFILES["STOCK_INTRANSIT"].input_folder
INTRANSIT_PREFIX = PROFILES["STOCK_INTRANSIT"].prefix
OUTPUT_FOLDER = DEFAULT_OUTPUT_FOLDER
DELIMITER = PROFILES["STOCK_INTRANSIT"].delimiter


def main():
    return run_profile("STOCK_INTRANSIT", OUTPUT_FOLDER, INPUT_FOLDER)


if __name__ == "__main__":
    main()
