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
# NGUỒN SCCT THẬT TRÊN Ổ CHUNG
# ------------------------------------------------------------

SCCT_FOLDER = Path(
    r"\\masan.local\15. Khoi Logistics\99.15.1. Inputdata\99.15.9 RAW"
)

SCCT_PREFIX = "SCCT_RAWDATA_LD_WMP_"


# ------------------------------------------------------------
# OUTPUT PARQUET TRÊN Ổ D
# ------------------------------------------------------------

OUTPUT_FOLDER = Path(
    r"D:\ClosingStockAutomation\CSVtoParquet"
)


# ============================================================
# CẤU HÌNH STREAM
# ============================================================

# Không đọc toàn bộ CSV vào RAM.
# Đọc từng dòng và đưa từng batch sang DuckDB.

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
# TÌM FILE SCCT MỚI NHẤT
# ============================================================

def find_latest_scct_file():

    print()
    print("=" * 80)
    print("TÌM FILE SCCT MỚI NHẤT")
    print("=" * 80)


    print()
    print("Folder nguồn:")

    print(
        SCCT_FOLDER
    )


    # ========================================================
    # KIỂM TRA FOLDER
    # ========================================================

    if not SCCT_FOLDER.exists():

        raise Exception(
            f"Folder không tồn tại:\n"
            f"{SCCT_FOLDER}"
        )


    if not SCCT_FOLDER.is_dir():

        raise Exception(
            f"Đường dẫn không phải folder:\n"
            f"{SCCT_FOLDER}"
        )


    # ========================================================
    # TÌM FILE
    # ========================================================

    files = list(
        SCCT_FOLDER.glob(
            f"{SCCT_PREFIX}*.csv"
        )
    )


    print()
    print(
        f"Số file tìm thấy: {len(files)}"
    )


    if not files:

        raise Exception(
            "Không tìm thấy file SCCT."
        )


    # ========================================================
    # FORMAT:
    #
    # SCCT_RAWDATA_LD_WMP_YYYYMMDD.csv
    # ========================================================

    regex = re.compile(
        rf"^{re.escape(SCCT_PREFIX)}"
        rf"(\d{{8}})\.csv$",
        re.IGNORECASE
    )


    latest_file = None

    latest_date = None


    # ========================================================
    # TÌM FILE MỚI NHẤT
    # ========================================================

    for file in files:

        match = regex.match(
            file.name
        )


        if not match:

            continue


        try:

            date_value = datetime.strptime(
                match.group(1),
                "%Y%m%d"
            )


        except ValueError:

            continue


        if (
            latest_date is None
            or date_value > latest_date
        ):

            latest_date = date_value

            latest_file = file


    # ========================================================
    # KHÔNG CÓ FILE ĐÚNG FORMAT
    # ========================================================

    if latest_file is None:

        raise Exception(
            "Không có file SCCT đúng format:\n"
            "SCCT_RAWDATA_LD_WMP_YYYYMMDD.csv"
        )


    # ========================================================
    # HIỂN THỊ FILE ĐƯỢC CHỌN
    # ========================================================

    print()
    print(
        "✓ File SCCT mới nhất:"
    )


    print(
        latest_file.name
    )


    print()
    print(
        "✓ Ngày:"
    )


    print(
        latest_date.strftime(
            "%d/%m/%Y"
        )
    )


    print()
    print(
        "✓ Size:"
    )


    print(
        format_bytes(
            latest_file.stat().st_size
        )
    )


    return latest_file


# ============================================================
# XÓA TOÀN BỘ FILE SCCT CŨ TRONG OUTPUT
#
# CHỈ XÓA:
#
# SCCT_RAWDATA_LD_WMP_*.parquet
#
# KHÔNG XÓA:
#
# 30D_SALES_*.parquet
# CLOSING_STOCK_*.parquet
# STOCK_INTRANSIT_*.parquet
# hoặc file khác
# ============================================================

def clear_old_scct_output():

    print()
    print("=" * 80)
    print("XÓA CÁC FILE SCCT CŨ TRONG OUTPUT")
    print("=" * 80)


    print()
    print(
        "Output folder:"
    )


    print(
        OUTPUT_FOLDER
    )


    # ========================================================
    # TẠO OUTPUT FOLDER
    # ========================================================

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )


    # ========================================================
    # CHỈ TÌM FILE SCCT
    # ========================================================

    old_files = list(
        OUTPUT_FOLDER.glob(
            f"{SCCT_PREFIX}*.parquet"
        )
    )


    print()
    print(
        f"Số file SCCT cũ: "
        f"{len(old_files)}"
    )


    # ========================================================
    # XÓA TỪNG FILE
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
                f"Không thể xóa file SCCT cũ:\n"
                f"{file}\n\n"
                f"Lỗi: {e}"
            )


    print()
    print(
        f"✓ Đã xóa "
        f"{deleted_count} file SCCT cũ."
    )


    print()
    print(
        "✓ Các file loại khác trong Output được giữ nguyên."
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
                # => giữ lại như dữ liệu
                # --------------------------------------------

                current.append('"')

                i += 1

                continue


            # ------------------------------------------------
            # NGOÀI QUOTE
            # ------------------------------------------------

            # Quote ở đầu field
            # => bắt đầu quoted field

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
# NORMALIZE HEADER
# ============================================================

def normalize_header(line):

    fields = parse_csv_line(
        line
    )

    return fields


# ============================================================
# TẠO TEMP CSV TRÊN Ổ D
# ============================================================

def create_temp_csv(
    input_file,
    temp_csv
):

    print()
    print("=" * 80)
    print("NORMALIZE CSV")
    print("=" * 80)


    print()
    print("Input:")


    print(
        input_file
    )


    print()
    print("Temp CSV:")


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


                # =================================================
                # PROGRESS
                # =================================================

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
    print("DUCKDB: CSV -> PARQUET")
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

                    header = true,

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
            f"Size   : "
            f"{format_bytes(parquet_size)}"
        )


        print(
            f"Time   : "
            f"{elapsed:.1f} giây"
        )


        print()


        print(
            "Output:"
        )


        print(
            output_parquet
        )


        # ====================================================
        # HIỂN THỊ 20 DÒNG TEST
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


    finally:

        con.close()


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print()


    print("=" * 80)

    print(
        "SCCT"
    )

    print(
        "NETWORK CSV -> D: PARQUET"
    )

    print("=" * 80)


    # ========================================================
    # OUTPUT FOLDER
    # ========================================================

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )


    # ========================================================
    # BƯỚC 1
    #
    # TÌM FILE SCCT MỚI NHẤT
    # ========================================================

    input_file = (
        find_latest_scct_file()
    )


    # ========================================================
    # BƯỚC 2
    #
    # XÓA TOÀN BỘ SCCT CŨ TRONG OUTPUT
    #
    # CHỈ XÓA:
    #
    # SCCT_RAWDATA_LD_WMP_*.parquet
    #
    # CÁC FILE KHÁC GIỮ NGUYÊN
    # ========================================================

    clear_old_scct_output()


    # ========================================================
    # BƯỚC 3
    #
    # TẠO TÊN OUTPUT THEO ĐÚNG TÊN INPUT
    #
    # INPUT:
    #
    # SCCT_RAWDATA_LD_WMP_20260905.csv
    #
    # OUTPUT:
    #
    # SCCT_RAWDATA_LD_WMP_20260905.parquet
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
        "_SCCT_normalized.tmp.csv"
    )


    # ========================================================
    # XÓA TEMP CŨ NẾU CÒN
    # ========================================================

    if temp_csv.exists():

        print()
        print(
            "Xóa temp CSV cũ..."
        )


        temp_csv.unlink()


    # ========================================================
    # NORMALIZE
    # ========================================================

    create_temp_csv(
        input_file,
        temp_csv
    )


    try:

        # ====================================================
        # CONVERT
        # ====================================================

        convert_to_parquet(
            temp_csv,
            output_parquet
        )


    except Exception:

        # ====================================================
        # NẾU LỖI -> XÓA PARQUET LỖI
        # ====================================================

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
    print("✓ SCCT HOÀN TẤT")
    print("=" * 80)


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
        "✓ Toàn bộ SCCT cũ trong Output đã được xóa."
    )


    print(
        "✓ File SCCT mới nhất đã được xuất."
    )


    print(
        "✓ Các file loại khác trong Output được giữ nguyên."
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


        print(
            str(e)
        )


        print()


        input(
            "Nhấn Enter để đóng..."
        )


        raise