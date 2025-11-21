import pandas as pd # type: ignore
import joblib # type: ignore
from pathlib import Path
import config
import math
import numpy as np # type: ignore
import sys

# --- Configurazione Percorsi ---
BASE_DIR = Path(__file__).resolve().parent

# --- Costanti ---
ROWS_PER_PAGE = 7 
SORT_BY_OPTIONS = [
    {'label': 'Nome (A-Z)', 'value': 'name_asc'},
    {'label': 'Nome (Z-A)', 'value': 'name_desc'},
    {'label': 'Età (Crescente)', 'value': 'age_asc'},
    {'label': 'Età (Decrescente)', 'value': 'age_desc'},
    {'label': 'Campionato (A-Z)', 'value': 'league_asc'},
    {'label': 'Campionato (Z-A)', 'value': 'league_desc'},
    {'label': 'Nazionalità (A-Z)', 'value': 'nation_asc'},
    {'label': 'Nazionalità (Z-A)', 'value': 'nation_desc'},
]

DATA_PATH = BASE_DIR / 'data' / 'dataset_master_unified_2526.parquet'
ARTIFACTS_DIR = BASE_DIR / 'artifacts'

# --- Variabili Globali (Inizialmente vuote per Lazy Loading) ---
DATABASE_DF = pd.DataFrame()
all_roles_options = []
PLAYER_SEARCH_OPTIONS = []

def load_data():
    """
    Carica i dati pesanti (CSV, Joblib) in modo sincrono.
    Popola le variabili globali DATABASE_DF, all_roles_options, PLAYER_SEARCH_OPTIONS.
    """
    global DATABASE_DF, all_roles_options, PLAYER_SEARCH_OPTIONS
    
    if not DATABASE_DF.empty:
        print("Dati già caricati.")
        return # Già caricati

    print("Avvio caricamento dati...")
    
    # 1. Carica PCA Dataframes per valid_player_ids
    try:
        print("Caricamento modelli PCA...")
        PCA_DATAFRAMES = joblib.load(ARTIFACTS_DIR / 'pca_dataframes.joblib')
    except Exception as e:
        print(f"Attenzione: Impossibile caricare pca_dataframes.joblib. {e}")
        PCA_DATAFRAMES = {}

    valid_player_ids = set()
    if isinstance(PCA_DATAFRAMES, dict):
        for role, df in PCA_DATAFRAMES.items():
            if isinstance(df, pd.DataFrame):
                valid_player_ids.update(df.index.astype(str))
    print(f"--- Trovati {len(valid_player_ids)} giocatori validi (900+ min) ---")

    # 2. Carica DATABASE_DF (con Caching)
    print("Caricamento Database Giocatori...")
    
    # Percorso per la cache del dataframe processato
    # cache_path = ARTIFACTS_DIR / 'database_df_cache.joblib'
    
    # Controlla se esiste una cache valida
    loaded_from_cache = False
    # if cache_path.exists():
    #     try:
    #         print("Trovata cache dati, caricamento veloce...")
    #         DATABASE_DF = joblib.load(cache_path)
    #         loaded_from_cache = True
    #         print("--- DATABASE_DF caricato dalla cache! ---")
    #     except Exception as e:
    #         print(f"Errore caricamento cache: {e}. Si procede con il caricamento standard.")
    
    if not loaded_from_cache:
        print("Lettura file Parquet (potrebbe richiedere tempo)...")
        DATABASE_DF = _prepare_database_dataframe(PCA_DATAFRAMES)
        
        # Salva in cache per la prossima volta
        # try:
        #     print("Salvataggio cache per avvii futuri...")
        #     joblib.dump(DATABASE_DF, cache_path)
        #     print("--- DATABASE_DF salvato in cache. ---")
        # except Exception as e:
        #     print(f"Impossibile salvare la cache: {e}")
    
    # 3. Carica all_roles_options
    print("Configurazione ruoli...")
    all_roles_options = get_all_roles_options()

    # 4. Crea PLAYER_SEARCH_OPTIONS
    print("Indicizzazione giocatori per la ricerca...")
    if not DATABASE_DF.empty and valid_player_ids:
        searchable_players_df = DATABASE_DF[DATABASE_DF['ID_Univoco'].isin(valid_player_ids)].copy()
        all_players_df = searchable_players_df[['ID_Univoco', 'Player', 'Team', 'Comp']].copy()
        all_players_df['label'] = all_players_df.apply(
            lambda row: f"{row['Player']} ({row['Team']}, {row['Comp']})",
            axis=1
        )
        PLAYER_SEARCH_OPTIONS = all_players_df.apply(
            lambda row: {'label': row['label'], 'value': str(row['ID_Univoco'])},
            axis=1
        ).tolist()
        print(f"--- Creati {len(PLAYER_SEARCH_OPTIONS)} suggerimenti di ricerca (filtrati da 900+ min) ---")
    else:
        PLAYER_SEARCH_OPTIONS = []
    
    print("Caricamento Dati completato.")

# --- Funzioni Helper ---

def make_blank_option():
    return {'label': ' ', 'value': ''}

def with_blank(options):
    return [make_blank_option()] + options

def get_all_roles_options():
    """
    Crea la lista di opzioni per il dropdown 'Ruolo', 
    mantenendoli ORDINATI per posizione (FW, MF, DF, GK).
    """
    all_roles_ordered = []
    for ruolo_key in config.RUOLI: # Es. ['FW', 'MF', 'DF', 'GK']
        role_group_names = config.CLUSTER_NAMES_MAP.get(ruolo_key, {})
        for role_name in role_group_names.values():
            if role_name not in all_roles_ordered:
                all_roles_ordered.append(role_name)
    return [{'label': role, 'value': role} for role in all_roles_ordered]

def _load_style_lookup(pca_dataframes=None) -> dict:
    """
    Carica dai joblib i cluster per ricavare il nome del ruolo/stile.
    Restituisce un dizionario {(player, comp): stile}.
    """
    lookup = {}
    
    if pca_dataframes is None:
        try:
            pca_dataframes = joblib.load(ARTIFACTS_DIR / 'pca_dataframes.joblib')
        except Exception:
            return lookup

    if not isinstance(pca_dataframes, dict):
        return lookup

    for role, df in pca_dataframes.items():
        if not isinstance(df, pd.DataFrame):
            continue
        required_cols = {'Player', 'Comp', 'Cluster'}
        if not required_cols.issubset(df.columns):
            continue
        style_map = config.CLUSTER_NAMES_MAP.get(role, {})
        subset = df[list(required_cols)].dropna()
        for id_univoco, row in subset.iterrows(): 
            try:
                cluster_id = int(row['Cluster'])
            except (ValueError, TypeError):
                continue
            # La chiave ora è l'ID univoco, che è l'indice
            lookup[str(id_univoco)] = style_map.get(cluster_id, f"{role} Cluster {cluster_id}")
    return lookup

def _prepare_database_dataframe(pca_dataframes=None) -> pd.DataFrame:
    """
    Carica e pulisce il dataset principale da utilizzare nella tabella DB.
    """
    try:
        raw_df = pd.read_parquet(DATA_PATH)
        raw_df['ID_Univoco'] = raw_df.index.astype(str)
    except Exception:
        return pd.DataFrame()

    columns_needed = ['ID_Univoco', 'Player', 'Pos', 'Age', 'Nation', 'Comp', 'Team']
    existing_columns = [col for col in columns_needed if col in raw_df.columns]
    df = raw_df[existing_columns].copy()

    for col in columns_needed:
        if col not in df.columns:
            df[col] = ""

    df['Player'] = df['Player'].fillna('').astype(str).str.strip()
    df['Pos'] = df['Pos'].fillna('').astype(str).str.strip()
    df['Comp'] = df['Comp'].fillna('').astype(str).str.strip()
    df['Nation'] = df['Nation'].fillna('').astype(str).str.strip()
    df['Team'] = df['Team'].fillna('').astype(str).str.strip()

    df['Age'] = pd.to_numeric(df['Age'], errors='coerce')
    df['AgeInt'] = df['Age'].round().astype('Int64')

    df['NationCode'] = df['Nation'].apply(
        lambda value: str(value).strip().split(' ')[-1].upper() if value else ''
    )

    df['PlayerKey'] = df['Player'].str.strip().str.lower()
    df['CompKey'] = df['Comp'].str.strip().str.lower()
    df['PosUpper'] = df['Pos'].str.upper()
    df['SearchName'] = df['Player'].str.lower()

    style_lookup = _load_style_lookup(pca_dataframes)
    df['StyleName'] = df['ID_Univoco'].map(style_lookup)

    df['StyleName'] = df['StyleName'].fillna('Stile non disponibile')
    df['DisplayAge'] = df['AgeInt'].apply(lambda x: "" if pd.isna(x) else str(int(x)))

    return df.reset_index(drop=True)

def _filter_database(name_value, pos_value, role_value, age_min_value, age_max_value, league_value, sort_by_value) -> pd.DataFrame:
    """
    Applica i filtri selezionati dall'utente al dataframe principale.
    """
    if DATABASE_DF.empty:
        return DATABASE_DF
    filtered = DATABASE_DF.copy()

    if name_value:
        search_term = str(name_value).strip().lower()
        if search_term:
            filtered = filtered[filtered['SearchName'].str.contains(search_term, na=False)]
    if pos_value:
        pos_term = str(pos_value).upper()
        filtered = filtered[filtered['PosUpper'].str.contains(pos_term, na=False)]
    if role_value:
        filtered = filtered[filtered['StyleName'] == role_value]
    try:
        if age_min_value is not None:
            age_min = int(round(float(age_min_value)))
            filtered = filtered[filtered['AgeInt'] >= age_min]
    except (ValueError, TypeError):
        pass
    try:
        if age_max_value is not None:
            age_max = int(round(float(age_max_value)))
            filtered = filtered[filtered['AgeInt'] <= age_max]
    except (ValueError, TypeError):
        pass
    if league_value:
        filtered = filtered[filtered['Comp'] == league_value]
    
    if sort_by_value:
        if sort_by_value == 'name_asc':
            filtered = filtered.sort_values(by='Player', ascending=True)
        elif sort_by_value == 'name_desc':
            filtered = filtered.sort_values(by='Player', ascending=False)
        elif sort_by_value == 'age_asc':
            filtered = filtered.sort_values(by='AgeInt', ascending=True, na_position='last')
        elif sort_by_value == 'age_desc':
            filtered = filtered.sort_values(by='AgeInt', ascending=False, na_position='last')
        elif sort_by_value == 'nation_asc':
            filtered['NationCode'] = filtered['NationCode'].replace('', np.nan)
            filtered = filtered.sort_values(by='NationCode', ascending=True, na_position='last')
        elif sort_by_value == 'nation_desc':
            filtered['NationCode'] = filtered['NationCode'].replace('', np.nan)
            filtered = filtered.sort_values(by='NationCode', ascending=False, na_position='last')
        elif sort_by_value == 'league_asc':
            filtered['Comp'] = filtered['Comp'].replace('', np.nan)
            filtered = filtered.sort_values(by='Comp', ascending=True, na_position='last')
        elif sort_by_value == 'league_desc':
            filtered['Comp'] = filtered['Comp'].replace('', np.nan)
            filtered = filtered.sort_values(by='Comp', ascending=False, na_position='last')
            
    return filtered