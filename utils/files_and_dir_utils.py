import json
import pandas as pd

from os import path
from typing import List, Dict



def read_txt_file_in_lines(filepath: str) -> List[str]:
    lines = list()
    if not path.exists(filepath):
        return lines

    with open(filepath, 'r') as f:
        for line in f.readlines():
            lines.append(line.strip())
    return lines


def read_txt_file_as_str(filepath: str) -> str:
    str_data = ""
    if not path.exists(filepath):
        return str_data

    with open(filepath, 'r') as file:
        str_data = file.read()
    return str_data


def write_str_to_txt_file(filepath: str, str_data: str) -> None:
    with open(filepath, 'w') as f:
        f.write(str_data)


def read_csv(csv_file_path: str) -> pd.DataFrame:
    return pd.read_csv(csv_file_path)


def write_csv(data: List, csv_file_path: str) -> None:
    pd.DataFrame(data).to_csv(csv_file_path, header=None, index=False)


def write_str_lines_to_file(lines: List[str], file_path: str) -> None:
    with open(file_path, 'w+') as f:
        for line in lines:
            f.write(line)
            f.write('\n')


def append_to_file(lines: List[str], file_path: str) -> None:
    if len(lines):
        with open(file_path, 'a') as f:
            for line in lines:
                f.write(line.replace('\n', '=nl='))
                f.write('\n')


def read_json(filepath: str):
    if path.exists(filepath):
        with open(filepath, 'r') as inFile:
            return json.loads(inFile.read())


def write_json(data: Dict, filepath: str):
    with open(filepath, 'w') as outfile:
        json.dump(data, outfile, indent=4)
