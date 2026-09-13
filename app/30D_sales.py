from converter_core import DEFAULT_OUTPUT_FOLDER, PROFILES, run_profile


INPUT_FOLDER = PROFILES["30D_SALES"].input_folder
SALES_PREFIX = PROFILES["30D_SALES"].prefix
OUTPUT_FOLDER = DEFAULT_OUTPUT_FOLDER
DELIMITER = PROFILES["30D_SALES"].delimiter


def main():
    return run_profile("30D_SALES", OUTPUT_FOLDER, INPUT_FOLDER)


if __name__ == "__main__":
    main()
