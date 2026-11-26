"""Currency exponents published by Telegram, plus Stars (XTR). No FX conversion."""
import json
from pathlib import Path

CURRENCIES=json.loads(Path(__file__).with_name('currency-exponents.json').read_text())

def exponent(currency):
    if currency not in CURRENCIES: raise ValueError('Неподдерживаемая валюта')
    return CURRENCIES[currency]
