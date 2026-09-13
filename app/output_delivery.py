from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

try:
    from .converter_core import PROFILES
except ImportError:
    from converter_core import PROFILES


NETWORK_OUTPUT = Path(
    r"\\masan.local\15. Khoi Logistics\15.4 Dat hang & Kiem soat ton kho"
    r"\15.4.4 KSTK WinMart Plus\2.TeamKSTK\02. Kiểm soát ĐH\08. KSDH MN"
    r"\anhntp4\Output"
)

Log = Callable[[str], None]


def publish_to_network(
    output_file: Path,
    profile_name: str,
    logger: Log = print,
    network_output: Path = NETWORK_OUTPUT,
) -> Path:
    output_file = Path(output_file)
    profile = PROFILES[profile_name]

    if not output_file.is_file():
        raise FileNotFoundError(f"Không tìm thấy Parquet local: {output_file}")

    if not network_output.exists() or not network_output.is_dir():
        raise FileNotFoundError(f"Không truy cập được thư mục Network: {network_output}")

    old_files = list(network_output.glob(f"{profile.prefix}*.parquet"))
    for old_file in old_files:
        old_file.unlink()
        logger(f"Đã xóa output cũ trên Network: {old_file.name}")

    destination = network_output / output_file.name
    shutil.copy2(output_file, destination)
    logger(f"Đã copy {destination.name} lên Network")
    return destination
