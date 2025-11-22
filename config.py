from typing import List, Dict
from pathlib import Path
import sys

# --- Configurazione Percorsi ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'

# --- VARIABILI DI CONFIGURAZIONE DATI ---
FILE_PATH: str = str(DATA_DIR / 'players_data-2024_2025.csv')
SOURCE_FILES: List[str] = [
    # Top 5 League data (il tuo file originale)
    str(DATA_DIR / 'players_data-2024_2025.csv'), 
    str(DATA_DIR / 'db_championship_2024_2025.csv'),
    str(DATA_DIR / 'db_gk_championship_2024_2025.csv'),
    str(DATA_DIR / 'db_argentina_2024_2025.csv'),
    str(DATA_DIR / 'db_gk_argentina_2024_2025.csv'),
    str(DATA_DIR / 'db_belgian_2024_2025.csv'),
    str(DATA_DIR / 'db_gk_belgian_2024_2025.csv'),
    str(DATA_DIR / 'db_brazil_2024_2025.csv'),
    str(DATA_DIR / 'db_gk_brazil_2024_2025.csv'),
    str(DATA_DIR / 'db_eredivisie_2024_2025.csv'),
    str(DATA_DIR / 'db_gk_eredivisie_2024_2025.csv'),
    str(DATA_DIR / 'db_primeiraliga_2024_2025.csv'),
    str(DATA_DIR / 'db_gk_primeiraliga_2024_2025.csv'),
    str(DATA_DIR / 'db_serieb_2024_2025.csv'),
    str(DATA_DIR / 'db_gk_serieb_2024_2025.csv')
]

# Mappa per tradurre i nomi dei file delle leghe minori in nomi leggibili
LEAGUE_NAME_MAP: Dict[str, str] = {
    'db_championship_2024_2025.csv': 'Championship',
    'db_gk_championship_2024_2025.csv': 'Championship',
    'db_brazil_2024_2025.csv': 'Série A Brazil',
    'db_gk_brazil_2024_2025.csv': 'Série A Brazil',
    'db_argentina_2024_2025.csv': 'Primera División',
    'db_gk_argentina_2024_2025.csv': 'Primera División',
    'db_belgian_2024_2025.csv': 'Jupiler Pro League',
    'db_gk_belgian_2024_2025.csv': 'Jupiler Pro League',
    'db_eredivisie_2024_2025.csv': 'Eredivisie',
    'db_gk_eredivisie_2024_2025.csv': 'Eredivisie',
    'db_primeiraliga_2024_2025.csv': 'Primeira Liga',
    'db_gk_primeiraliga_2024_2025.csv': 'Primeira Liga',
    'db_serieb_2024_2025.csv': 'Serie B',
    'db_gk_serieb_2024_2025.csv': 'Serie B'
    # Aggiungi altre mappature se necessario
}

VALUE_FILE_PATH: str = str(DATA_DIR / 'player_latest_market_value.csv')
PROFILE_FILE_PATH: str = str(DATA_DIR / 'player_profiles.csv')

TRANSFERS_FILE_PATH: str = str(DATA_DIR / 'data_summer2025.csv') # Sostituisci se il nome è diverso

# Percorso del file finale che userà la tua IA (Output)
MASTER_CSV_PATH: str = str(DATA_DIR / 'dataset_master_pulito.csv')
MASTER_CSV_PATH_FINAL: str = str(DATA_DIR / 'dataset_master_final.csv')

MIN_MINUTES: int = 900
RUOLI: List[str] = ['FW', 'MF', 'DF', 'GK']

# Colonne che saranno mantenute (Metadata)
METADATA_COLS: List[str] = ['Rk', 'Player', 'Nation', 'Pos', 'Team', 'Comp', 'Age', '90s']
FILTER_COL: List[str] = ['Min'] 

# Colonne che non vanno divise per 90s (percentuali o ratio)
PERCENTAGE_COLS: List[str] = ['Cmp%', 'Save%', 'CS%']

# Dizionario delle Feature Rilevanti per Ruolo
ROLE_FEATURES: Dict[str, List[str]] = {
    'FW': ['Gls', 'Ast', 'xG', 'KP', 'Touches', 'G+A', 'npxG', 'G-PK', 'PPA', 'Carries', 'PrgC', 'PrgR', 'TklW', 'Dis', 'Mis'],
    'MF': ['PrgP', 'PrgC', 'Cmp%', 'TklW', 'Recov', 'Gls', 'Ast', 'xG', 'xAG', 'KP', 'PPA', 'PrgR', 'Tkl', 'Int', 'Tkl+Int', 'Blocks', 'Err'],
    'DF': ['Tkl', 'Int', 'Clr', 'PrgP', 'Touches', 'TklW', 'Blocks', 'Err', 'Recov', 'PrgC', 'Cmp%', 'Gls', 'Ast', 'xG'],
    'GK': ['GA', 'Saves', 'Save%', 'CS', 'CS%', 'PKA', 'PKsv', 'Touches', 'Cmp%']
}


# Valori 'k' ottimali decisi dall'analisi Elbow Method sul DATASET COMPLETO
OPTIMAL_K: Dict[str, int] = {
    'FW': 5,
    'MF': 6,
    'DF': 4,
    'GK': 2
}

CLUSTER_NAMES_MAP = {
    'FW': {
        0: 'Seconda Punta',
        1: 'Attaccante d\'Area',
        2: 'Ala Tornante',
        3: 'Bomber',
        4: 'Ala d\'Attacco'
    },
    'MF': {
        0: 'Regista Arretrato',
        1: 'Centrocampista Offensivo',
        2: 'Centrocampista di Equilibrio',
        3: 'Mediano',
        4: 'Centrocampista "Box-to-Box"',
        5: 'Rifinitore'
    },
    'DF': {
        0: 'Difensore Centrale Impostatore',
        1: 'Stopper',
        2: 'Terzino Difensivo',
        3: 'Terzino Fluidificante',
    },
    'GK': {
        0: 'Portiere "Saracinesca"',
        1: 'Portiere "Sotto Assedio"',
    }
}

# Lista per il dropdown "Campionato"
LEAGUES_LIST: List[str] = [
    'Belgian Pro League',
    'Bundesliga',
    'Championship',
    'Eredivisie',
    'Liga Profesional Argentina',
    'La Liga',
    'Liga MX',
    'Ligue 1',
    'Premier League',
    'Primeira Liga',
    'Serie A',
    'Serie B',
    'Série A',
]