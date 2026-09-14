from __future__ import annotations

import csv
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

import duckdb


Log = Callable[[str], None]



@dataclass(frozen=True)
class ConverterProfile:
    key: str
    title: str
    prefix: str
    input_folder: Path
    delimiter: str
    timestamp_format: str
    all_varchar: bool
    has_header: bool
    row_group_size: str | None = None
    progress_every: int = 100000


DEFAULT_OUTPUT_FOLDER = Path(r"D:\ClosingStockAutomation\CSVtoParquet")
DEFAULT_INPUT_FOLDER = Path(r"\\masan.local\15. Khoi Logistics\99.15.1. Inputdata")

PROFILES = {
    "30D_SALES": ConverterProfile(
        key="30D_SALES",
        title="30D SALES",
        prefix="30D_SALES_",
        input_folder=DEFAULT_INPUT_FOLDER,
        delimiter=";",
        timestamp_format="%Y%m%d%H%M%S",
        all_varchar=True,
        has_header=False,
        row_group_size="128MB",
    ),
    "CLOSING_STOCK": ConverterProfile(
        key="CLOSING_STOCK",
        title="CLOSING STOCK",
        prefix="CLOSING_STOCK_",
        input_folder=DEFAULT_INPUT_FOLDER,
        delimiter=",",
        timestamp_format="%Y%m%d%H%M%S",
        all_varchar=False,
        has_header=False,
    ),
    "STOCK_INTRANSIT": ConverterProfile(
        key="STOCK_INTRANSIT",
        title="STOCK INTRANSIT",
        prefix="STOCK_INTRANSIT_",
        input_folder=DEFAULT_INPUT_FOLDER,
        delimiter=";",
        timestamp_format="%Y%m%d%H%M%S",
        all_varchar=True,
        has_header=False,
        row_group_size="128MB",
    ),
    "SCCT": ConverterProfile(
        key="SCCT",
        title="SCCT",
        prefix="SCCT_RAWDATA_LD_WMP_",
        input_folder=Path(r"\\masan.local\15. Khoi Logistics\99.15.9 RAW"),
        delimiter=",",
        timestamp_format="%Y%m%d",
        all_varchar=False,
        has_header=True,
    ),
}


def profiles_for_date(day: datetime | None = None) -> list[tuple[ConverterProfile, str]]:
    value = day or datetime.now()
    return [
        (PROFILES["30D_SALES"], value.strftime("%Y%m%d")),
        (PROFILES["CLOSING_STOCK"], value.strftime("%Y%m%d")),
        (PROFILES["STOCK_INTRANSIT"], value.strftime("%Y%m%d")),
        (PROFILES["SCCT"], value.strftime("%Y%m%d")),
    ]


def get_profile(value: str | None) -> ConverterProfile:
    if not value:
        raise ValueError("Thiếu loại dữ liệu cần convert.")

    normalized = value.upper().strip()
    if normalized in PROFILES:
        return PROFILES[normalized]

    for profile in PROFILES.values():
        if normalized == profile.prefix.rstrip("_") or normalized.startswith(profile.prefix):
            return profile

    raise ValueError(f"Không hỗ trợ loại dữ liệu: {value}")


def format_bytes(value: int | float) -> str:
    amount = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024:
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} PB"


def _log(logger: Log, message: str) -> None:
    logger(message)


def _parse_line(line: str, delimiter: str) -> list[str]:
    line = line.rstrip("\r\n")
    fields: list[str] = []
    current: list[str] = []
    in_quotes = False
    index = 0

    while index < len(line):
        char = line[index]
        if char == '"':
            if in_quotes:
                if index + 1 < len(line) and line[index + 1] == '"':
                    current.append('"')
                    index += 2
                    continue
                if index + 1 == len(line) or line[index + 1] == delimiter:
                    in_quotes = False
                    index += 1
                    continue
                current.append('"')
                index += 1
                continue
            if not current:
                in_quotes = True
                index += 1
                continue
            current.append('"')
            index += 1
            continue

        if char == delimiter and not in_quotes:
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
        index += 1

    fields.append("".join(current))
    return fields


def normalize_csv(
    input_file: Path,
    temp_csv: Path,
    profile: ConverterProfile,
    logger: Log = print,
) -> int:
    _log(logger, f"Normalize {input_file.name} (delimiter={profile.delimiter})")
    row_count = 0
    temp_csv.parent.mkdir(parents=True, exist_ok=True)

    with input_file.open("r", encoding="utf-8-sig", errors="replace", newline="") as source:
        with temp_csv.open("w", encoding="utf-8", newline="") as target:
            writer = csv.writer(target, delimiter=profile.delimiter, quotechar='"', lineterminator="\n")
            for line_number, line in enumerate(source, 1):
                try:
                    writer.writerow(_parse_line(line, profile.delimiter))
                except Exception as exc:
                    raise RuntimeError(f"Lỗi tại dòng {line_number}: {exc}") from exc
                row_count += 1
                if row_count % profile.progress_every == 0:
                    _log(logger, f"Đã normalize {row_count:,} dòng...")

    _log(logger, f"Normalize xong: {row_count:,} dòng")
    return row_count


def inspect_csv(input_file: Path, profile: ConverterProfile) -> dict:
    rows = 0
    columns = 0
    preview = []
    with input_file.open("r", encoding="utf-8-sig", errors="replace", newline="") as source:
        for line in source:
            fields = _parse_line(line, profile.delimiter)
            if not fields or (len(fields) == 1 and not fields[0]):
                continue
            if len(preview) < 20:
                preview.append(fields)
            columns = max(columns, len(fields))
            rows += 1

    if profile.has_header and rows:
        rows -= 1
        preview = preview[1:]

    return {
        "rows": rows,
        "columns": columns,
        "size": input_file.stat().st_size,
        "size_label": format_bytes(input_file.stat().st_size),
        "preview": preview,
    }


def find_latest_file(
    profile: ConverterProfile,
    input_folder: Path | None = None,
    logger: Log = print,
) -> Path:
    folder = input_folder or profile.input_folder
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Folder nguồn không tồn tại: {folder}")

    regex = re.compile(
        rf"^{re.escape(profile.prefix)}(\d{{{len(datetime.now().strftime(profile.timestamp_format))}}})\.csv$",
        re.IGNORECASE,
    )
    latest: tuple[datetime, Path] | None = None
    for candidate in folder.glob(f"{profile.prefix}*.csv"):
        match = regex.match(candidate.name)
        if not match:
            continue
        try:
            stamp = datetime.strptime(match.group(1), profile.timestamp_format)
        except ValueError:
            continue
        if latest is None or stamp > latest[0]:
            latest = (stamp, candidate)

    if latest is None:
        raise FileNotFoundError(f"Không tìm thấy file {profile.title} đúng format trong {folder}")

    _log(logger, f"File {profile.title} mới nhất: {latest[1].name}")
    return latest[1]


def clear_old_output(output_folder: Path, profile: ConverterProfile, logger: Log = print) -> None:
    output_folder.mkdir(parents=True, exist_ok=True)
    old_files = list(output_folder.glob(f"{profile.prefix}*.parquet"))
    for old_file in old_files:
        old_file.unlink()
    _log(logger, f"Đã xóa {len(old_files)} file Parquet cũ của {profile.title}")


def _sql_path(path: Path) -> str:
    return path.as_posix().replace("'", "''")


def convert_normalized(
    normalized_csv: Path,
    output_parquet: Path,
    profile: ConverterProfile,
    logger: Log = print,
) -> dict:
    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    source = _sql_path(normalized_csv)
    destination = _sql_path(output_parquet)
    options = [
        f"header = {'true' if profile.has_header else 'false'}",
        f"delim = '{profile.delimiter}'",
        "strict_mode = true",
        "parallel = true",
    ]

    if profile.all_varchar:
        with normalized_csv.open("r", encoding="utf-8", newline="") as handle:
            first_row = next(csv.reader(handle, delimiter=profile.delimiter), None)
        if not first_row:
            raise ValueError("CSV không có dữ liệu.")
        columns = {f"column{i}": "VARCHAR" for i in range(1, len(first_row) + 1)}
        options.extend(["auto_detect = false", f"columns = {columns}", "quote = '\"'", "escape = '\"'"])
    else:
        options.append("auto_detect = true")

    row_group = f", ROW_GROUP_SIZE_BYTES '{profile.row_group_size}'" if profile.row_group_size else ""
    query = f"""
        COPY (SELECT * FROM read_csv('{source}', {', '.join(options)}))
        TO '{destination}' (FORMAT PARQUET, COMPRESSION SNAPPY{row_group});
    """

    connection = duckdb.connect(database=":memory:")
    try:
        connection.execute(f"SET threads TO {min(os.cpu_count() or 4, 16)}")
        connection.execute("SET preserve_insertion_order = false")
        _log(logger, f"Đang convert {profile.title} sang Parquet...")
        connection.execute(query)
        row_count = connection.execute(
            f"SELECT COUNT(*) FROM read_parquet('{destination}')"
        ).fetchone()[0]
        column_count = len(connection.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{destination}')"
        ).fetchall())
        size = output_parquet.stat().st_size
        result = {
            "profile": profile.key,
            "input": str(normalized_csv),
            "output": str(output_parquet),
            "rows": row_count,
            "columns": column_count,
            "size": size,
            "size_label": format_bytes(size),
        }
        _log(logger, f"Hoàn tất {profile.title}: {row_count:,} dòng, {format_bytes(size)}")
        return result
    finally:
        connection.close()


def convert_file(
    input_file: Path,
    output_folder: Path = DEFAULT_OUTPUT_FOLDER,
    profile_name: str | None = None,
    logger: Log = print,
    clean_old: bool = True,
) -> dict:
    input_file = Path(input_file)
    profile = get_profile(profile_name or input_file.name)
    if not input_file.is_file():
        raise FileNotFoundError(f"Không tìm thấy file: {input_file}")
    output_folder.mkdir(parents=True, exist_ok=True)
    if clean_old:
        clear_old_output(output_folder, profile, logger)

    output_parquet = output_folder / f"{input_file.stem}.parquet"
    temp_csv = output_folder / f"_{profile.key}_normalized.tmp.csv"
    if temp_csv.exists():
        temp_csv.unlink()

    started_at = time.perf_counter()
    csv_info = inspect_csv(input_file, profile)
    try:
        normalize_csv(input_file, temp_csv, profile, logger)
        result = convert_normalized(temp_csv, output_parquet, profile, logger)
        result["csv"] = csv_info
        result["parquet"] = {
            "rows": result["rows"],
            "columns": result["columns"],
            "size": result["size"],
            "size_label": result["size_label"],
            "preview": read_parquet_preview(output_parquet),
            "schema": read_parquet_schema(output_parquet),
        }
        result["compression_ratio"] = round(
            (1 - result["size"] / csv_info["size"]) * 100, 1
        ) if csv_info["size"] else 0
        result["elapsed_seconds"] = round(time.perf_counter() - started_at, 2)
        return result
    except Exception:
        if output_parquet.exists():
            output_parquet.unlink()
        raise
    finally:
        if temp_csv.exists():
            temp_csv.unlink()


def read_parquet_preview(output_parquet: Path) -> list[list]:
    connection = duckdb.connect(database=":memory:")
    try:
        rows = connection.execute(
            f"SELECT * FROM read_parquet('{_sql_path(output_parquet)}') LIMIT 20"
        ).fetchall()
        return [list(row) for row in rows]
    finally:
        connection.close()


def read_parquet_schema(output_parquet: Path) -> list[dict]:
    connection = duckdb.connect(database=":memory:")
    try:
        return [
            {"name": row[0], "type": row[1]}
            for row in connection.execute(
                f"DESCRIBE SELECT * FROM read_parquet('{_sql_path(output_parquet)}')"
            ).fetchall()
        ]
    finally:
        connection.close()


def inspect_conversion(input_file: Path, output_parquet: Path, profile_name: str) -> dict:
    profile = get_profile(profile_name)
    csv_info = inspect_csv(Path(input_file), profile)
    connection = duckdb.connect(database=":memory:")
    try:
        row_count = connection.execute(
            f"SELECT COUNT(*) FROM read_parquet('{_sql_path(Path(output_parquet))}')"
        ).fetchone()[0]
        column_count = len(connection.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{_sql_path(Path(output_parquet))}')"
        ).fetchall())
        parquet_path = Path(output_parquet)
        parquet_info = {
            "rows": row_count,
            "columns": column_count,
            "size": parquet_path.stat().st_size,
            "size_label": format_bytes(parquet_path.stat().st_size),
            "preview": read_parquet_preview(parquet_path),
            "schema": read_parquet_schema(parquet_path),
        }
    finally:
        connection.close()

    return {
        "csv": csv_info,
        "parquet": parquet_info,
        "output": str(output_parquet),
        "compression_ratio": round((1 - parquet_info["size"] / csv_info["size"]) * 100, 1) if csv_info["size"] else 0,
    }


def run_profile(
    profile_name: str,
    output_folder: Path = DEFAULT_OUTPUT_FOLDER,
    input_folder: Path | None = None,
    logger: Log = print,
) -> dict:
    profile = get_profile(profile_name)
    input_file = find_latest_file(profile, input_folder, logger)
    return convert_file(input_file, output_folder, profile.key, logger)
