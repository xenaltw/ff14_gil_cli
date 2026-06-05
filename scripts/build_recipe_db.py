from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from pathlib import Path


REPO_URL = "https://github.com/thewakingsands/ffxiv-datamining-tc.git"
DEFAULT_REPO_DIR = Path("raw_data/ffxiv-datamining-tc")
DEFAULT_ITEM_CSV = "Item.csv"
DEFAULT_RECIPE_CSV = "Recipe.csv"


def run_cmd(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print("Command failed:", " ".join(cmd), file=sys.stderr)
        if e.stdout:
            print("stdout:", e.stdout, file=sys.stderr)
        if e.stderr:
            print("stderr:", e.stderr, file=sys.stderr)
        raise


def ensure_repo(repo_url: str, repo_dir: Path, force_clone: bool = False) -> None:
    if force_clone and repo_dir.exists():
        shutil.rmtree(repo_dir)

    if not repo_dir.exists():
        repo_dir.parent.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Cloning repo to {repo_dir}")
        run_cmd(["git", "clone", repo_url, str(repo_dir)])
        return

    git_dir = repo_dir / ".git"
    if not git_dir.exists():
        raise RuntimeError(f"{repo_dir} exists but is not a git repo")

    print(f"[INFO] Pulling latest changes in {repo_dir}")
    run_cmd(["git", "pull"], cwd=repo_dir)


def preview_csv_header(csv_path: Path, preview_rows: int = 2) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    print(f"\n[INFO] Previewing: {csv_path}")
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        print("[INFO] Header fields:")
        for idx, field in enumerate(reader.fieldnames or []):
            print(f"  {idx:03d}: {field}")

        print(f"\n[INFO] First {preview_rows} row(s):")
        for i, row in enumerate(reader):
            if i >= preview_rows:
                break
            print(f"--- row {i+1} ---")
            for k, v in row.items():
                print(f"{k} = {v}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Fetch FFXIV datamining CSVs and preview Item/Recipe schema."
    )
    parser.add_argument(
        "--repo-url",
        default=REPO_URL,
        help="Git repository URL for ffxiv-datamining-tc",
    )
    parser.add_argument(
        "--repo-dir",
        type=Path,
        default=DEFAULT_REPO_DIR,
        help="Where the datamining repo should be cloned/pulled",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Do not clone/pull repo; use existing local files only",
    )
    parser.add_argument(
        "--force-clone",
        action="store_true",
        help="Delete existing repo dir and clone again",
    )
    parser.add_argument(
        "--item-csv",
        default=DEFAULT_ITEM_CSV,
        help="Relative path to Item CSV inside repo",
    )
    parser.add_argument(
        "--recipe-csv",
        default=DEFAULT_RECIPE_CSV,
        help="Relative path to Recipe CSV inside repo",
    )
    parser.add_argument(
        "--preview-rows",
        type=int,
        default=2,
        help="How many rows to preview from each CSV",
    )
    return parser.parse_args()

def read_exd_csv_rows(csv_path: Path):
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)

        row1 = next(reader)   # 資料編號列
        row2 = next(reader)   # 欄位名稱列
        row3 = next(reader)   # 型態列

        dict_reader = csv.DictReader(f, fieldnames=row2)

        for row in dict_reader:
            yield row


def main():
    args = parse_args()

    repo_dir: Path = args.repo_dir

    if not args.skip_fetch:
        ensure_repo(args.repo_url, repo_dir, force_clone=args.force_clone)
    else:
        print("[INFO] skip-fetch enabled; using local repo only")

    item_csv_path = repo_dir / args.item_csv
    recipe_csv_path = repo_dir / args.recipe_csv

    preview_csv_header(item_csv_path, preview_rows=args.preview_rows)
    preview_csv_header(recipe_csv_path, preview_rows=args.preview_rows)

    print("\n[INFO] Done. Next step: map useful columns into your own JSON schema.")


if __name__ == "__main__":
    main()
