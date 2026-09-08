import subprocess
import sys
import shutil
from pathlib import Path


# ============================================================
# CẤU HÌNH
# ============================================================

# Thư mục chứa 4 file Python hiện tại
APP_FOLDER = Path(__file__).resolve().parent

# 4 chương trình con sẽ chạy lần lượt
PYTHON_FILES = [
    "30D_sales.py",
    "closing.stock.py",
    "stock_intransit.py",
    "scct.py",
]

# Thư mục Output trung gian trên ổ D
LOCAL_OUTPUT = Path(r"D:\ClosingStockAutomation\CSVtoParquet")

# Thư mục Output cuối cùng trên network
NETWORK_OUTPUT = Path(
    r"\\masan.local\15. Khoi Logistics\15.4 Dat hang & Kiem soat ton kho"
    r"\15.4.4 KSTK WinMart Plus\2.TeamKSTK\02. Kiểm soát ĐH\08. KSDH MN"
    r"\anhntp4\Output"
)


# ============================================================
# CẤU HÌNH FILE OUTPUT THEO TỪNG LOẠI
# ============================================================

OUTPUT_RULES = [
    {
        "name": "30D SALES",
        "prefix": "30D_SALES_",
    },
    {
        "name": "CLOSING STOCK",
        "prefix": "CLOSING_STOCK_",
    },
    {
        "name": "STOCK INTRANSIT",
        "prefix": "STOCK_INTRANSIT_",
    },
    {
        "name": "SCCT",
        "prefix": "SCCT_RAWDATA_LD_WMP_",
    },
]


# ============================================================
# HÀM CHẠY 1 FILE PYTHON
# ============================================================

def run_python_file(filename):
    script_path = APP_FOLDER / filename

    if not script_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file Python: {script_path}"
        )

    print()
    print("=" * 80)
    print(f"ĐANG CHẠY: {filename}")
    print("=" * 80)

    # Gửi sẵn Enter để xử lý đoạn:
    # input("Nhấn Enter để đóng...")
    # trong các file con.
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(APP_FOLDER),
        input="\n",
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"File {filename} chạy KHÔNG thành công. "
            f"Return code = {result.returncode}"
        )

    print(f"✓ {filename} chạy thành công.")


# ============================================================
# TÌM FILE PARQUET MỚI NHẤT CỦA TỪNG LOẠI TRÊN Ổ D
# ============================================================

def find_latest_local_output(prefix):
    files = list(LOCAL_OUTPUT.glob(f"{prefix}*.parquet"))

    if not files:
        return None

    # Ưu tiên file có thời gian sửa đổi mới nhất.
    # Trong trường hợp các file được tạo liên tiếp trong cùng một lần chạy,
    # file mới xuất ra sẽ được chọn.
    return max(files, key=lambda p: p.stat().st_mtime)


# ============================================================
# XÓA OUTPUT CŨ TRÊN NETWORK - CHỈ ĐÚNG LOẠI
# ============================================================

def clear_network_old_files(prefix):
    old_files = list(NETWORK_OUTPUT.glob(f"{prefix}*.parquet"))

    for old_file in old_files:
        try:
            old_file.unlink()
            print(f"  ✓ Đã xóa output cũ: {old_file.name}")
        except Exception as e:
            raise RuntimeError(
                f"Không thể xóa file cũ trên Network: "
                f"{old_file}\nLỗi: {e}"
            )


# ============================================================
# COPY FILE MỚI NHẤT TỪ D -> NETWORK
# ============================================================

def copy_latest_to_network(rule):
    prefix = rule["prefix"]
    name = rule["name"]

    print()
    print("-" * 80)
    print(f"COPY {name}")
    print("-" * 80)

    latest_file = find_latest_local_output(prefix)

    if latest_file is None:
        raise FileNotFoundError(
            f"Không tìm thấy file output {name} với prefix "
            f"{prefix} trong:\n{LOCAL_OUTPUT}"
        )

    print(f"File mới nhất trên D: {latest_file.name}")

    # Chỉ xóa các file cùng loại trên Network.
    # Không đụng vào output của 3 loại còn lại.
    clear_network_old_files(prefix)

    destination = NETWORK_OUTPUT / latest_file.name

    try:
        shutil.copy2(latest_file, destination)
    except Exception as e:
        raise RuntimeError(
            f"Không thể copy file:\n"
            f"  Từ: {latest_file}\n"
            f"  Đến: {destination}\n"
            f"Lỗi: {e}"
        )

    print(f"✓ Đã copy: {latest_file.name}")
    print(f"✓ Network: {destination}")


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("=" * 80)
    print("BẮT ĐẦU CHẠY TOÀN BỘ 4 AUTOMATION")
    print("=" * 80)

    print(f"\nThư mục Python:")
    print(f"  {APP_FOLDER}")

    print(f"\nOutput trung gian:")
    print(f"  {LOCAL_OUTPUT}")

    print(f"\nOutput cuối trên Network:")
    print(f"  {NETWORK_OUTPUT}")

    # Tạo thư mục D nếu chưa có
    LOCAL_OUTPUT.mkdir(parents=True, exist_ok=True)

    # Tạo thư mục Network nếu chưa có.
    # Nếu Network không truy cập được thì sẽ báo lỗi tại đây.
    NETWORK_OUTPUT.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # BƯỚC 1: CHẠY 4 FILE PYTHON LẦN LƯỢT
    # --------------------------------------------------------

    for filename in PYTHON_FILES:
        run_python_file(filename)

    # --------------------------------------------------------
    # BƯỚC 2: SAU KHI CẢ 4 FILE CHẠY XONG
    #         COPY TỪ D LÊN NETWORK
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("BẮT ĐẦU COPY OUTPUT LÊN NETWORK")
    print("=" * 80)

    for rule in OUTPUT_RULES:
        copy_latest_to_network(rule)

    # --------------------------------------------------------
    # HOÀN TẤT
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("✓✓✓ HOÀN TẤT TOÀN BỘ ✓✓✓")
    print("=" * 80)
    print()
    print("Đã thực hiện:")
    print("1. Chạy 30D Sales")
    print("2. Chạy Closing Stock")
    print("3. Chạy Stock Intransit")
    print("4. Chạy SCCT")
    print("5. Lấy file Parquet mới nhất từ ổ D")
    print("6. Xóa output cũ CÙNG LOẠI trên Network")
    print("7. Copy file mới nhất lên Network")
    print()
    print("Không xóa file của loại khác.")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print()
        print("=" * 80)
        print("!!! CHƯƠNG TRÌNH DỪNG DO CÓ LỖI !!!")
        print("=" * 80)
        print()
        print(str(e))
        print()
        input("Nhấn Enter để đóng...")
        raise
