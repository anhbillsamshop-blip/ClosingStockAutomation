from pathlib import Path
from datetime import datetime, timedelta
import time
import re
import os
import csv
import shutil

import duckdb
import pyarrow as pa
import pyarrow.csv as pv
import pyarrow.parquet as pq


# ============================================================
# CONFIG
# ============================================================

# ------------------------------------------------------------
# Folder chứa 3 file:
# CLOSING_STOCK
# 30D_SALE
# STOCK_INTRANSIT
# ------------------------------------------------------------

INPUT_FOLDER = Path(
    r"\\masan.local\15. Khoi Logistics\99.15.1. Inputdata"
)


# ------------------------------------------------------------
# Folder riêng của SCCT
# ------------------------------------------------------------

SCCT_FOLDER = Path(
    r"\\masan.local\15. Khoi Logistics\99.15.1. Inputdata\99.15.9 RAW"
)


# ------------------------------------------------------------
# Output
# ------------------------------------------------------------

OUTPUT_FOLDER = Path(
    r"\\masan.local\15. Khoi Logistics\15.4 Dat hang & Kiem soat ton kho\15.4.4 KSTK WinMart Plus\2.TeamKSTK\02. Kiểm soát ĐH\08. KSDH MN\anhntp4\Output"
)

# ------------------------------------------------------------
# TEMP PARQUET LOCAL
#
# DuckDB sẽ ghi Parquet vào SSD local trước.
# Chỉ sau khi convert + kiểm tra xong mới copy 1 lần lên network.
# ------------------------------------------------------------

LOCAL_TEMP_FOLDER = Path(
    r"C:\ClosingStockAutomation\duckdb_temp"
)


# ============================================================
# CSV STREAMING CONFIG
# ============================================================

# Mỗi lần đọc khoảng 64 MB vào RAM.
#
# Nếu máy mạnh:
# 128 * 1024 * 1024
#
# Nhưng với file nằm trên network,
# 64 MB là mức an toàn để bắt đầu.
# ============================================================

BLOCK_SIZE = 64 * 1024 * 1024


# ============================================================
# LOG PROGRESS
# ============================================================

# Cứ xử lý xong số batch này thì in progress.
#
# 1 batch khoảng 64 MB nên:
#
# 5 batch ≈ 320 MB
#
# ============================================================

PROGRESS_EVERY_BATCH = 5


# ============================================================
# DANH SÁCH FILE
# ============================================================

FILE_TYPES = [

    {
        "name": "CLOSING_STOCK",
        "prefix": "CLOSING_STOCK_",
        "type": "timestamp",
        "folder": INPUT_FOLDER
    },

    {
        "name": "30D_SALES",
        "prefix": "30D_SALES_",
        "type": "timestamp",
        "folder": INPUT_FOLDER
    },

    {
        "name": "STOCK_INTRANSIT",
        "prefix": "STOCK_INTRANSIT_",
        "type": "timestamp",
        "folder": INPUT_FOLDER
    },

    {
        "name": "SCCT_RAWDATA_LD_WMP",
        "prefix": "SCCT_RAWDATA_LD_WMP_",
        "type": "date",
        "folder": SCCT_FOLDER
    }

]


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
# FORMAT TIME
# ============================================================

def format_seconds(seconds):

    seconds = int(seconds)

    hours = seconds // 3600

    minutes = (
        seconds % 3600
    ) // 60

    secs = seconds % 60

    if hours > 0:

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{secs:02d}"
        )

    return (
        f"{minutes:02d}:"
        f"{secs:02d}"
    )


# ============================================================
# TẠO OUTPUT FOLDER
# ============================================================

def create_output_folder():

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# KIỂM TRA FOLDER
# ============================================================

def check_folder(folder):

    print()
    print(
        "Folder:"
    )

    print(
        folder
    )

    if not folder.exists():

        print(
            "!!! FOLDER KHÔNG TỒN TẠI !!!"
        )

        return False


    if not folder.is_dir():

        print(
            "!!! ĐƯỜNG DẪN KHÔNG PHẢI FOLDER !!!"
        )

        return False


    print(
        "✓ Folder OK"
    )

    return True


# ============================================================
# TÌM FILE MỚI NHẤT
# ============================================================

def find_latest_file(
    prefix,
    file_type,
    folder
):

    print()
    print("=" * 80)

    print(
        f"TÌM FILE: {prefix}"
    )

    print("=" * 80)


    print()
    print(
        "Folder tìm kiếm:"
    )

    print(
        folder
    )


    # --------------------------------------------------------
    # Kiểm tra folder
    # --------------------------------------------------------

    if not check_folder(folder):

        return None


    pattern = f"{prefix}*.csv"


    try:

        files = list(
            folder.glob(pattern)
        )

    except Exception as e:

        print(
            f"Lỗi khi đọc folder: {e}"
        )

        return None


    print()
    print(
        f"Số file tìm thấy: "
        f"{len(files)}"
    )


    if not files:

        print(
            "Không tìm thấy file."
        )

        return None


    # ========================================================
    # PREFIX_YYYYMMDDHHMMSS.csv
    # ========================================================

    if file_type == "timestamp":

        regex = re.compile(
            rf"^{re.escape(prefix)}(\d{{14}})\.csv$",
            re.IGNORECASE
        )


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


        if latest_file is None:

            print(
                "Không có file đúng format "
                "YYYYMMDDHHMMSS."
            )

            return None


        print()
        print(
            f"✓ File mới nhất:"
        )

        print(
            latest_file.name
        )


        return latest_file


    # ========================================================
    # SCCT:
    #
    # SCCT_RAWDATA_LD_WMP_YYYYMMDD.csv
    # ========================================================

    if file_type == "date":

        regex = re.compile(
            rf"^{re.escape(prefix)}(\d{{8}})\.csv$",
            re.IGNORECASE
        )


        latest_file = None

        latest_date = None


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


        if latest_file is None:

            print(
                "Không có file SCCT đúng format."
            )

            return None


        print()
        print(
            f"✓ File SCCT WMP mới nhất:"
        )

        print(
            latest_file.name
        )


        print(
            f"✓ Folder:"
        )

        print(
            latest_file.parent
        )


        return latest_file


    return None


# ============================================================
# KIỂM TRA FILE ĐÃ COPY XONG
# ============================================================

def wait_for_file_ready(
    file_path,
    checks=3,
    wait_seconds=5
):

    print()
    print(
        "Kiểm tra file đã hoàn tất..."
    )


    try:

        previous_size = (
            file_path.stat().st_size
        )


        for i in range(checks):

            time.sleep(
                wait_seconds
            )


            current_size = (
                file_path.stat().st_size
            )


            print(
                f"  Check {i + 1}: "
                f"{format_bytes(current_size)}"
            )


            if current_size != previous_size:

                previous_size = current_size

                print(
                    "  → File vẫn đang thay đổi."
                )

                continue


            print(
                "✓ File đã ổn định."
            )

            return True


        print(
            "!!! File vẫn đang thay đổi."
        )

        return False


    except Exception as e:

        print(
            f"Không thể kiểm tra file: {e}"
        )

        return False


# ============================================================
# CSV → PARQUET BẰNG DUCKDB
# ============================================================

def _sql_string(value):
    """Escape Python string thành SQL string literal."""
    return "'" + str(value).replace("'", "''") + "'"


def convert_csv_to_parquet(
    input_file,
    prefix
):

    create_output_folder()

    # ========================================================
    # FILE SIZE
    # ========================================================

    file_size = input_file.stat().st_size

    # ========================================================
    # OUTPUT
    # ========================================================

    output_file = (
        OUTPUT_FOLDER /
        f"{input_file.stem}.parquet"
    )

    # Parquet tạm được tạo LOCAL.
    LOCAL_TEMP_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    local_temp_file = (
        LOCAL_TEMP_FOLDER /
        f"{input_file.stem}.tmp.parquet"
    )

    # File tạm NETWORK chỉ xuất hiện sau khi local Parquet hoàn tất.
    network_temp_file = (
        OUTPUT_FOLDER /
        f"{input_file.stem}.network.tmp.parquet"
    )

    print()
    print("=" * 80)
    print("CONVERT CSV → PARQUET (DUCKDB LOCAL SSD V2.1)")
    print("=" * 80)

    print()
    print("Input:")
    print(input_file)

    print()
    print("Local temp:")
    print(local_temp_file)

    print()
    print("Final output:")
    print(output_file)

    print()
    print(f"File size: {format_bytes(file_size)}")

    # ========================================================
    # NẾU PARQUET ĐÃ CÓ
    # ========================================================

    if output_file.exists():

        print()
        print("✓ Parquet đã tồn tại.")
        print("→ Không convert lại.")

        return output_file

    # ========================================================
    # KIỂM TRA FILE NGUỒN
    # ========================================================

    if not wait_for_file_ready(input_file):

        raise Exception(
            "File nguồn chưa ổn định."
        )

    file_size = input_file.stat().st_size

    # ========================================================
    # KIỂM TRA DISK LOCAL
    # ========================================================

    disk = shutil.disk_usage(LOCAL_TEMP_FOLDER)

    required_space = int(file_size * 1.50)

    if disk.free < required_space:

        raise Exception(
            "Ổ C: không đủ dung lượng trống để tạo Parquet tạm local.\n"
            f"Còn trống : {format_bytes(disk.free)}\n"
            f"Khuyến nghị: ít nhất {format_bytes(required_space)}"
        )

    # ========================================================
    # XÓA TEMP CŨ
    # ========================================================

    for old_temp in (local_temp_file, network_temp_file):

        if old_temp.exists():

            try:
                old_temp.unlink()
            except Exception as e:
                raise Exception(
                    f"Không thể xóa file temp:\n{old_temp}\n{e}"
                )

    # ========================================================
    # XÁC ĐỊNH SỐ CỘT TỪ DÒNG DATA ĐẦU TIÊN
    #
    # Bản V2 bị Columns = 1 vì dùng DESCRIBE trên read_csv.
    # Ở đây không DESCRIBE và không đọc lại CSV để dò schema.
    # Chỉ đọc đúng dòng đầu tiên bằng Python csv.reader.
    # Sau đó truyền names + all_varchar trực tiếp cho DuckDB.
    # ========================================================

    try:

        with open(
            input_file,
            "r",
            encoding="utf-8-sig",
            errors="replace",
            newline=""
        ) as f:

            csv_reader = csv.reader(
                f,
                delimiter=",",
                quotechar='"'
            )

            first_row = next(csv_reader, None)

    except Exception as e:

        raise Exception(
            f"Không thể đọc dòng đầu tiên của CSV để xác định số cột: {e}"
        )

    if not first_row:

        raise Exception(
            "CSV không có dữ liệu."
        )

    column_count = len(first_row)

    if column_count <= 0:

        raise Exception(
            "Không xác định được số cột CSV."
        )

    column_names = [
        f"column{i}"
        for i in range(1, column_count + 1)
    ]

    # DuckDB read_csv(auto_detect=false) requires the `columns` option.
    # Build an explicit VARCHAR schema so every field stays text and
    # the output keeps the original column1, column2, ... logic.
    columns_sql = "{" + ", ".join(
        _sql_string(name) + ": 'VARCHAR'"
        for name in column_names
    ) + "}"

    print()
    print("────────────────────────────────────────")
    print(f"Columns   : {column_count}")
    print(f"File size : {format_bytes(file_size)}")
    print("Engine    : DuckDB")

    cpu_count = os.cpu_count() or 4

    # Không dùng toàn bộ logical CPU nếu máy có quá nhiều thread.
    # 16 là mức trần để tránh oversubscription trên network CSV.
    threads = min(cpu_count, 16)

    print(f"Threads   : {threads}")
    print("Write     : LOCAL SSD")
    print("Network   : COPY AFTER CONVERT")
    print("Delimiter : ,")
    print("Types     : ALL VARCHAR")
    print("────────────────────────────────────────")

    # ========================================================
    # DUCKDB CONFIG
    # ========================================================

    con = duckdb.connect(database=":memory:")

    try:

        con.execute(f"SET threads TO {threads}")

        # Power BI không cần thứ tự dòng của CSV.
        # DuckDB có thể parallelize/export linh hoạt hơn.
        con.execute(
            "SET preserve_insertion_order = false"
        )

        con.execute(
            f"SET temp_directory = {_sql_string(str(LOCAL_TEMP_FOLDER))}"
        )

        csv_path_sql = _sql_string(input_file)
        local_path_sql = _sql_string(local_temp_file)

        # ====================================================
        # READ CSV
        #
        # Không auto-detect schema.
        # Không DESCRIBE.
        # Không đọc CSV lần thứ hai để lấy schema.
        # names + all_varchar giúp giữ nguyên logic column1...
        # ====================================================

        read_sql = f"""
            read_csv(
                {csv_path_sql},
                auto_detect = false,
                header = false,
                delim = ',',
                quote = '"',
                escape = '"',
                columns = {columns_sql},
                parallel = true,
                null_padding = false,
                strict_mode = true
            )
        """

        # ====================================================
        # CONVERT LOCAL
        # ====================================================

        print()
        print("Đang convert CSV → Parquet trên ổ C...")

        start_time = time.time()

        copy_sql = f"""
            COPY (
                SELECT *
                FROM {read_sql}
            )
            TO {local_path_sql}
            (
                FORMAT PARQUET,
                COMPRESSION SNAPPY,
                USE_TMP_FILE FALSE,
                ROW_GROUP_SIZE_BYTES '128MB'
            )
        """

        con.execute(copy_sql)

        convert_elapsed = time.time() - start_time

        # ====================================================
        # KIỂM TRA LOCAL PARQUET
        # ====================================================

        print()
        print("Đang kiểm tra Parquet local...")

        parquet_file = pq.ParquetFile(local_temp_file)
        parquet_rows = parquet_file.metadata.num_rows

        if parquet_rows <= 0:

            raise Exception(
                "Parquet không có dữ liệu."
            )

        local_parquet_size = local_temp_file.stat().st_size

        print(f"✓ Rows: {parquet_rows:,}")
        print(
            f"✓ Local Parquet size: "
            f"{format_bytes(local_parquet_size)}"
        )

        # ====================================================
        # COPY LOCAL → NETWORK
        # ====================================================

        print()
        print("Đang copy Parquet hoàn chỉnh lên network...")

        network_start = time.time()

        shutil.copyfile(
            local_temp_file,
            network_temp_file
        )

        network_elapsed = time.time() - network_start

        # ====================================================
        # KIỂM TRA FILE NETWORK
        # ====================================================

        print()
        print("Đang kiểm tra Parquet trên network...")

        network_parquet = pq.ParquetFile(
            network_temp_file
        )

        network_rows = network_parquet.metadata.num_rows

        if network_rows != parquet_rows:

            raise Exception(
                f"Số dòng không khớp sau khi copy:\n"
                f"Local={parquet_rows:,}\n"
                f"Network={network_rows:,}"
            )

        # ====================================================
        # TEMP NETWORK → OUTPUT CHÍNH THỨC
        # ====================================================

        if output_file.exists():

            output_file.unlink()

        network_temp_file.replace(output_file)

        # ====================================================
        # XÓA PARQUET CŨ CÙNG LOẠI
        # ====================================================

        print()
        print("Đang dọn Parquet cũ...")

        deleted_count = 0

        for old_file in OUTPUT_FOLDER.glob(
            f"{prefix}*.parquet"
        ):

            if old_file.resolve() == output_file.resolve():
                continue

            try:

                old_file.unlink()

                print(
                    f"  Đã xóa: {old_file.name}"
                )

                deleted_count += 1

            except Exception as e:

                print(
                    f"  Không thể xóa {old_file.name}: {e}"
                )

        # ====================================================
        # FINAL PROGRESS
        # ====================================================

        total_elapsed = convert_elapsed + network_elapsed

        convert_speed = (
            file_size / convert_elapsed
            if convert_elapsed > 0
            else 0
        )

        network_speed = (
            local_parquet_size / network_elapsed
            if network_elapsed > 0
            else 0
        )

        print()
        print("DUCKDB PROGRESS")
        print("────────────────────────────────────────")
        print(f"CSV size          : {format_bytes(file_size)}")
        print(f"Columns           : {column_count}")
        print(f"Rows              : {parquet_rows:,}")
        print(f"Local Parquet     : {format_bytes(local_parquet_size)}")
        print(
            f"CSV → Parquet     : "
            f"{format_bytes(convert_speed)}/s"
        )
        print(
            f"Convert time      : "
            f"{format_seconds(convert_elapsed)}"
        )
        print(
            f"Parquet → Network : "
            f"{format_bytes(network_speed)}/s"
        )
        print(
            f"Network copy time : "
            f"{format_seconds(network_elapsed)}"
        )
        print(
            f"TOTAL             : "
            f"{format_seconds(total_elapsed)}"
        )
        print("────────────────────────────────────────")

        print()
        print("=" * 80)
        print("✓ CONVERT THÀNH CÔNG")
        print("=" * 80)
        print(f"Rows   : {parquet_rows:,}")
        print(f"Output : {output_file}")
        print(f"Deleted old parquet: {deleted_count}")

        # Xóa local temp sau khi output network đã hoàn tất.
        try:
            local_temp_file.unlink()
        except Exception:
            pass

        return output_file

    except Exception:

        if local_temp_file.exists():

            try:
                local_temp_file.unlink()
            except Exception:
                pass

        if network_temp_file.exists():

            try:
                network_temp_file.unlink()
            except Exception:
                pass

        raise

    finally:

        try:
            con.close()
        except Exception:
            pass


# ============================================================
# CHẠY TOÀN BỘ 4 FILE
# ============================================================

def run_all():

    print()
    print()
    print("=" * 80)


    print(
        "BẮT ĐẦU WORKFLOW"
    )


    print(
        datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )


    print("=" * 80)


    results = []


    # ========================================================
    # CHẠY TỪNG FILE
    # ========================================================

    for config in FILE_TYPES:

        name = config["name"]

        prefix = config["prefix"]

        file_type = config["type"]

        folder = config["folder"]


        print()
        print()
        print(
            "#" * 80
        )


        print(
            f"ĐANG XỬ LÝ: {name}"
        )


        print(
            "#" * 80
        )


        input_file = None


        try:

            # ------------------------------------------------
            # Tìm file
            # ------------------------------------------------

            input_file = find_latest_file(

                prefix=prefix,

                file_type=file_type,

                folder=folder

            )


            if input_file is None:

                results.append({

                    "name": name,

                    "status": "NOT FOUND"

                })


                continue


            # ------------------------------------------------
            # Convert
            # ------------------------------------------------

            output_file = (
                convert_csv_to_parquet(

                    input_file=input_file,

                    prefix=prefix

                )
            )


            results.append({

                "name": name,

                "status": "SUCCESS",

                "input": input_file,

                "output": output_file

            })


        except Exception as e:

            print()
            print(
                f"!!! LỖI {name} !!!"
            )


            print(
                str(e)
            )


            results.append({

                "name": name,

                "status": "ERROR",

                "input": input_file,

                "error": str(e)

            })


    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print()
    print("=" * 80)


    print(
        "KẾT QUẢ WORKFLOW"
    )


    print("=" * 80)


    for result in results:

        print()
        print(
            result["name"]
        )


        print(
            f"  Status: "
            f"{result['status']}"
        )


        if result.get("input"):

            print(
                f"  Input : "
                f"{result['input'].name}"
            )


        if result.get("output"):

            print(
                f"  Output: "
                f"{result['output'].name}"
            )


    print()
    print("=" * 80)


    print(
        "HOÀN TẤT WORKFLOW"
    )


    print(
        datetime.now().strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )


    print("=" * 80)


# ============================================================
# TÍNH THỜI GIAN ĐẾN 10:00
# ============================================================

def seconds_until_10am():

    now = datetime.now()


    target = now.replace(

        hour=10,

        minute=0,

        second=0,

        microsecond=0

    )


    if now >= target:

        target += timedelta(
            days=1
        )


    return (

        (
            target - now
        ).total_seconds(),

        target

    )


# ============================================================
# SCHEDULER
# ============================================================

def scheduler():

    print()
    print("=" * 80)


    print(
        "DATA AUTOMATION"
    )


    print(
        "BACKGROUND MODE"
    )


    print("=" * 80)


    print()
    print(
        "Tự động chạy mỗi ngày lúc 10:00."
    )


    while True:

        seconds, target = (
            seconds_until_10am()
        )


        print()
        print(
            f"Lần chạy tiếp theo: "
            f"{target.strftime('%d/%m/%Y %H:%M:%S')}"
        )


        print(
            f"Còn khoảng "
            f"{seconds / 3600:.2f} giờ."
        )


        # ----------------------------------------------------
        # Chờ đến 10h
        # ----------------------------------------------------

        time.sleep(
            seconds
        )


        # ----------------------------------------------------
        # Chạy workflow
        # ----------------------------------------------------

        try:

            run_all()


        except Exception as e:

            print()
            print(
                "!!! WORKFLOW CÓ LỖI !!!"
            )


            print(
                str(e)
            )


        # ----------------------------------------------------
        # Tránh chạy lại ngay
        # ----------------------------------------------------

        time.sleep(
            60
        )


# ============================================================
# MENU
# ============================================================

def main():

    print()
    print("=" * 80)


    print(
        "DATA AUTOMATION"
    )


    print("=" * 80)


    print()
    print(
        "1. CHẠY NGAY"
    )


    print(
        "2. CHẠY NỀN - TỰ ĐỘNG 10:00"
    )


    print()


    choice = input(
        "Chọn chế độ (1/2): "
    ).strip()


    if choice == "1":

        print()
        print(
            "→ CHẠY NGAY"
        )


        run_all()


    elif choice == "2":

        print()
        print(
            "→ CHẠY NỀN"
        )


        scheduler()


    else:

        print(
            "Lựa chọn không hợp lệ."
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()