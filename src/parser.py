import re
from typing import Optional, Dict, Any

MULTIPLIERS = {
    'k': 1_000,
    'rb': 1_000,
    'ribu': 1_000,
    'jt': 1_000_000,
    'juta': 1_000_000,
    'm': 1_000_000_000,
    'miliar': 1_000_000_000,
}

# Regex to find nominals anywhere (front, middle, back)
# Supports: 20k, 25.5rb, 1,5jt, 20.000, 50000, rp 25k, rp25000
AMOUNT_REGEX = re.compile(
    r'(?:rp\.?\s*)?(\d+(?:[.,]\d+)?)\s*(k|rb|ribu|jt|juta|m|miliar)?\b',
    re.IGNORECASE
)

# Cues that mark the transaction strictly as INCOME
INCOME_CUES = re.compile(
    r'\b(?:duit\s+dari|uang\s+dr|duit\s+dr|uang\s+dari|dikasih|dapet|dapat|gaji|terima\s+dari|transferan\s+dari|honor|cair)\b',
    re.IGNORECASE
)

# Default keyword to category rules (Sorted by priority, longer phrases first)
DEFAULT_CATEGORY_RULES = [
    # Topup / E-Wallet
    (r'\b(topup\s+gopay|topup\s+ovo|topup\s+dana|topup\s+shopeepay|top\s*up|gopay|ovo|dana|shopeepay|e-wallet|ewallet)\b', 'Top Up / E-Wallet', 'EXPENSE'),
    # Transportasi
    (r'\b(bensin|spbu|pertalite|pertamax|solar|parkir|ojol|gojek|grab|maxim|kereta|krl|mrt|busway|toll|tol|angkot|tambal\s+ban)\b', 'Transportasi', 'EXPENSE'),
    # Makanan & Minuman
    (r'\b(nasi|makan|kopi|coffee|mie|ayam|bakso|sate|warteg|teh|snack|roti|sarapan|siang|malam|minum|burger|pizza|jus|es\s+teh|gorengan)\b', 'Makanan & Minuman', 'EXPENSE'),
    # Belanja / Kebutuhan
    (r'\b(baju|celana|sepatu|sabun|shampoo|odol|indomaret|alfamart|supermarket|belanja|skincare|buku)\b', 'Belanja', 'EXPENSE'),
    # Tagihan
    (r'\b(listrik|token|pln|wifi|indihome|pdam|air|kontrakan|kos|kost|pulsa|paket\s+data|kuota|bpjs)\b', 'Tagihan', 'EXPENSE'),
    # Hiburan
    (r'\b(bioskop|nonton|game|steam|netflix|spotify|youtube)\b', 'Hiburan', 'EXPENSE'),
    # Pendapatan
    (r'\b(dpt\s+uang|gaji|freelance|bonus|thr|dividen|penjualan|omset|profit)\b', 'Pendapatan', 'INCOME'),
]

def parse_transaction(text: str) -> Optional[Dict[str, Any]]:
    """
    Parses natural language chat into financial transaction attributes.
    Returns None if no valid nominal is found.
    """
    clean_text = text.strip()
    if not clean_text:
        return None

    # Ignore slash commands like /start, /rekap, /batal
    if clean_text.startswith('/'):
        return None

    # Step 1: Detect Income Intent
    has_income_cue = bool(INCOME_CUES.search(clean_text))

    # Step 2: Extract Amount & Unit anywhere in the string
    matches = list(AMOUNT_REGEX.finditer(clean_text))
    if not matches:
        return None

    # Prioritize match with explicit multiplier if multiple numbers present
    chosen_match = None
    for m in matches:
        chosen_match = m
        if m.group(2): # Has unit k, rb, jt
            break

    if not chosen_match:
        return None

    raw_num_str = chosen_match.group(1).replace(',', '.')
    unit_str = (chosen_match.group(2) or '').lower()

    try:
        base_amount = float(raw_num_str)
    except ValueError:
        return None

    multiplier = MULTIPLIERS.get(unit_str, 1)

    # Distinguish standard thousand separator (e.g. 20.000 vs 20.5)
    if not unit_str and '.' in chosen_match.group(1):
        parts = chosen_match.group(1).split('.')
        if len(parts) == 2 and len(parts[1]) == 3:
            amount = float(parts[0] + parts[1])
        else:
            amount = base_amount * multiplier
    else:
        amount = base_amount * multiplier

    if amount <= 0:
        return None

    # Step 3: Extract Description
    desc_start, desc_end = chosen_match.span()
    desc_remaining = clean_text[:desc_start] + " " + clean_text[desc_end:]
    desc_normalized = re.sub(r'\s+', ' ', desc_remaining).strip()

    # Step 4: Categorization
    tx_type = 'INCOME' if has_income_cue else 'EXPENSE'
    category = 'Pendapatan' if has_income_cue else 'Lain-lain'

    for pattern, cat_name, cat_type in DEFAULT_CATEGORY_RULES:
        if re.search(pattern, clean_text, re.IGNORECASE):
            category = cat_name
            if not has_income_cue:
                tx_type = cat_type
            break

    # Clean description for display (remove common filler prefixes)
    cleaned_desc = desc_normalized
    for sw in [r'\bduit\s+(?:dari|dr)\b', r'\buang\s+(?:dari|dr)\b', r'\bduit\b', r'\buang\b', r'\bbeli\b', r'\bbuat\b']:
        cleaned_desc = re.sub(sw, '', cleaned_desc, flags=re.IGNORECASE).strip()

    if not cleaned_desc:
        cleaned_desc = category

    return {
        'amount': int(amount),
        'category': category,
        'type': tx_type,
        'description': cleaned_desc,
        'raw_text': clean_text
    }
