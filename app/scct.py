from converter_core import DEFAULT_OUTPUT_FOLDER, PROFILES, run_profile


SCCT_FOLDER = PROFILES["SCCT"].input_folder
SCCT_PREFIX = PROFILES["SCCT"].prefix
OUTPUT_FOLDER = DEFAULT_OUTPUT_FOLDER


def main():
    return run_profile("SCCT", OUTPUT_FOLDER, SCCT_FOLDER)


if __name__ == "__main__":
    main()
