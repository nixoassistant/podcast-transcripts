#!/usr/bin/env python3
"""
Use LLM to add logical paragraph breaks to transcripts.
"""

import os
import sys
import json
import re
from pathlib import Path
import urllib.request
import urllib.error

EFAI_URL = "https://automation-testing.ethereum.foundation/gateway/inference/v1/chat/completions"
EFAI_MODEL = "openai/gpt-oss-120b"

def call_efai(text: str, api_key: str) -> str:
    """Call EFAI API to format paragraphs."""
    
    prompt = f"""You are a transcript formatter. Your job is to add paragraph breaks to a podcast transcript to make it more readable.

Rules:
- Add blank lines between paragraphs at natural topic transitions
- Keep the text EXACTLY the same - only add line breaks
- Don't add any commentary, headers, or formatting
- Don't remove or change any words
- Aim for paragraphs of 3-6 sentences each
- Break at topic changes, "All right", "So", "Now", "Moving on", etc.

Here is the transcript to format:

{text}

Return ONLY the formatted transcript with paragraph breaks added. No other text."""

    payload = {
        "model": EFAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 16000,
        "temperature": 0.1
    }
    
    req = urllib.request.Request(
        EFAI_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        print(f"API error: {e.code} - {e.read().decode()}")
        raise
    except Exception as e:
        print(f"Error calling EFAI: {e}")
        raise

def process_file(filepath: Path, api_key: str, dry_run: bool = False) -> bool:
    """Process a single transcript file."""
    content = filepath.read_text()
    
    # Split into header and body
    parts = content.split("---\n\n", 1)
    if len(parts) != 2:
        print(f"  Skipping {filepath.name}: unexpected format")
        return False
    
    header, body = parts[0] + "---\n\n", parts[1]
    
    # Skip if already has paragraphs (multiple blank lines)
    if "\n\n" in body and body.count("\n\n") > 3:
        print(f"  Skipping {filepath.name}: already formatted")
        return False
    
    print(f"  Formatting {filepath.name}...")
    
    # Process in chunks if too long (>30k chars)
    if len(body) > 30000:
        # Split roughly in half at a sentence boundary
        mid = len(body) // 2
        # Find nearest period
        split_point = body.rfind(". ", mid - 1000, mid + 1000)
        if split_point == -1:
            split_point = mid
        
        part1 = call_efai(body[:split_point + 1], api_key)
        part2 = call_efai(body[split_point + 1:], api_key)
        formatted = part1 + "\n\n" + part2
    else:
        formatted = call_efai(body, api_key)
    
    if not dry_run:
        filepath.write_text(header + formatted)
    
    return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Format transcript paragraphs with LLM")
    parser.add_argument("files", nargs="*", help="Files to process")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    api_key = os.environ.get("EFAI_API_KEY")
    if not api_key:
        print("Error: EFAI_API_KEY not set")
        sys.exit(1)
    
    files = args.files
    if not files:
        files = list(Path(__file__).parent.glob("transcripts/*.md"))
    else:
        files = [Path(f) for f in files]
    
    processed = 0
    for f in files:
        try:
            if process_file(f, api_key, args.dry_run):
                processed += 1
        except Exception as e:
            print(f"  Error processing {f.name}: {e}")
    
    print(f"\nFormatted {processed} files")

if __name__ == "__main__":
    main()
