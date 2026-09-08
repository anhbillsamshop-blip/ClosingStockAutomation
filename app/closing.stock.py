import csv
import re
import os
from pathlib import Path
from datetime import datetime
import duckdb


# ============================================================
# CONFIG
# ============================================================

# ------------------------------------------------------------
# NGUỒN CLOSING STOCK TRÊN Ổ CHUNG
# ------------------------------------------------------------

INPUT_FOLDER = Path(
    r"\\masan.local\15. Khoi Logistics\99.15.1. Inputdata"
)

CLOSING_STOCK_PREFIX = "CLOSING_STOCK_"


# ------------------------------------------------------------
# OUTPUT PARQUET TRÊN Ổ D
# ------------------------------------------------------------

OUTPUT_FOLDER = Path(
    r"D:\ClosingStockAutomation\CSVtoParquet"
)


# ============================================================
# CẤU HÌNH
# ============================================================

BATCH_SIZE = 10000


# ============================================================
# FORMAT SIZE
# ============================================================

def format_bytes(value):

    value = float(value)

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB"
    ]

    for unit in units:

        if value < 1024:

            return f"{value:.1f} {unit}"

        value /= 1024

    return f"{value:.1f} PB"


# ============================================================
# TÌM FILE CLOSING STOCK MỚI NHẤT
# ============================================================

def find_latest_closing_stock_file():

    print()
    print("=" * 80)
    print("TÌM FILE CLOSING STOCK MỚI NHẤT")
    print("=" * 80)

    print()
    print("Folder nguồn:")

    print(
        INPUT_FOLDER
    )


    # ========================================================
    # KIỂM TRA FOLDER
    # ========================================================

    if not INPUT_FOLDER.exists():

        raise Exception(
            f"Folder nguồn không tồn tại:\n"
            f"{INPUT_FOLDER}"
        )


    if not INPUT_FOLDER.is_dir():

        raise Exception(
            f"Đường dẫn không phải folder:\n"
            f"{INPUT_FOLDER}"
        )


    # ========================================================
    # TÌM TẤT CẢ FILE CLOSING STOCK
    # ========================================================

    files = list(
        INPUT_FOLDER.glob(
            f"{CLOSING_STOCK_PREFIX}*.csv"
        )
    )


    print()
    print(
        f"Tổng số file tìm thấy: {len(files)}"
    )


    if not files:

        raise Exception(
            "Không tìm thấy file CLOSING_STOCK."
        )


    # ========================================================
    # FORMAT:
    #
    # CLOSING_STOCK_YYYYMMDDHHMMSS.csv
    # ========================================================

    regex = re.compile(
        rf"^{re.escape(CLOSING_STOCK_PREFIX)}"
        rf"(\d{{14}})\.csv$",
        re.IGNORECASE
    )


    # ========================================================
    # TÌM FILE CÓ TIMESTAMP LỚN NHẤT
    #
    # KHÔNG QUAN TÂM NGÀY
    # ========================================================

    latest_file = None

    latest_timestamp = None


    for file in files:

        match = regex.match(
            file.name
        )


        if not match:

            continue


        try:

            timestamp = datetime.strptime(
                match.group(1),
                "%Y%m%d%H%M%S"
            )

        except ValueError:

            continue


        if (
            latest_timestamp is None
            or timestamp > latest_timestamp
        ):

            latest_timestamp = timestamp

            latest_file = file


    # ========================================================
    # KHÔNG CÓ FILE ĐÚNG FORMAT
    # ========================================================

    if latest_file is None:

        raise Exception(
            "Không có file CLOSING_STOCK đúng format:\n"
            "CLOSING_STOCK_YYYYMMDDHHMMSS.csv"
        )


    # ========================================================
    # HIỂN THỊ FILE ĐƯỢC CHỌN
    # ========================================================

    print()
    print("✓ File CLOSING_STOCK mới nhất:")

    print(
        latest_file.name
    )


    print()
    print("✓ Timestamp:")

    print(
        latest_timestamp.strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )


    print()
    print("✓ Size:")

    print(
        format_bytes(
            latest_file.stat().st_size
        )
    )


    return latest_file


# ============================================================
# XÓA CÁC FILE CLOSING STOCK CŨ TRONG OUTPUT
#
# CHỈ XÓA:
#
# CLOSING_STOCK_*.parquet
#
# KHÔNG XÓA:
#
# 30D_SALES_*.parquet
# SCCT_RAWDATA_*.parquet
# STOCK_INTRANSIT_*.parquet
# hoặc các file khác
# ============================================================

def clear_old_closing_stock_output():

    print()
    print("=" * 80)
    print("XÓA FILE CLOSING STOCK CŨ TRONG OUTPUT")
    print("=" * 80)

    print()
    print("Output folder:")

    print(
        OUTPUT_FOLDER
    )


    # ========================================================
    # TẠO FOLDER NẾU CHƯA CÓ
    # ========================================================

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )


    # ========================================================
    # CHỈ TÌM FILE CLOSING_STOCK_*.parquet
    # ========================================================

    old_files = list(
        OUTPUT_FOLDER.glob(
            f"{CLOSING_STOCK_PREFIX}*.parquet"
        )
    )


    print()
    print(
        f"Số file CLOSING_STOCK cũ: "
        f"{len(old_files)}"
    )


    # ========================================================
    # XÓA FILE CŨ
    # ========================================================

    deleted_count = 0


    for file in old_files:

        try:

            file.unlink()

            deleted_count += 1

            print(
                f"✓ Đã xóa: "
                f"{file.name}"
            )

        except Exception as e:

            raise Exception(
                f"Không thể xóa file "
                f"CLOSING_STOCK cũ:\n"
                f"{file}\n\n"
                f"Lỗi: {e}"
            )


    print()
    print(
        f"✓ Đã xóa "
        f"{deleted_count} file CLOSING_STOCK cũ."
    )


    print()
    print(
        "✓ Các file khác trong Output được giữ nguyên."
    )


# ============================================================
# PARSE 1 DÒNG CSV BỊ LỖI QUOTE
# ============================================================

def parse_csv_line(line):

    """
    Parse một dòng CSV có thể có quote không chuẩn.

    Quy tắc:
    - Dấu phẩy ngoài quote = phân cách cột.
    - Dấu phẩy trong quote = dữ liệu.
    - "" trong quote = quote literal.
    - " ở giữa nội dung = quote literal.
    - " trước comma / cuối dòng = quote đóng.
    """

    line = line.rstrip(
        "\r\n"
    )


    fields = []

    current = []

    in_quotes = False

    i = 0


    while i < len(line):

        ch = line[i]


        # ====================================================
        # QUOTE
        # ====================================================

        if ch == '"':


            # ------------------------------------------------
            # ĐANG TRONG QUOTE
            # ------------------------------------------------

            if in_quotes:


                # --------------------------------------------
                # "" => quote literal
                # --------------------------------------------

                if (
                    i + 1 < len(line)
                    and line[i + 1] == '"'
                ):

                    current.append('"')

                    i += 2

                    continue


                # --------------------------------------------
                # Quote trước comma
                # hoặc cuối dòng
                # => quote đóng
                # --------------------------------------------

                if (
                    i + 1 == len(line)
                    or line[i + 1] == ","
                ):

                    in_quotes = False

                    i += 1

                    continue


                # --------------------------------------------
                # Quote nằm giữa nội dung
                # => coi là dữ liệu
                # --------------------------------------------

                current.append('"')

                i += 1

                continue


            # ------------------------------------------------
            # NGOÀI QUOTE
            # ------------------------------------------------

            if not current:

                in_quotes = True

                i += 1

                continue


            # ------------------------------------------------
            # QUOTE GIỮA FIELD
            # => coi là dữ liệu
            # ------------------------------------------------

            current.append('"')

            i += 1

            continue


        # ====================================================
        # COMMA
        # ====================================================

        if ch == "," and not in_quotes:

            fields.append(
                "".join(current)
            )

            current = []

            i += 1

            continue


        # ====================================================
        # KÝ TỰ BÌNH THƯỜNG
        # ====================================================

        current.append(ch)

        i += 1


    # ========================================================
    # FIELD CUỐI
    # ========================================================

    fields.append(
        "".join(current)
    )


    return fields


# ============================================================
# NORMALIZE CSV
# ============================================================

def create_temp_csv(
    input_file,
    temp_csv
):

    print()
    print("=" * 80)
    print("NORMALIZE CLOSING STOCK CSV")
    print("=" * 80)


    print()
    print("Input:")

    print(
        input_file
    )


    print()
    print("Temp:")

    print(
        temp_csv
    )


    start_time = datetime.now()

    row_count = 0


    # ========================================================
    # ĐỌC FILE NGUỒN
    # ========================================================

    with open(
        input_file,
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline=""
    ) as source:


        # ====================================================
        # GHI TEMP
        # ====================================================

        with open(
            temp_csv,
            "w",
            encoding="utf-8",
            newline=""
        ) as target:


            writer = csv.writer(
                target,
                delimiter=",",
                quotechar='"',
                doublequote=True,
                lineterminator="\n"
            )


            # =================================================
            # XỬ LÝ TỪNG DÒNG
            # =================================================

            for line_number, line in enumerate(
                source,
                1
            ):

                try:

                    fields = parse_csv_line(
                        line
                    )


                    writer.writerow(
                        fields
                    )


                    row_count += 1


                except Exception as e:

                    raise Exception(
                        f"Lỗi tại dòng "
                        f"{line_number}: {e}"
                    )


                # ------------------------------------------------
                # PROGRESS
                # ------------------------------------------------

                if (
                    row_count
                    % BATCH_SIZE
                    == 0
                ):

                    print(
                        f"  Đã normalize "
                        f"{row_count:,} dòng..."
                    )


    elapsed = (
        datetime.now() - start_time
    ).total_seconds()


    print()
    print(
        f"✓ Normalize xong: "
        f"{row_count:,} dòng"
    )


    print(
        f"✓ Thời gian: "
        f"{elapsed:.1f} giây"
    )


    return row_count


# ============================================================
# CSV -> PARQUET
# ============================================================

def convert_to_parquet(
    normalized_csv,
    output_parquet
):

    print()
    print("=" * 80)
    print("DUCKDB: CLOSING STOCK CSV -> PARQUET")
    print("=" * 80)


    print()
    print("Input:")

    print(
        normalized_csv
    )


    print()
    print("Output:")

    print(
        output_parquet
    )


    # ========================================================
    # DUCKDB
    # ========================================================

    con = duckdb.connect(
        database=":memory:"
    )


    try:

        # ====================================================
        # CPU
        # ====================================================

        cpu_count = (
            os.cpu_count() or 4
        )


        threads = min(
            cpu_count,
            16
        )


        con.execute(
            f"SET threads TO {threads}"
        )


        con.execute(
            "SET preserve_insertion_order = false"
        )


        print()
        print(
            f"Threads: {threads}"
        )


        # ====================================================
        # CONVERT
        # ====================================================

        print()
        print(
            "Đang convert..."
        )


        start_time = datetime.now()


        con.execute(
            f"""
            COPY (
                SELECT *
                FROM read_csv(
                    '{normalized_csv.as_posix()}',
                    header = false,
                    auto_detect = true,
                    strict_mode = true,
                    parallel = true
                )
            )

            TO '{output_parquet.as_posix()}'

            (
                FORMAT PARQUET,
                COMPRESSION SNAPPY
            );
            """
        )


        elapsed = (
            datetime.now() - start_time
        ).total_seconds()


        # ====================================================
        # KIỂM TRA PARQUET
        # ====================================================

        print()
        print(
            "Đang kiểm tra Parquet..."
        )


        count = con.execute(
            f"""
            SELECT COUNT(*)
            FROM read_parquet(
                '{output_parquet.as_posix()}'
            )
            """
        ).fetchone()[0]


        columns = con.execute(
            f"""
            DESCRIBE
            SELECT *
            FROM read_parquet(
                '{output_parquet.as_posix()}'
            )
            """
        ).fetchall()


        # ====================================================
        # SIZE
        # ====================================================

        parquet_size = (
            output_parquet.stat().st_size
        )


        # ====================================================
        # KẾT QUẢ
        # ====================================================

        print()
        print("=" * 80)
        print("✓ PARQUET HOÀN TẤT")
        print("=" * 80)


        print()


        print(
            f"Rows   : {count:,}"
        )


        print(
            f"Columns: {len(columns)}"
        )


        print(
            f"Size   : {format_bytes(parquet_size)}"
        )


        print(
            f"Time   : {elapsed:.1f} giây"
        )


        print()


        print("Output:")


        print(
            output_parquet
        )


        # ====================================================
        # HIỂN THỊ 20 DÒNG ĐẦU
        # ====================================================

        print()
        print("-" * 80)
        print("20 DÒNG ĐẦU PARQUET")
        print("-" * 80)


        result = con.execute(
            f"""
            SELECT *
            FROM read_parquet(
                '{output_parquet.as_posix()}'
            )
            LIMIT 20
            """
        ).fetchall()


        for row in result:

            print(row)


        return count


    finally:

        con.close()


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print()
    print("=" * 80)
    print("CLOSING STOCK")
    print("NETWORK CSV -> D: PARQUET")
    print("=" * 80)


    # ========================================================
    # TẠO OUTPUT FOLDER
    # ========================================================

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )


    # ========================================================
    # BƯỚC 1
    #
    # TÌM FILE CLOSING STOCK MỚI NHẤT
    #
    # KHÔNG QUAN TÂM NGÀY
    # ========================================================

    input_file = (
        find_latest_closing_stock_file()
    )


    # ========================================================
    # BƯỚC 2
    #
    # XÓA CHỈ CÁC FILE CLOSING_STOCK CŨ
    #
    # CÁC FILE KHÁC GIỮ NGUYÊN
    # ========================================================

    clear_old_closing_stock_output()


    # ========================================================
    # BƯỚC 3
    #
    # TÊN OUTPUT
    #
    # INPUT:
    #
    # CLOSING_STOCK_20260905090000.csv
    #
    # OUTPUT:
    #
    # CLOSING_STOCK_20260905090000.parquet
    # ========================================================

    output_parquet = (
        OUTPUT_FOLDER /
        f"{input_file.stem}.parquet"
    )


    # ========================================================
    # TEMP CSV
    # ========================================================

    temp_csv = (
        OUTPUT_FOLDER /
        "_CLOSING_STOCK_normalized.tmp.csv"
    )


    # ========================================================
    # XÓA TEMP CŨ NẾU CÒN
    # ========================================================

    if temp_csv.exists():

        try:

            temp_csv.unlink()

        except Exception as e:

            raise Exception(
                f"Không thể xóa temp CSV cũ:\n"
                f"{temp_csv}\n"
                f"Lỗi: {e}"
            )


    # ========================================================
    # BƯỚC 4
    #
    # NORMALIZE
    # ========================================================

    create_temp_csv(
        input_file,
        temp_csv
    )


    try:

        # ====================================================
        # BƯỚC 5
        #
        # CONVERT SANG PARQUET
        # ====================================================

        row_count = convert_to_parquet(
            temp_csv,
            output_parquet
        )


    except Exception:

        # ----------------------------------------------------
        # Nếu convert lỗi
        # -> xóa file output lỗi
        # ----------------------------------------------------

        if output_parquet.exists():

            try:

                output_parquet.unlink()

            except Exception:

                pass


        raise


    finally:

        # ====================================================
        # XÓA TEMP CSV
        # ====================================================

        if temp_csv.exists():

            try:

                temp_csv.unlink()

                print()
                print(
                    "✓ Đã xóa temp CSV."
                )

            except Exception as e:

                print()
                print(
                    f"⚠ Không xóa được temp CSV: {e}"
                )


    # ========================================================
    # FINAL
    # ========================================================

    print()
    print("=" * 80)
    print("✓ CLOSING STOCK HOÀN TẤT")
    print("=" * 80)


    print()


    print(
        f"Rows: {row_count:,}"
    )


    print()


    print(
        "File input được chọn:"
    )


    print(
        input_file
    )


    print()


    print(
        "File output:"
    )


    print(
        output_parquet
    )


    print()


    print(
        "✓ Chỉ các file CLOSING_STOCK cũ đã được xóa."
    )


    print(
        "✓ Các file output khác vẫn được giữ nguyên."
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as e:

        print()
        print("=" * 80)
        print("!!! CHƯƠNG TRÌNH BỊ LỖI !!!")
        print("=" * 80)

        print()
        print(str(e))

        print()

        input(
            "Nhấn Enter để đóng..."
        )

        raise