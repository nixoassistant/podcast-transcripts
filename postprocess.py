#!/usr/bin/env python3
"""
Post-process Daily Gwei transcripts using Ethereum dictionary corrections.
"""

import json
import re
import sys
from pathlib import Path

DICT_PATH = Path(__file__).parent / "eth-dictionary.json"

def load_dictionary():
    with open(DICT_PATH) as f:
        return json.load(f)

def apply_corrections(text: str, dictionary: dict) -> str:
    corrections = dictionary.get("corrections", {})
    
    # Case-sensitive replacements
    for wrong, right in corrections.get("case_sensitive", {}).items():
        text = text.replace(wrong, right)
    
    # Case-insensitive replacements (word boundaries)
    for wrong, right in corrections.get("case_insensitive", {}).items():
        pattern = re.compile(r'\b' + re.escape(wrong) + r'\b', re.IGNORECASE)
        text = pattern.sub(right, text)
    
    return text

def process_file(filepath: Path, dictionary: dict, dry_run: bool = False) -> tuple[int, list]:
    original = filepath.read_text()
    corrected = apply_corrections(original, dictionary)
    
    # Count changes
    changes = []
    for wrong in dictionary["corrections"].get("case_sensitive", {}).keys():
        if wrong in original:
            changes.append(wrong)
    for wrong in dictionary["corrections"].get("case_insensitive", {}).keys():
        if re.search(r'\b' + re.escape(wrong) + r'\b', original, re.IGNORECASE):
            changes.append(wrong)
    
    if not dry_run and corrected != original:
        filepath.write_text(corrected)
    
    return len(changes), changes

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Post-process transcripts with ETH dictionary")
    parser.add_argument("files", nargs="*", help="Files to process (default: transcripts/*.md)")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    args = parser.parse_args()
    
    dictionary = load_dictionary()
    
    files = args.files
    if not files:
        files = list(Path(__file__).parent.glob("transcripts/*.md"))
    else:
        files = [Path(f) for f in files]
    
    total_changes = 0
    for f in files:
        count, changes = process_file(f, dictionary, args.dry_run)
        if count > 0:
            print(f"{f.name}: {count} corrections ({', '.join(changes)})")
            total_changes += count
    
    action = "would apply" if args.dry_run else "applied"
    print(f"\nTotal: {action} corrections to {len(files)} files")

if __name__ == "__main__":
    main()
