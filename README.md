# Pasjans (Solitaire) Terminal Game

![Solitaire Game](https://img.shields.io/badge/Game-Solitaire-green)
![Python](https://img.shields.io/badge/Python-3.6+-blue)

## Features

- 🎮 Full-featured Solitaire game with intuitive controls
- 🎴 Beautiful card display with Unicode symbols and colors
- 💾 Game saving and loading functionality
- 📊 Game statistics tracking
- 🔄 Automatic detection of available moves

## Getting Started

### Prerequisites

You need Python 3.6 or higher to run this game.

### Installation

1. Clone the repository or download the game files
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Run the game:

```bash
python solitaire.py
```

## How to Play

### Controls

- **←/→** : Move selector between columns
- **Space** : Draw card from deck
- **O** : Select card from revealed pile
- **F** : Auto-move to foundation
- **1-4** : Select foundation pile
- **Enter** : Select/Move card
- **Esc** : Cancel selection
- **M** : Open menu (save/load)
- **Q** : Quit game

### Game Rules

1. **Goal**: Move all cards to the foundation piles, sorted by suit from Ace to King.
2. **Tableau**: Cards in the tableau must be placed in descending order and alternating colors.
3. **Foundation**: Cards in the foundation must be of the same suit and placed in ascending order (A,2,3,...,K).
4. **Stock**: Click to draw cards when you have no moves available.

## Game Structure

The game is organized around several key components:

- **Card Class**: Represents individual playing cards
- **StosKart (CardPile)**: Base class for all card piles 
- **Terminal UI**: Provides the curses-based user interface
- **Game Logic**: Handles the rules and valid move determination

## Save/Load System

The game automatically creates a `saves` directory where your saved games are stored. You can:

- Save your current game with a custom name
- Load previous games from the menu
- Continue your progress any time

## Author

Patryk - May 2025

## License

This project is available as open source under the terms of the MIT License.
