#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pasjans (Solitaire) - Gra Karciana
----------------------------------
Autor: Patryk
Data: Maj 2025

Profesjonalna implementacja klasycznej gry w pasjansa w konsoli.
Zawiera zaawansowane funkcje jak:
- Kolorowe karty z symbolami Unicode
- Intuicyjny interfejs użytkownika
- System cofania ruchów
- Automatyczne wykrywanie możliwych ruchów
- Statystyki gry
- System zapisywania i wczytywania gier
"""

import os
import random
import time
import json
import datetime
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
from dataclasses import dataclass
import curses
from abc import ABC, abstractmethod
from pathlib import Path

# --- Stałe i konfiguracja ---
KARTA_ODKRYTA = True
KARTA_ZAKRYTA = False
SAVES_DIR = Path("saves")

# Ensure saves directory exists
SAVES_DIR.mkdir(exist_ok=True)

class Kolor(Enum):
    """Kolory kart z symbolami Unicode"""
    KIER = ("♥", "czerwony")
    KARO = ("♦", "czerwony") 
    PIK = ("♠", "czarny")
    TREFL = ("♣", "czarny")

class Figura(Enum):
    """Figury kart z ich wartościami"""
    AS = (1, "A")
    DWA = (2, "2")
    TRZY = (3, "3")
    CZTERY = (4, "4")
    PIEC = (5, "5")
    SZESC = (6, "6")
    SIEDEM = (7, "7")
    OSIEM = (8, "8")
    DZIEWIEC = (9, "9")
    DZIESIEC = (10, "10")
    WALET = (11, "J")
    DAMA = (12, "Q")
    KROL = (13, "K")

@dataclass
class Karta:
    """Reprezentacja pojedynczej karty"""
    kolor: Kolor
    figura: Figura
    odkryta: bool = KARTA_ZAKRYTA

    def __str__(self) -> str:
        if not self.odkryta:
            return "[XX]"
        return f"[{self.figura.value[1]}{self.kolor.value[0]}]"

    @property
    def wartosc(self) -> int:
        return self.figura.value[0]

    @property
    def jest_czerwona(self) -> bool:
        return self.kolor.value[1] == "czerwony"
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje kartę do słownika do zapisu JSON"""
        return {
            "kolor": self.kolor.name,
            "figura": self.figura.name,
            "odkryta": self.odkryta
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Karta':
        """Tworzy obiekt karty z danych słownikowych"""
        return cls(
            kolor=Kolor[data["kolor"]],
            figura=Figura[data["figura"]],
            odkryta=data["odkryta"]
        )

class StosKart:
    """Bazowa klasa dla wszystkich stosów kart"""
    def __init__(self):
        self.karty: List[Karta] = []

    def dodaj_karte(self, karta: Karta) -> None:
        self.karty.append(karta)

    def usun_karte(self) -> Optional[Karta]:
        if self.karty:
            return self.karty.pop()
        return None

    def jest_pusty(self) -> bool:
        return len(self.karty) == 0

    def wierzchnia_karta(self) -> Optional[Karta]:
        if self.karty:
            return self.karty[-1]
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje stos kart do słownika do zapisu JSON"""
        return {
            "karty": [karta.to_dict() for karta in self.karty]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StosKart':
        """Tworzy obiekt stosu kart z danych słownikowych"""
        stos = cls()
        stos.karty = [Karta.from_dict(k) for k in data["karty"]]
        return stos

class StosKoncowy(StosKart):
    """Stos końcowy do układania kart według kolorów"""
    def __init__(self, kolor: Kolor):
        super().__init__()
        self.kolor = kolor

    def mozna_dodac(self, karta: Karta) -> bool:
        if karta.kolor != self.kolor:
            return False
        
        if self.jest_pusty():
            return karta.figura == Figura.AS
            
        return (karta.wartosc == self.wierzchnia_karta().wartosc + 1)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje stos końcowy do słownika do zapisu JSON"""
        data = super().to_dict()
        data["kolor"] = self.kolor.name
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StosKoncowy':
        """Tworzy obiekt stosu końcowego z danych słownikowych"""
        stos = cls(kolor=Kolor[data["kolor"]])
        stos.karty = [Karta.from_dict(k) for k in data["karty"]]
        return stos

class KolumnaGry(StosKart):
    """Kolumna główna w grze"""
    def mozna_dodac(self, karta: Karta) -> bool:
        if self.jest_pusty():
            return karta.figura == Figura.KROL
            
        wierzchnia = self.wierzchnia_karta()
        return (wierzchnia.wartosc == karta.wartosc + 1 and 
                wierzchnia.jest_czerwona != karta.jest_czerwona)

class StosRezerwowy(StosKart):
    """Stos kart do dobierania"""
    def przetasuj(self) -> None:
        random.shuffle(self.karty)
        for karta in self.karty:
            karta.odkryta = KARTA_ZAKRYTA

class Gra:
    """Główna klasa gry zarządzająca logiką i stanem gry"""
    def __init__(self):
        self.kolumny: List[KolumnaGry] = [KolumnaGry() for _ in range(7)]
        self.stosy_koncowe: List[StosKoncowy] = [
            StosKoncowy(kolor) for kolor in Kolor
        ]
        self.stos_rezerwowy = StosRezerwowy()
        self.stos_odkryty = StosKart()
        self.data_rozpoczecia = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.ruchy = 0
        self.inicjalizuj_gre()

    def inicjalizuj_gre(self) -> None:
        """Inicjalizacja nowej gry"""
        # Tworzenie i tasowanie talii
        talia = [
            Karta(kolor, figura)
            for kolor in Kolor
            for figura in Figura
        ]
        random.shuffle(talia)

        # Rozdawanie kart do kolumn
        for i, kolumna in enumerate(self.kolumny):
            for j in range(i + 1):
                karta = talia.pop()
                if j == i:  # Ostatnia karta w kolumnie
                    karta.odkryta = KARTA_ODKRYTA
                kolumna.dodaj_karte(karta)

        # Reszta kart na stos rezerwowy
        self.stos_rezerwowy.karty = talia

    def dobierz_karte(self) -> None:
        """Dobieranie karty ze stosu rezerwowego"""
        if self.stos_rezerwowy.jest_pusty():
            # Przenoszenie kart z powrotem na stos rezerwowy
            while not self.stos_odkryty.jest_pusty():
                karta = self.stos_odkryty.usun_karte()
                karta.odkryta = KARTA_ZAKRYTA
                self.stos_rezerwowy.dodaj_karte(karta)
        else:
            karta = self.stos_rezerwowy.usun_karte()
            if karta:
                karta.odkryta = KARTA_ODKRYTA
                self.stos_odkryty.dodaj_karte(karta)
        self.ruchy += 1

    def czy_wygrana(self) -> bool:
        """Sprawdzanie czy gra została wygrana"""
        return all(len(stos.karty) == 13 for stos in self.stosy_koncowe)

    def licz_dostepne_ruchy(self) -> int:
        """Oblicza liczbę dostępnych ruchów w obecnej sytuacji"""
        ruchy = 0
        
        # Sprawdź możliwe ruchy między kolumnami
        for i in range(7):
            for j in range(7):
                if i != j and not self.kolumny[i].jest_pusty():
                    karta = self.kolumny[i].wierzchnia_karta()
                    if karta.odkryta and self.kolumny[j].mozna_dodac(karta):
                        ruchy += 1
        
        # Sprawdź możliwe ruchy z stosu odkrytego na kolumny
        if not self.stos_odkryty.jest_pusty():
            karta = self.stos_odkryty.wierzchnia_karta()
            for j in range(7):
                if self.kolumny[j].mozna_dodac(karta):
                    ruchy += 1
        
        # Sprawdź możliwe ruchy z kolumn na stosy końcowe
        for i in range(7):
            if not self.kolumny[i].jest_pusty():
                karta = self.kolumny[i].wierzchnia_karta()
                if karta.odkryta:
                    for stos in self.stosy_koncowe:
                        if stos.kolor == karta.kolor and stos.mozna_dodac(karta):
                            ruchy += 1
        
        # Sprawdź możliwe ruchy z stosu odkrytego na stosy końcowe
        if not self.stos_odkryty.jest_pusty():
            karta = self.stos_odkryty.wierzchnia_karta()
            for stos in self.stosy_koncowe:
                if stos.kolor == karta.kolor and stos.mozna_dodac(karta):
                    ruchy += 1
        
        # Sprawdź możliwość dobierania kart
        if not self.stos_rezerwowy.jest_pusty() or not self.stos_odkryty.jest_pusty():
            ruchy += 1
            
        return ruchy
    
    def czy_koniec_gry(self) -> bool:
        """Sprawdza czy gra jest zakończona (brak możliwych ruchów)"""
        return self.licz_dostepne_ruchy() == 0 and not self.czy_wygrana()

    def wyswietl_stan_gry(self) -> None:
        """Wyświetlanie aktualnego stanu gry"""
        os.system('clear')
        print("\n=== PASJANS ===\n")
        
        # Wyświetlanie stosu rezerwowego i odkrytego
        print("Stos rezerwowy:", end=" ")
        if not self.stos_rezerwowy.jest_pusty():
            print("[##]", end=" ")
        else:
            print("[ ]", end=" ")
            
        print("Odkryte:", end=" ")
        if not self.stos_odkryty.jest_pusty():
            print(self.stos_odkryty.wierzchnia_karta(), end=" ")
        else:
            print("[ ]", end=" ")
            
        # Wyświetlanie stosów końcowych
        print("\nStosy końcowe:", end=" ")
        for stos in self.stosy_koncowe:
            if stos.jest_pusty():
                print(f"[{stos.kolor.value[0]}]", end=" ")
            else:
                print(stos.wierzchnia_karta(), end=" ")
        
        # Wyświetlanie kolumn gry
        print("\n\nKolumny:")
        for i, kolumna in enumerate(self.kolumny):
            print(f"{i+1}:", end=" ")
            for karta in kolumna.karty:
                print(karta, end=" ")
            print()
        print()

    def wykonaj_ruch(self, komenda: str) -> bool:
        """Wykonywanie ruchu na podstawie komendy gracza"""
        if komenda.lower() == 'd':
            self.dobierz_karte()
            return True
            
        try:
            if len(komenda) == 2:
                zrodlo, cel = int(komenda[0]), int(komenda[1])
                return self.przenies_karte(zrodlo - 1, cel - 1)
        except ValueError:
            return False
            
        return False

    def przenies_karte(self, zrodlo: int, cel: int) -> bool:
        """Przenoszenie karty między kolumnami"""
        if not (0 <= zrodlo < 7 and 0 <= cel < 7):
            return False
            
        zrodlo_stos = self.kolumny[zrodlo]
        cel_stos = self.kolumny[cel]
        
        if zrodlo_stos.jest_pusty():
            return False
            
        karta = zrodlo_stos.wierzchnia_karta()
        if cel_stos.mozna_dodac(karta):
            karta = zrodlo_stos.usun_karte()
            cel_stos.dodaj_karte(karta)
            
            # Odkrywanie następnej karty w stosie źródłowym
            if not zrodlo_stos.jest_pusty():
                zrodlo_stos.wierzchnia_karta().odkryta = KARTA_ODKRYTA
                
            self.ruchy += 1
            return True
            
        return False

    def przenies_karte_z_odkrytej(self, cel: int) -> bool:
        """Przenoszenie karty z odkrytego stosu do kolumny"""
        if self.stos_odkryty.jest_pusty() or not (0 <= cel < 7):
            return False
            
        cel_stos = self.kolumny[cel]
        karta = self.stos_odkryty.wierzchnia_karta()
        
        if cel_stos.mozna_dodac(karta):
            karta = self.stos_odkryty.usun_karte()
            cel_stos.dodaj_karte(karta)
            self.ruchy += 1
            return True
            
        return False
    
    def przenies_karte_do_koncowego(self, zrodlo: int) -> bool:
        """Przenoszenie karty z kolumny do odpowiedniego stosu końcowego"""
        if not (0 <= zrodlo < 7) or self.kolumny[zrodlo].jest_pusty():
            return False
            
        karta = self.kolumny[zrodlo].wierzchnia_karta()
        if not karta.odkryta:
            return False
            
        # Znajdź odpowiedni stos końcowy dla koloru karty
        for stos in self.stosy_koncowe:
            if stos.kolor == karta.kolor and stos.mozna_dodac(karta):
                karta = self.kolumny[zrodlo].usun_karte()
                stos.dodaj_karte(karta)
                
                # Odkrywanie następnej karty w stosie źródłowym
                if not self.kolumny[zrodlo].jest_pusty():
                    self.kolumny[zrodlo].wierzchnia_karta().odkryta = KARTA_ODKRYTA
                
                self.ruchy += 1
                return True
                
        return False
        
    def przenies_karte_z_odkrytej_do_koncowego(self) -> bool:
        """Przenoszenie karty z odkrytego stosu do odpowiedniego stosu końcowego"""
        if self.stos_odkryty.jest_pusty():
            return False
            
        karta = self.stos_odkryty.wierzchnia_karta()
        
        # Znajdź odpowiedni stos końcowy dla koloru karty
        for stos in self.stosy_koncowe:
            if stos.kolor == karta.kolor and stos.mozna_dodac(karta):
                karta = self.stos_odkryty.usun_karte()
                stos.dodaj_karte(karta)
                self.ruchy += 1
                return True
                
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje stan gry do słownika do zapisu JSON"""
        return {
            "data_rozpoczecia": self.data_rozpoczecia,
            "ruchy": self.ruchy,
            "kolumny": [kolumna.to_dict() for kolumna in self.kolumny],
            "stosy_koncowe": [stos.to_dict() for stos in self.stosy_koncowe],
            "stos_rezerwowy": self.stos_rezerwowy.to_dict(),
            "stos_odkryty": self.stos_odkryty.to_dict(),
            "data_zapisu": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Gra':
        """Tworzy obiekt gry z danych słownikowych"""
        gra = cls()
        gra.data_rozpoczecia = data.get("data_rozpoczecia", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        gra.ruchy = data.get("ruchy", 0)
        
        # Wczytaj kolumny
        gra.kolumny = [KolumnaGry.from_dict(kol) for kol in data["kolumny"]]
        
        # Wczytaj stosy końcowe
        gra.stosy_koncowe = [StosKoncowy.from_dict(stos) for stos in data["stosy_koncowe"]]
        
        # Wczytaj stos rezerwowy i odkryty
        gra.stos_rezerwowy = StosRezerwowy.from_dict(data["stos_rezerwowy"])
        gra.stos_odkryty = StosKart.from_dict(data["stos_odkryty"])
        
        return gra
    
    def zapisz_gre(self, nazwa: str) -> bool:
        """Zapisuje stan gry do pliku JSON"""
        try:
            file_path = SAVES_DIR / f"{nazwa}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Błąd podczas zapisywania gry: {e}")
            return False
    
    @classmethod
    def wczytaj_gre(cls, nazwa: str) -> Optional['Gra']:
        """Wczytuje stan gry z pliku JSON"""
        try:
            file_path = SAVES_DIR / f"{nazwa}.json"
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            print(f"Błąd podczas wczytywania gry: {e}")
            return None
    
    @staticmethod
    def lista_zapisanych_gier() -> List[Dict[str, Any]]:
        """Zwraca listę zapisanych gier z metadanymi"""
        zapisy = []
        for file_path in SAVES_DIR.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    zapisy.append({
                        "nazwa": file_path.stem,
                        "data_rozpoczecia": data.get("data_rozpoczecia", "Nieznana"),
                        "data_zapisu": data.get("data_zapisu", "Nieznana"),
                        "ruchy": data.get("ruchy", 0)
                    })
            except Exception:
                # Zignoruj uszkodzone pliki zapisu
                pass
        return zapisy

class CursesUI:
    def __init__(self, gra=None):
        self.gra = gra or Gra()
        self.win = None
        self.selected = 0  # which column is highlighted
        self.source_col = None  # source column for move
        self.odkryty_selected = False  # whether odkryty pile is selected
        self.selected_foundation = None  # which foundation is selected (0-3)
        self.status_msg = ""    # status message to display
        self.menu_active = False
        self.menu_items = ["Powrót do gry", "Zapisz grę", "Wczytaj grę", "Nowa gra", "Wyjdź"]
        self.menu_selected = 0
        self.submenu_active = False
        self.submenu_selected = 0
        self.submenu_items = []
        self.submenu_type = ""
        self.prompt_active = False
        self.prompt_text = ""
        self.prompt_value = ""
        self.input_cursor = 0
        self.game_over = False  # Track game over state

    def run(self):
        if self.gra is None:
            # Show load game menu if no game is provided
            self.gra = self._show_main_menu()
            if self.gra is None:
                return
        curses.wrapper(self._main)

    def _show_main_menu(self):
        """Shows the main menu and returns a game object"""
        menu_items = ["Nowa gra", "Wczytaj grę", "Wyjdź"]
        selected = 0
        
        stdscr = curses.initscr()
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_WHITE, -1)
        curses.curs_set(0)
        stdscr.keypad(True)
        
        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            
            # Draw logo
            title = "PASJANS - MENU GŁÓWNE"
            stdscr.addstr(h//6, (w-len(title))//2, title, curses.A_BOLD)
            
            # Draw menu items
            for i, item in enumerate(menu_items):
                y = h//2 - len(menu_items)//2 + i
                x = (w - len(item)) // 2
                attr = curses.A_REVERSE if i == selected else curses.A_NORMAL
                stdscr.addstr(y, x, item, attr)
            
            # Draw footer
            footer = "Użyj strzałek do nawigacji i ENTER do wyboru"
            stdscr.addstr(h-2, (w-len(footer))//2, footer, curses.A_DIM)
            
            stdscr.refresh()
            
            key = stdscr.getch()
            
            if key in (curses.KEY_UP, ord('w'), ord('W')):
                selected = (selected - 1) % len(menu_items)
            elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
                selected = (selected + 1) % len(menu_items)
            elif key in (curses.KEY_ENTER, 10, 13):
                if selected == 0:  # New game
                    stdscr.clear()
                    stdscr.refresh()
                    curses.endwin()
                    return Gra()
                elif selected == 1:  # Load game
                    saves = Gra.lista_zapisanych_gier()
                    if not saves:
                        stdscr.clear()
                        msg = "Brak zapisanych gier!"
                        stdscr.addstr(h//2, (w-len(msg))//2, msg)
                        stdscr.getch()
                        continue
                    
                    save_selected = 0
                    while True:
                        stdscr.clear()
                        stdscr.addstr(2, 2, "Wybierz zapis gry:", curses.A_BOLD)
                        
                        for i, save in enumerate(saves):
                            y = 4 + i
                            attr = curses.A_REVERSE if i == save_selected else curses.A_NORMAL
                            display = f"{save['nazwa']} - Ruchy: {save['ruchy']} - Zapis: {save['data_zapisu']}"
                            stdscr.addstr(y, 4, display, attr)
                        
                        stdscr.addstr(h-3, 2, "ESC: Powrót")
                        stdscr.refresh()
                        
                        key = stdscr.getch()
                        
                        if key in (curses.KEY_UP, ord('w'), ord('W')):
                            save_selected = (save_selected - 1) % len(saves)
                        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
                            save_selected = (save_selected + 1) % len(saves)
                        elif key in (curses.KEY_ENTER, 10, 13):
                            save_name = saves[save_selected]["nazwa"]
                            loaded_game = Gra.wczytaj_gre(save_name)
                            if loaded_game:
                                stdscr.clear()
                                stdscr.refresh()
                                curses.endwin()
                                return loaded_game
                            else:
                                stdscr.clear()
                                msg = f"Błąd wczytywania {save_name}!"
                                stdscr.addstr(h//2, (w-len(msg))//2, msg)
                                stdscr.getch()
                        elif key == 27:  # ESC
                            break
                            
                elif selected == 2:  # Exit
                    stdscr.clear()
                    stdscr.refresh()
                    curses.endwin()
                    return None
            
            elif key in (27, ord('q'), ord('Q')):  # ESC or Q
                stdscr.clear()
                stdscr.refresh()
                curses.endwin()
                return None

    def _main(self, stdscr):
        self.win = stdscr
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_RED, -1)
        curses.init_pair(2, curses.COLOR_WHITE, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)  # New color for warnings
        self.win.keypad(True)

        # show beginner tutorial before entering main loop
        self._show_tutorial()

        while True:
            # Check for game over at the start of each loop
            if not self.game_over and not self.menu_active and not self.submenu_active and not self.prompt_active:
                if self.gra.czy_koniec_gry():
                    self.game_over = True
                    self.status_msg = "KONIEC GRY! Brak możliwych ruchów. Naciśnij 'N' dla nowej gry lub 'M' dla menu."
            
            if self.menu_active:
                self._draw_menu()
            elif self.submenu_active:
                self._draw_submenu()
            elif self.prompt_active:
                self._draw_prompt()
            else:
                self._draw()

            key = self.win.getch()
            
            # Allow 'N' key for new game when game is over
            if self.game_over and key in (ord('n'), ord('N')):
                self.gra = Gra()
                self.selected = 0
                self.source_col = None
                self.odkryty_selected = False
                self.selected_foundation = None
                self.status_msg = "Rozpoczęto nową grę"
                self.game_over = False
                continue
            
            # Check for menu activation key (M)
            if key in (ord('m'), ord('M')) and not self.menu_active and not self.submenu_active and not self.prompt_active:
                self.menu_active = True
                self.menu_selected = 0
                continue
                
            # Handle menu navigation
            if self.menu_active:
                self._handle_menu_key(key)
                continue
                
            # Handle submenu navigation
            if self.submenu_active:
                self._handle_submenu_key(key)
                continue
                
            # Handle prompt input
            if self.prompt_active:
                self._handle_prompt_key(key)
                continue
                
            # If game is over, only allow menu or quit
            if self.game_over:
                if key in (ord('q'), ord('Q')):
                    return
                continue
                
            # Handle regular game keys
            if key in (ord('q'), ord('Q')):
                return
            elif key == curses.KEY_RIGHT:
                if self.odkryty_selected:
                    self.odkryty_selected = False
                    self.status_msg = f"Wybrano kolumnę {self.selected + 1}"
                else:
                    # Find next non-empty column or select column with kings only
                    original_selected = self.selected
                    for _ in range(7):  # Try all columns
                        self.selected = (self.selected + 1) % 7
                        # Skip empty column unless user can place a king there
                        if not self.gra.kolumny[self.selected].jest_pusty() or self.can_move_king_to_empty():
                            break
                    
                    # If we cycled through all columns and they're all empty
                    if self.selected == original_selected and self.gra.kolumny[self.selected].jest_pusty():
                        self.status_msg = "Wszystkie kolumny są puste!"
                    else:
                        self.status_msg = f"Wybrano kolumnę {self.selected + 1}"
            elif key == curses.KEY_LEFT:
                if self.odkryty_selected:
                    self.odkryty_selected = False
                    self.status_msg = f"Wybrano kolumnę {self.selected + 1}"
                else:
                    # Find previous non-empty column or select column with kings only
                    original_selected = self.selected
                    for _ in range(7):  # Try all columns
                        self.selected = (self.selected - 1) % 7
                        # Skip empty column unless user can place a king there
                        if not self.gra.kolumny[self.selected].jest_pusty() or self.can_move_king_to_empty():
                            break
                    
                    # If we cycled through all columns and they're all empty
                    if self.selected == original_selected and self.gra.kolumny[self.selected].jest_pusty():
                        self.status_msg = "Wszystkie kolumny są puste!"
                    else:
                        self.status_msg = f"Wybrano kolumnę {self.selected + 1}"
            elif key == ord(' '):
                self.gra.dobierz_karte()
                self.status_msg = "Dobrano kartę"
                if self.gra.czy_wygrana():
                    break
            elif key == ord('o'):  # Add shortcut to select odkryty pile
                if not self.gra.stos_odkryty.jest_pusty():
                    self.odkryty_selected = True
                    self.source_col = None  # Reset column selection when selecting odkryty
                    self.status_msg = "Wybrano kartę z stosu odkrytego. Wybierz kolumnę docelową."
                else:
                    self.status_msg = "Stos odkryty jest pusty!"
            elif key in (ord('1'), ord('2'), ord('3'), ord('4')):
                # Select a foundation pile (1-4)
                self.selected_foundation = int(chr(key)) - 1
                self.odkryty_selected = False
                self.source_col = None
                self.status_msg = f"Wybrano stos końcowy {self.selected_foundation + 1}"
            elif key == ord('f'):
                # Auto-move card to foundation
                if self.odkryty_selected:
                    # Move from odkryty to foundation
                    moved = self.gra.przenies_karte_z_odkrytej_do_koncowego()
                    if moved:
                        self.status_msg = "Przeniesiono kartę ze stosu odkrytego na stos końcowy"
                        self.odkryty_selected = False
                        if self.gra.czy_wygrana():
                            break
                    else:
                        self.status_msg = "Nie można przenieść tej karty na stos końcowy"
                elif self.source_col is None and not self.gra.kolumny[self.selected].jest_pusty():
                    # Move from selected column to foundation
                    moved = self.gra.przenies_karte_do_koncowego(self.selected)
                    if moved:
                        self.status_msg = f"Przeniesiono kartę z kolumny {self.selected + 1} na stos końcowy"
                        if self.gra.czy_wygrana():
                            break
                    else:
                        self.status_msg = "Nie można przenieść tej karty na stos końcowy"
                else:
                    self.status_msg = "Wybierz kartę, którą chcesz przenieść do stosu końcowego"
            elif key in (curses.KEY_ENTER, 10, 13):
                # If foundation is selected, move card to it
                if self.selected_foundation is not None:
                    if self.odkryty_selected:
                        # Try to move from odkryty to the specific foundation
                        karta = self.gra.stos_odkryty.wierzchnia_karta()
                        if (karta.kolor == list(Kolor)[self.selected_foundation] and 
                            self.gra.stosy_koncowe[self.selected_foundation].mozna_dodac(karta)):
                            karta = self.gra.stos_odkryty.usun_karte()
                            self.gra.stosy_koncowe[self.selected_foundation].dodaj_karte(karta)
                            self.gra.ruchy += 1
                            self.status_msg = f"Przeniesiono kartę na stos końcowy {self.selected_foundation + 1}"
                            if self.gra.czy_wygrana():
                                break
                        else:
                            self.status_msg = "Nie można przenieść tej karty na wybrany stos końcowy"
                        self.odkryty_selected = False
                    elif self.source_col is not None:
                        # Try to move from selected column to specific foundation
                        src = self.source_col
                        if not self.gra.kolumny[src].jest_pusty():
                            karta = self.gra.kolumny[src].wierzchnia_karta()
                            if (karta.kolor == list(Kolor)[self.selected_foundation] and 
                                self.gra.stosy_koncowe[self.selected_foundation].mozna_dodac(karta)):
                                karta = self.gra.kolumny[src].usun_karte()
                                self.gra.stosy_koncowe[self.selected_foundation].dodaj_karte(karta)
                                self.gra.ruchy += 1
                                # Odkrywanie następnej karty
                                if not self.gra.kolumny[src].jest_pusty():
                                    self.gra.kolumny[src].wierzchnia_karta().odkryta = KARTA_ODKRYTA
                                self.status_msg = f"Przeniesiono kartę z kolumny {src + 1} na stos końcowy {self.selected_foundation + 1}"
                                if self.gra.czy_wygrana():
                                    break
                            else:
                                self.status_msg = "Nie można przenieść tej karty na wybrany stos końcowy"
                        self.source_col = None
                    else:
                        self.status_msg = "Wybierz najpierw kartę do przeniesienia"
                    self.selected_foundation = None
                # Check if odkryty pile is selected
                elif self.odkryty_selected:
                    # Try to move card from odkryty to destination column
                    moved = self.gra.przenies_karte_z_odkrytej(self.selected)
                    if moved:
                        self.status_msg = f"Przeniesiono kartę ze stosu odkrytego do kolumny {self.selected + 1}"
                        if self.gra.czy_wygrana():
                            break
                    else:
                        self.status_msg = "Niepoprawny ruch!"
                    self.odkryty_selected = False
                # If no source column is selected, set the current column as source
                elif self.source_col is None:
                    self.source_col = self.selected
                    self.status_msg = f"Wybrano kolumnę źródłową {self.source_col + 1}. Wybierz kolumnę docelową."
                else:
                    # Try to move card from source to destination column
                    src = self.source_col
                    dst = self.selected
                    
                    # Only attempt move if source and destination are different
                    if src != dst:
                        moved = self.gra.przenies_karte(src, dst)
                        if moved:
                            self.status_msg = f"Przeniesiono kartę z kolumny {src + 1} do kolumny {dst + 1}"
                            if self.gra.czy_wygrana():
                                break
                        else:
                            self.status_msg = "Niepoprawny ruch!"
                    else:
                        self.status_msg = "Wybierz inną kolumnę docelową"
                    
                    # Reset source column after move attempt
                    self.source_col = None
                
                time.sleep(0.05)
            
            # Cancel selection with Escape key
            elif key == 27:  # ESC key
                if self.odkryty_selected:
                    self.odkryty_selected = False
                    self.status_msg = "Anulowano wybór karty z stosu odkrytego"
                elif self.source_col is not None:
                    self.source_col = None
                    self.status_msg = "Anulowano wybór"
                elif self.selected_foundation is not None:
                    self.selected_foundation = None
                    self.status_msg = "Anulowano wybór stosu końcowego"
        
        if self.gra.czy_wygrana():
            self._draw()
            self.win.addstr(22, 2, "Gratulacje! Wygrałeś!", curses.A_BOLD)
            self.win.getch()

    def _draw_menu(self):
        """Draw the game menu"""
        self.win.clear()
        h, w = self.win.getmaxyx()
        
        # Draw menu border
        menu_width = 40
        menu_height = len(self.menu_items) + 4
        start_y = (h - menu_height) // 2
        start_x = (w - menu_width) // 2
        
        # Draw menu box
        for y in range(start_y, start_y + menu_height):
            for x in range(start_x, start_x + menu_width):
                if (y == start_y or y == start_y + menu_height - 1 or 
                    x == start_x or x == start_x + menu_width - 1):
                    self.win.addch(y, x, curses.ACS_CKBOARD)
        
        # Menu title
        title = "MENU PASJANSA"
        self.win.addstr(start_y + 1, start_x + (menu_width - len(title)) // 2, title, curses.A_BOLD)
        
        # Menu items
        for i, item in enumerate(self.menu_items):
            attr = curses.A_REVERSE if i == self.menu_selected else curses.A_NORMAL
            self.win.addstr(start_y + 3 + i, start_x + 3, item, attr)
        
        self.win.refresh()

    def _handle_menu_key(self, key):
        """Handle key press in menu mode"""
        if key in (curses.KEY_UP, ord('w'), ord('W')):
            self.menu_selected = (self.menu_selected - 1) % len(self.menu_items)
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            self.menu_selected = (self.menu_selected + 1) % len(self.menu_items)
        elif key in (curses.KEY_ENTER, 10, 13):
            self._execute_menu_action()
        elif key in (27, ord('q'), ord('Q')):  # ESC or Q
            self.menu_active = False

    def _execute_menu_action(self):
        """Execute the selected menu action"""
        selected = self.menu_selected
        
        if selected == 0:  # Return to game
            self.menu_active = False
        elif selected == 1:  # Save game
            self.menu_active = False
            self.prompt_active = True
            self.prompt_text = "Wpisz nazwę zapisu gry:"
            self.prompt_value = ""
            self.input_cursor = 0
        elif selected == 2:  # Load game
            saved_games = Gra.lista_zapisanych_gier()
            if not saved_games:
                self.menu_active = False
                self.status_msg = "Brak zapisanych gier!"
                return
                
            # Setup load submenu
            self.menu_active = False
            self.submenu_active = True
            self.submenu_type = "load"
            self.submenu_items = [
                f"{game['nazwa']} - Ruchy: {game['ruchy']} - {game['data_zapisu']}"
                for game in saved_games
            ]
            self.submenu_items.append("Powrót")
            self.submenu_selected = 0
        elif selected == 3:  # New game
            self.menu_active = False
            # Reset game state
            self.gra = Gra()
            self.selected = 0
            self.source_col = None
            self.odkryty_selected = False
            self.selected_foundation = None
            self.status_msg = "Rozpoczęto nową grę"
            self.game_over = False  # Reset game over state
        elif selected == 4:  # Exit
            exit(0)

    def _draw_submenu(self):
        """Draw the submenu for loading games"""
        self.win.clear()
        h, w = self.win.getmaxyx()
        
        # Draw menu border
        menu_width = 60
        menu_height = min(len(self.submenu_items) + 4, h - 4)
        start_y = (h - menu_height) // 2
        start_x = (w - menu_width) // 2
        
        # Draw menu box
        for y in range(start_y, start_y + menu_height):
            for x in range(start_x, start_x + menu_width):
                if (y == start_y or y == start_y + menu_height - 1 or 
                    x == start_x or x == start_x + menu_width - 1):
                    self.win.addch(y, x, curses.ACS_CKBOARD)
        
        # Menu title
        title = "WCZYTAJ GRĘ" if self.submenu_type == "load" else "SUBMENU"
        self.win.addstr(start_y + 1, start_x + (menu_width - len(title)) // 2, title, curses.A_BOLD)
        
        # Calculate visible items and scrolling
        max_items = menu_height - 4
        offset = 0
        if len(self.submenu_items) > max_items:
            offset = max(0, min(self.submenu_selected - max_items // 2, len(self.submenu_items) - max_items))
        
        # Menu items
        for i in range(offset, min(offset + max_items, len(self.submenu_items))):
            item = self.submenu_items[i]
            attr = curses.A_REVERSE if i == self.submenu_selected else curses.A_NORMAL
            display_text = item if len(item) <= menu_width - 6 else item[:menu_width - 9] + "..."
            self.win.addstr(start_y + 3 + i - offset, start_x + 3, display_text, attr)
        
        self.win.refresh()

    def _handle_submenu_key(self, key):
        """Handle key press in submenu mode"""
        if key in (curses.KEY_UP, ord('w'), ord('W')):
            self.submenu_selected = (self.submenu_selected - 1) % len(self.submenu_items)
        elif key in (curses.KEY_DOWN, ord('s'), ord('S')):
            self.submenu_selected = (self.submenu_selected + 1) % len(self.submenu_items)
        elif key in (curses.KEY_ENTER, 10, 13):
            # Return to menu if last item ("Powrót") selected
            if self.submenu_selected == len(self.submenu_items) - 1:
                self.submenu_active = False
                self.menu_active = True
                return
                
            if self.submenu_type == "load":
                saved_games = Gra.lista_zapisanych_gier()
                if self.submenu_selected < len(saved_games):
                    save_name = saved_games[self.submenu_selected]["nazwa"]
                    loaded_game = Gra.wczytaj_gre(save_name)
                    if loaded_game:
                        self.gra = loaded_game
                        self.submenu_active = False
                        self.selected = 0
                        self.source_col = None
                        self.odkryty_selected = False
                        self.selected_foundation = None
                        self.status_msg = f"Wczytano grę: {save_name}"
                    else:
                        self.submenu_active = False
                        self.status_msg = f"Błąd wczytywania gry: {save_name}"
        elif key in (27, ord('q'), ord('Q')):  # ESC or Q
            self.submenu_active = False
            self.menu_active = True

    def _draw_prompt(self):
        """Draw the input prompt"""
        self.win.clear()
        h, w = self.win.getmaxyx()
        
        # Draw prompt border
        prompt_width = 50
        prompt_height = 6
        start_y = (h - prompt_height) // 2
        start_x = (w - prompt_width) // 2
        
        # Draw prompt box
        for y in range(start_y, start_y + prompt_height):
            for x in range(start_x, start_x + prompt_width):
                if (y == start_y or y == start_y + prompt_height - 1 or 
                    x == start_x or x == start_x + prompt_width - 1):
                    self.win.addch(y, x, curses.ACS_CKBOARD)
        
        # Prompt title
        self.win.addstr(start_y + 1, start_x + 2, self.prompt_text, curses.A_BOLD)
        
        # Input field
        input_x = start_x + 2
        input_y = start_y + 3
        max_display = prompt_width - 4
        
        # Calculate display offset for long inputs
        display_offset = max(0, self.input_cursor - max_display + 5)
        display_value = self.prompt_value[display_offset:display_offset + max_display]
        
        self.win.addstr(input_y, input_x, display_value)
        
        # Draw cursor
        cursor_pos = self.input_cursor - display_offset
        if 0 <= cursor_pos < max_display:
            self.win.addch(input_y, input_x + cursor_pos, '_', curses.A_BLINK)
        
        # Instructions
        self.win.addstr(start_y + prompt_height - 2, start_x + 2, 
                      "ENTER: Zatwierdź  |  ESC: Anuluj", curses.A_DIM)
        
        # Make cursor visible for text input
        curses.curs_set(1)
        self.win.refresh()

    def _handle_prompt_key(self, key):
        """Handle key press in prompt mode"""
        if key in (curses.KEY_ENTER, 10, 13):  # Enter key
            if self.prompt_value.strip():  # Only proceed if value isn't empty
                # Handle save game prompt
                success = self.gra.zapisz_gre(self.prompt_value.strip())
                if success:
                    self.status_msg = f"Gra zapisana jako '{self.prompt_value}'"
                else:
                    self.status_msg = "Wystąpił błąd podczas zapisywania gry"
                
                self.prompt_active = False
                curses.curs_set(0)  # Hide cursor
        elif key == 27:  # ESC key
            self.prompt_active = False
            curses.curs_set(0)  # Hide cursor
        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:  # Backspace
            if self.input_cursor > 0:
                self.prompt_value = (self.prompt_value[:self.input_cursor-1] + 
                                  self.prompt_value[self.input_cursor:])
                self.input_cursor -= 1
        elif key == curses.KEY_DC:  # Delete key
            if self.input_cursor < len(self.prompt_value):
                self.prompt_value = (self.prompt_value[:self.input_cursor] + 
                                  self.prompt_value[self.input_cursor+1:])
        elif key == curses.KEY_LEFT:
            self.input_cursor = max(0, self.input_cursor - 1)
        elif key == curses.KEY_RIGHT:
            self.input_cursor = min(len(self.prompt_value), self.input_cursor + 1)
        elif key == curses.KEY_HOME:
            self.input_cursor = 0
        elif key == curses.KEY_END:
            self.input_cursor = len(self.prompt_value)
        elif 32 <= key <= 126:  # Printable characters
            self.prompt_value = (self.prompt_value[:self.input_cursor] + 
                              chr(key) + 
                              self.prompt_value[self.input_cursor:])
            self.input_cursor += 1

    def _show_tutorial(self):
        """Display a pop-up modal with basic controls."""
        h, w = self.win.getmaxyx()
        tw, th = 40, 15  # Increased height for additional menu controls
        start_y, start_x = (h - th) // 2, (w - tw) // 2
        win = curses.newwin(th, tw, start_y, start_x)
        win.box()
        lines = [
            " PORADNIK PASJANSA ",
            "",
            " ←/→ : Move selector",
            " SPACE : Draw card",
            " O : Select card from odkryty pile",
            " F : Auto-move to foundation",
            " 1-4 : Select foundation pile",
            " ENTER : Select/Move card",
            " ESC : Cancel selection",
            " M : Open menu (save/load)",
            " Q : Quit game",
            "",
            "",
            " Press any key to start "
        ]
        for idx, txt in enumerate(lines):
            win.addstr(1 + idx, 2, txt)
        win.refresh()
        win.getch()
        win.clear()
        win.refresh()

    def can_move_king_to_empty(self):
        """Check if there's a king available to move to an empty column."""
        # Check if we have a king in odkryty pile
        if (not self.gra.stos_odkryty.jest_pusty() and 
            self.gra.stos_odkryty.wierzchnia_karta().figura == Figura.KROL):
            return True
            
        # Check if we have a king at the top of any non-empty column
        for i, kolumna in enumerate(self.gra.kolumny):
            if (i != self.selected and not kolumna.jest_pusty() and 
                kolumna.wierzchnia_karta().odkryta and 
                kolumna.wierzchnia_karta().figura == Figura.KROL):
                return True
                
        # If source column is selected, check if its top card is a king
        if (self.source_col is not None and 
            not self.gra.kolumny[self.source_col].jest_pusty() and 
            self.gra.kolumny[self.source_col].wierzchnia_karta().figura == Figura.KROL):
            return True
            
        return False

    def _draw(self):
        self.win.clear()
        # draw reserve
        self.win.addstr(1, 2, "Rezerwowy ", curses.A_BOLD)
        sym = "[##]" if not self.gra.stos_rezerwowy.jest_pusty() else "[  ]"
        self.win.addstr(1, 14, sym, curses.color_pair(2))

        # draw odkryty with highlight when selected
        self.win.addstr(1, 20, "Odkryty ", curses.A_BOLD)
        top = self.gra.stos_odkryty.wierzchnia_karta()
        disp = str(top) if top else "[  ]"
        color = curses.color_pair(1) if top and top.jest_czerwona else curses.color_pair(2)
        attr = color | curses.A_REVERSE if self.odkryty_selected else color
        self.win.addstr(1, 29, disp, attr)

        # draw foundations
        for idx, stos in enumerate(self.gra.stosy_koncowe):
            x = 2 + idx*6
            self.win.addstr(3, x, f"{stos.kolor.value[0]}", curses.A_BOLD)
            top = stos.wierzchnia_karta()
            disp = str(top) if top else "[  ]"
            col = curses.color_pair(1 if stos.kolor.value[1]=="czerwony" else 2)
            
            # Highlight the selected foundation
            if idx == self.selected_foundation:
                attr = col | curses.A_REVERSE
            else:
                attr = col
                
            self.win.addstr(4, x, disp, attr)

        # draw columns with empty column indicator
        for i, kol in enumerate(self.gra.kolumny):
            x = 2 + i*6
            
            # Mark empty columns differently
            if kol.jest_pusty():
                if i == self.selected:
                    self.win.addstr(7, x, "[   ]", curses.A_REVERSE)
                else:
                    self.win.addstr(7, x, "[---]", curses.A_DIM)
            else:
                for j, karta in enumerate(kol.karty):
                    y = 7 + j
                    col = curses.color_pair(1) if karta.jest_czerwona else curses.color_pair(2)
                    
                    # Different highlighting for current selection and source column
                    if i == self.selected:
                        attr = col | curses.A_REVERSE
                    elif i == self.source_col:
                        attr = col | curses.A_UNDERLINE | curses.A_BOLD
                    else:
                        attr = col
                    
                    self.win.addstr(y, x, str(karta), attr)

        # Display the current status message
        status_color = curses.color_pair(3) if self.game_over else curses.A_ITALIC
        self.win.addstr(20, 2, self.status_msg, status_color)
        
        # Show moves count and available moves
        h, w = self.win.getmaxyx()
        moves_txt = f"Ruchy: {self.gra.ruchy}"
        self.win.addstr(1, w - len(moves_txt) - 2, moves_txt)
        
        # Display available moves count
        available_moves = self.gra.licz_dostepne_ruchy()
        avail_txt = f"Dostępne ruchy: {available_moves}"
        avail_color = curses.color_pair(3) if available_moves < 3 else curses.A_NORMAL
        self.win.addstr(2, w - len(avail_txt) - 2, avail_txt, avail_color)
        
        # Display game over message if no moves available
        if self.game_over:
            game_over_txt = "KONIEC GRY! Brak możliwych ruchów."
            self.win.addstr(h-3, (w-len(game_over_txt))//2, game_over_txt, curses.color_pair(3) | curses.A_BOLD)
            help_txt = "Naciśnij 'N' dla nowej gry lub 'M' dla menu"
            self.win.addstr(h-2, (w-len(help_txt))//2, help_txt, curses.A_BOLD)
        
        # Display help text with updated instructions including menu
        if not self.game_over:
            self.win.addstr(22, 2, "ENTER: Move | M: Menu | F: To foundation | 1-4: Foundation | Q: Quit", curses.A_DIM)
        
        self.win.refresh()

def main():
    ui = CursesUI()
    ui.run()

if __name__ == "__main__":
    main()
