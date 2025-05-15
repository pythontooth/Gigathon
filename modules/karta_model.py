def karta_model(typ=None, numer=None, kolor=None):
    types = {'kier', 'karo', 'trefl', 'pik'}
    numbers = {'2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'}
    colors = {'czerwony', 'czarny'}
    karta = {}
    karta['typ'] = typ
    karta['numer'] = numer
    karta['kolor'] = kolor

    if typ not in types:
        raise ValueError(f"Typ karty '{typ}' jest nieprawidłowy. Dozwolone typy to: {types}")
    if numer not in numbers:
        raise ValueError(f"Numer karty '{numer}' jest nieprawidłowy. Dozwolone numery to: {numbers}")
    if kolor not in colors:
        raise ValueError(f"Kolor karty '{kolor}' jest nieprawidłowy. Dozwolone kolory to: {colors}")
    
    return karta

print(karta_model(typ='kier', numer='A', kolor='czerwony'))


def renderuj_karte(karta):
    """Render a card with symbols in the terminal."""
    # Symbole kart
    symbole = {
        'kier': '♥',
        'karo': '♦',
        'trefl': '♣',
        'pik': '♠'
    }
    
    # Kolory
    kolory = {
        'czerwony': '\033[91m',  # Red
        'czarny': '\033[30m'     # Black
    }
    
    reset = '\033[0m'  # Reset color
    
    # Get card properties
    typ = karta['typ']
    numer = karta['numer']
    kolor = karta['kolor']
    
    symbol = symbole[typ]
    kolor_kod = kolory[kolor]
    
    # Przykład wyglądu karty
    karta_wyglad = [
        '┌─────────┐',
        f'│ {kolor_kod}{numer.ljust(2)}{reset}      │',
        '│         │',
        f'│    {kolor_kod}{symbol}{reset}    │',
        '│         │',
        f'│      {kolor_kod}{numer.rjust(2)}{reset} │',
        '└─────────┘'
    ]
    
    return '\n'.join(karta_wyglad)

# Przykładowe użycie (wygenerowanie dwóch innych kart)
if __name__ == "__main__":
    karta1 = karta_model(typ='kier', numer='A', kolor='czerwony')
    karta2 = karta_model(typ='pik', numer='K', kolor='czarny')
    
    print(renderuj_karte(karta1))
    print("\n")
    print(renderuj_karte(karta2))

