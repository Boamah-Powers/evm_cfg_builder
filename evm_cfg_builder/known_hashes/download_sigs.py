"""
Queries and import function signatures from https://www.4byte.directory/
"""
import sys
from typing import Tuple, Dict

try:
    import requests
except ImportError:
    print('Run "pip install requests" t run this script')
    sys.exit(0)
import known_hashes


def get_results(url: str, num_parsed: int) -> Tuple[str, int]:
    """
    Queries the API for a json formatted list of functions and their associated function signatures
    """
    resp = requests.get(url)
    resp.raise_for_status()

    json_data = resp.json()
    next_url: str = json_data["next"]
    results = json_data["results"]

    cur_parsed = 0
    for result in results:
        hex_sig = result["hex_signature"]
        text_sig = result["text_signature"]
        
        # normalize key into integer
        key = int(hex_sig, 16)

        # If this key is not present, add a new list with the text signature
        if key not in known_hashes.known_hashes:
            known_hashes.known_hashes[key] = {text_sig}
            cur_parsed += 1
        else:
            # If this text signature is new, add it
            before_count = len(known_hashes.known_hashes[key])
            known_hashes.known_hashes[key].add(text_sig)
            # Only increment if we actually added something new
            if len(known_hashes.known_hashes[key]) > before_count:
                cur_parsed += 1

    num_parsed += cur_parsed
    # Display a status update (guard against missing 'count')
    total_count = json_data.get("count")
    percentage_comp = (num_parsed / total_count * 100) if total_count else 0
    print(f"Parsed {num_parsed}/{total_count if total_count is not None else '?'} results ({percentage_comp:.2f}%)")

    return next_url, cur_parsed


def iterate_paginated_results(url: str) -> None:
    """
    4byte paginates the results for effeciency because there are > 400,000 function signatures.
    This will move from page to page and collect all the signatures available.
    """
    results_parsed = 0
    while True:
        url, num_parsed = get_results(url, results_parsed)
        if not url:
            break

        results_parsed += num_parsed

    print("Finished iterating over results")


def sort_dict(unsorted_dict: Dict) -> Dict:
    sorted_dict = dict(sorted(unsorted_dict.items()))
    return sorted_dict


def save_results() -> None:
    """
    Write the dict to the known_hashes.py file
    We write the key and value so the file contains a literal Python dict where
    each value is a list of text signatures (even if there's only one).
    """
    sorted_dict = sort_dict(known_hashes.known_hashes)
    with open("known_hashes.py", "w", encoding="utf-8") as f:
        f.write("known_hashes = {\n")
        for k, v in sorted_dict.items():
            v_list = list(v) if isinstance(v, set) else v
            f.write(f"  {k:#010x}: {v_list!r},\n")
        f.write("}\n")

    print("Saved results!")


if __name__ == "__main__":

    # Ensure we start fresh each run to avoid stale/sticky data from previous executions
    known_hashes.known_hashes = {}

    iterate_paginated_results("https://www.4byte.directory/api/v1/signatures/")
    save_results()
