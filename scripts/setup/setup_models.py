"""
Sets up the LLM for Layer A by writing config/robbie_agent/.env.

Asks which model to use (from llm_models.yaml) and where models are stored, shows the
model's licence, then downloads any files not already somewhere under the models folder.
Does nothing if the .env already exists, unless --redo is given.

    python3 scripts/setup/setup_models.py [--redo]
"""
import argparse
import os
import pathlib
import re
import subprocess
import sys

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST = pathlib.Path(__file__).with_name("llm_models.yaml")
ENV = REPO_ROOT / "config" / "robbie_agent" / ".env"
ENV_EXAMPLE = ENV.with_name(".env.example")
DEFAULT_MODELS_DIR = ".models"
SEARCH_DEPTH = 4


def ask(prompt, default=""):
    answer = input(prompt).strip()
    return answer or default


def ask_yes_no(prompt):
    return ask(f"{prompt} [y/N]: ").lower() in ("y", "yes")


def read_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)", line)
        if match:
            values[match[1]] = match[2].strip()
    return values


def write_env(source, target, values):
    """Copies source to target with the given keys set, keeping comments and other keys."""
    lines = source.read_text(encoding="utf-8").splitlines()
    remaining = dict(values)
    for i, line in enumerate(lines):
        match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)=", line)
        if match and match[1] in remaining:
            lines[i] = f"{match[1]}={remaining.pop(match[1])}"
    lines += [f"{key}={value}" for key, value in remaining.items()]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def choose_model(models):
    print("\nWhich LLM should Robbie use?")
    for i, m in enumerate(models, 1):
        print(f"  {i}) {m['name']:<26} {m['size_gb']} GB download, about {m['vram_gb']} GB VRAM, {m['licence']}")
    while True:
        answer = ask("Model [1]: ", "1")
        if answer.isdigit() and 1 <= int(answer) <= len(models):
            return models[int(answer) - 1]
        print(f"Enter a number from 1 to {len(models)}.")


def resolve_dir(folder):
    path = pathlib.Path(folder).expanduser()
    return path if path.is_absolute() else REPO_ROOT / path


def choose_models_dir(current):
    print("\nWhere are AI models stored? Use a shared folder to avoid re-downloading models across projects.")
    while True:
        folder = ask(f"Models folder [{current}], or enter a custom folder (eg: /mnt/c/ai_models): ", current)
        if re.match(r"[A-Za-z]:", folder) or "\\" in folder:
            print("That looks like a Windows path. Use the WSL path instead, eg: C:\\ai_models is /mnt/c/ai_models")
            continue
        if folder == DEFAULT_MODELS_DIR:
            resolve_dir(folder).mkdir(exist_ok=True)
        if not resolve_dir(folder).is_dir():
            print(f"Folder not found: {folder}")
            continue
        return folder


def find_file(root, name):
    """Returns the first file called name under root, searching SEARCH_DEPTH folders deep."""
    for folder, subfolders, files in os.walk(root):
        if name in files:
            return pathlib.Path(folder) / name
        depth = len(pathlib.Path(folder).relative_to(root).parts)
        subfolders[:] = sorted(d for d in subfolders if not d.startswith(".")) if depth < SEARCH_DEPTH else []
    return None


def download(model, name, target):
    url = f"https://huggingface.co/{model['repo']}/resolve/{model['revision']}/{name}"
    partial = target.with_name(target.name + ".part")
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nDownloading {name}")
    # -C - resumes an interrupted download from the .part file.
    subprocess.run(["curl", "-L", "--fail", "--progress-bar", "-C", "-", "-o", str(partial), url], check=True)
    partial.rename(target)


def fetch(model, models_dir):
    """Finds or downloads the model's files, returning their paths relative to models_dir."""
    root = resolve_dir(models_dir)
    paths = {}
    for key in ("model", "mmproj"):
        name = model[key]
        found = find_file(root, name)
        if found:
            print(f"Found {found}")
        else:
            found = root / model["repo"].split("/")[-1] / name
            download(model, name, found)
        paths[key] = found.relative_to(root).as_posix()
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--redo", action="store_true", help="offer to set up the AI model again")
    args = parser.parse_args()

    if ENV.exists():
        if not args.redo:
            print(f"AI model already set up ({ENV.relative_to(REPO_ROOT)}). Use just setup --redo to change it.")
            return
        if not ask_yes_no("Re-setup AI model?"):
            return

    current = read_env(ENV) if ENV.exists() else {}
    models = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))["models"]
    model = choose_model(models)
    models_dir = choose_models_dir(current.get("MODELS_DIR") or DEFAULT_MODELS_DIR)

    print(f"\n{model['name']} is licensed under {model['licence']}: {model['licence_url']}")
    if not ask_yes_no("Accept the licence and continue?"):
        sys.exit("Setup cancelled.")

    paths = fetch(model, models_dir)
    write_env(ENV if ENV.exists() else ENV_EXAMPLE, ENV, {
        "MODELS_DIR": models_dir,
        "LLM_MODEL": paths["model"],
        "LLM_MMPROJ": paths["mmproj"],
    })
    print(f"\nWrote {ENV.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        sys.exit("\nSetup cancelled.")
