import pandas as pd # type: ignore
import numpy as np # type: ignore
from typing import Dict, List
import os
import sys
from pathlib import Path
import unicodedata
import re

# --- Funzione per gestire i percorsi sia in Dev che in .Exe ---
def get_base_path():
    """
    Restituisce il percorso base corretto.
    Se siamo in un eseguibile PyInstaller, usa sys._MEIPASS.
    Se siamo in sviluppo locale, usa la cartella corrente del file.
    """
    if getattr(sys, 'frozen', False):
        # Se siamo compilati in un .exe
        return Path(sys._MEIPASS)
    else:
        # Se stiamo eseguendo lo script python normalmente
        return Path(__file__).resolve().parent

# --- Configurazione Pandas ---
pd.set_option('display.max_rows', 10)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.set_option('display.precision', 3)


class PlayerDataPreprocessor:
    """
    Classe per la gestione e la pre-elaborazione del dataset dei calciatori, 
    suddividendo i dati per ruolo e convertendo le statistiche in metriche per 90 minuti (x90).
    """

    def __init__(self, master_file_path: str, 
                 ruoli: List[str], 
                 metadata_cols: List[str], role_features: Dict[str, List[str]], 
                 percentage_cols: List[str], filter_col: List[str]):
        
        # --- ATTRIBUTI MODIFICATI ---
        self.MASTER_FILE_PATH = master_file_path # <-- Unico file
        # self.MIN_MINUTES rimosso perché il dataset è già filtrato
        self.RUOLI = ruoli
        
        # Aggiungiamo Ht. e Wt. ai metadati se non ci sono già
        self.METADATA_COLS = metadata_cols
        for col in ['Ht.', 'Wt.']:
            if col not in self.METADATA_COLS:
                self.METADATA_COLS.append(col)
                
        self.ROLE_FEATURES = role_features
        self.PERCENTAGE_COLS = percentage_cols
        self.FILTER_COL = filter_col

    # --- Funzioni di Caricamento e Filtro Iniziale ---
    def _coerce_numeric_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Converte le colonne statistiche in float e riempie i NaN 
        SOLO per le colonne numeriche.
        """
        
        # 1. Identifica le colonne che DEVONO essere numeriche
        # Escludiamo le colonne di testo e i metadati fisici (Ht., Wt.) che possono essere "ND"
        text_cols = ['Rk', 'Player', 'Nation', 'Pos', 'Team', 'Comp', 'Valore_Mercato', 'Ht.', 'Wt.']
        
        numeric_cols_to_check = [col for col in self.METADATA_COLS if col not in text_cols]
        numeric_cols_to_check.extend(self.FILTER_COL) 
        
        all_feature_cols = list(set(col for features in self.ROLE_FEATURES.values() for col in features))
        numeric_cols_to_check.extend(all_feature_cols)

        # Prendi solo quelle che esistono nel DF
        cols_to_coerce = list(set(col for col in numeric_cols_to_check if col in df.columns))

        print(f"   -> Trovate {len(cols_to_coerce)} colonne da convertire in numerico.")
        
        # 2. Applica il fillna(0) SOLO a queste colonne
        df[cols_to_coerce] = df[cols_to_coerce].fillna(0)
        
        # 3. Converti in numerico
        for col in cols_to_coerce:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 4. Riempi di nuovo (sicurezza per i valori 'coerce' falliti)
        df[cols_to_coerce] = df[cols_to_coerce].fillna(0)
        
        print("   -> Tipologia dati numerici forzata a Float (solo colonne statistiche).")
        
        return df

    def _setup_and_load(self) -> pd.DataFrame:
        """
        Carica il file CSV master già pulito e unito.
        """
        print("\n--- Caricamento Dataset Master Statico ---")
        try:
            # 1. Carica il singolo file master
            df_master = pd.read_csv(self.MASTER_FILE_PATH, low_memory=False)
            print(f"   -> Caricato {self.MASTER_FILE_PATH}. Righe totali: {len(df_master)}")
        except FileNotFoundError:
            print(f"ERRORE: File '{self.MASTER_FILE_PATH}' non trovato.")
            print("Esegui prima 'crea_dataset_master.py' per generarlo.")
            raise

        # --- LEAGUE EXCHANGE RATE ADJUSTMENT (PRE-TRAINING) ---
        print("\n--- Applicazione League Exchange Rate (Pre-Training) ---")
        
        import config
        import numpy as np # type: ignore
        
        # Verifica presenza colonna Comp
        if 'Comp' not in df_master.columns:
            print("   ⚠️ ATTENZIONE: Colonna 'Comp' non trovata. Ponderazione saltata.")
        else:
            # Mappa coefficienti
            coefficients = df_master['Comp'].map(config.LEAGUE_COEFFICIENTS).fillna(config.DEFAULT_LEAGUE_COEFFICIENT)
            
            # Identifica colonne numeriche da ponderare
            numeric_cols = df_master.select_dtypes(include=[np.number]).columns.tolist()
            cols_to_adjust = [col for col in numeric_cols if col not in config.COLS_TO_EXCLUDE_FROM_ADJUSTMENT]
            
            print(f"   Colonne numeriche: {len(numeric_cols)} | Da ponderare: {len(cols_to_adjust)}")
            
            # Applica ponderazione
            for col in cols_to_adjust:
                df_master[col] = df_master[col].mul(coefficients)
            
            print(f"   ✓ Ponderazione PRE-TRAINING completata")
            
            # Verifica: Mostra media di una statistica chiave per diverse leghe
            if 'Gls' in df_master.columns:
                sample_leagues = ['Premier League', 'Serie A', 'Serie B']
                for league in sample_leagues:
                    if league in df_master['Comp'].values:
                        avg_gls = df_master[df_master['Comp'] == league]['Gls'].mean()
                        coeff = config.LEAGUE_COEFFICIENTS.get(league, config.DEFAULT_LEAGUE_COEFFICIENT)
                        print(f"      {league} (x{coeff}): Media Gls = {avg_gls:.2f}")
        
        # --- FINE LEAGUE EXCHANGE RATE ---
        
        # Salva df_master come attributo per verifica post-training
        self.df_master = df_master.copy()
        
        # 2. Creazione ID Univoco (Robusto)
        try:
            # 2. Creazione ID Univoco (Robusto)
            # L'indice del DataFrame (0, 1, 2...) è ora l'ID univoco.
            df_master['ID_Univoco'] = df_master.index.astype(str)
            df_master.set_index('ID_Univoco', inplace=True)
            print("   -> Indice (0...N) impostato come ID_Univoco.")
        except Exception as e:
            raise KeyError(f"Impossibile creare 'ID_Univoco' a causa di: {e}")

        # 3. Fase di Filtraggio Colonne
        all_feature_cols = list(set(col for features in self.ROLE_FEATURES.values() for col in features))
        cols_to_keep = self.METADATA_COLS + all_feature_cols + self.FILTER_COL 
        cols_to_keep = list(set(cols_to_keep + ['Player', 'Comp', 'Pos', 'Team'])) 
        cols_to_keep = [col for col in cols_to_keep if col in df_master.columns]
        df = df_master[cols_to_keep].copy()
        
        df = self._coerce_numeric_types(df)
        return df
    

    def _clean_and_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applica l'ID univoco e rimuove le colonne di servizio."""
        
        print("\n--- Fase di Pulizia Generale ---")
        
        # 3.1 Imposta Rk come indice (ID univoco)
        # if 'Rk' in df.columns:
        #     df.set_index('Rk', inplace=True)
        #     print("   -> Colonna 'Rk' impostata come ID/Indice.")

        # 3.2 Filtro Minutaggio RIMOSSO (Dataset già filtrato)
        # df_filtrato = df[df['Min'] >= self.MIN_MINUTES].copy()
        df_filtrato = df.copy()
        print(f"   -> Filtro Minutaggio ignorato (Dataset già filtrato). Righe: {len(df_filtrato)}")

        # 3.3 Rimuove la colonna 'Min' dopo il filtraggio
        if 'Min' in df_filtrato.columns:
            df_filtrato.drop(columns=['Min'], inplace=True)
            
        return df_filtrato

    def _create_role_dataframes(self, df_filtrato: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Crea i DataFrames separati per ruolo, filtrando le colonne specifiche per ogni DF."""
        
        dataframes_ruolo = {}
        print("\n--- Creazione DataFrames Filtrati per Ruolo ---")
        
        # Metadati da mantenere (escluso Rk, che è l'indice)
        metadata_cols_no_rk = [col for col in self.METADATA_COLS if col != 'Rk']
        
        for ruolo in self.RUOLI:
            # Filtra il DataFrame per il ruolo specifico (mantenendo la duplicazione se presente)
            df_ruolo_completo = df_filtrato[df_filtrato['Pos'].str.contains(ruolo, na=False)].copy()
            
            # Definisce le colonne finali da mantenere: Metadati + Feature specifiche
            feature_specifiche = self.ROLE_FEATURES.get(ruolo, [])
            colonne_finali = metadata_cols_no_rk + feature_specifiche
            
            # Applica il filtro delle colonne
            colonne_finali_esistenti = [col for col in colonne_finali if col in df_ruolo_completo.columns]
            df_ruolo_filtrato = df_ruolo_completo[colonne_finali_esistenti].copy()
            
            df_ruolo_filtrato['Ruolo_Primario'] = ruolo
            dataframes_ruolo[ruolo] = df_ruolo_filtrato
            
            print(f"   -> DF {ruolo} ({df_ruolo_filtrato.shape[0]} Giocatori) creato con {len(feature_specifiche)} feature.")
            
        return dataframes_ruolo

    # --- Nuova Funzione di Feature Engineering ---
    
    def _convert_to_x90(self, dataframes_ruolo: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Converte tutte le statistiche grezze in metriche per 90 minuti (x90)."""
        
        print("\n--- Conversione Statistiche in Metriche per 90 Minuti (x90) ---")
        dataframes_x90 = {}
        
        for ruolo, df in dataframes_ruolo.items():
            df_x90 = df.copy()
            
            # --- RINFORZO DELLA PULIZIA ---
            # Questo è il passaggio anti-errore. Forziamo le colonne statistiche a float
            # un'ultima volta prima della divisione.
            # ESCLUDIAMO ESPLICITAMENTE Ht. e Wt. dalla divisione per 90s
            cols_to_divide = [
                col for col in df.columns 
                if col not in self.METADATA_COLS and col not in self.PERCENTAGE_COLS and col != 'Ruolo_Primario' and col not in ['Ht.', 'Wt.']
            ]
            
            for col in cols_to_divide:
                df_x90[col] = pd.to_numeric(df_x90[col], errors='coerce')
            
            df_x90['90s'] = pd.to_numeric(df_x90['90s'], errors='coerce') # Forza anche il divisore

            # Sostituisce i NaN che potrebbero essere emersi dalla coercizione con 0
            df_x90.fillna(0, inplace=True) 
            
            # ---------------------------

            # Esegue la divisione come prima
            for col in cols_to_divide:
                new_col_name = f"{col}_x90"
                # A questo punto, sia df_x90[col] che df_x90['90s'] dovrebbero essere float.
                # Gestiamo esplicitamente la divisione per zero con .replace([0], np.nan)
                
                # Impedisce la divisione per zero impostando i divisori 0 a NaN temporaneamente
                # La divisione NaN/X è 0, che poi fillna(0) gestisce
                
                # Applica la formula: Statistica / 90s
                df_x90[new_col_name] = df_x90[col] / df_x90['90s'].replace([0], np.nan) 
                
                df_x90.drop(columns=[col], inplace=True)
            
            # Pulizia finale (gestisce i NaN prodotti dalla divisione per zero)
            df_x90.replace([np.inf, -np.inf], np.nan, inplace=True)
            df_x90.fillna(0, inplace=True)

            print(f"   -> DF {ruolo} convertito. Ora contiene {len(df_x90.columns)} colonne.")
            dataframes_x90[ruolo] = df_x90
            
        return dataframes_x90

    def prepare_data(self) -> Dict[str, pd.DataFrame]:
        """Esegue l'intero flusso di pre-elaborazione e restituisce i DataFrames finali."""
        
        # 1. Caricamento e Filtro Colonne Iniziale + Pulizia Tipi
        df_raw = self._setup_and_load()
        
        # 2. Pulizia (Rk Index, Minutaggio) e Filtro Minutaggio
        df_clean = self._clean_and_filter(df_raw)
        
        # 3. Creazione DataFrames per Ruolo con colonne specifiche
        dataframes_ruolo = self._create_role_dataframes(df_clean)
        
        # 4. Conversione a x90 (Feature Engineering)
        dataframes_x90 = self._convert_to_x90(dataframes_ruolo)
        
        return dataframes_x90


# Alla fine di PlayerDataPreprocessor.py

if __name__ == "__main__":
    
    import config 
    import traceback
    
    pd.set_option('display.max_rows', 20)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1500)

    print("--- TEST: PlayerDataPreprocessor (con NUOVO Dataset Unificato) ---")
    
    # Percorso del nuovo dataset unificato
    base_dir = Path(__file__).resolve().parent.parent
    new_dataset_path = base_dir / 'data' / 'dataset_master_unified_2526.csv'
    
    print(f"Usando dataset: {new_dataset_path}")

    try:
        processor = PlayerDataPreprocessor(
            master_file_path=str(new_dataset_path), 
            ruoli=config.RUOLI,
            metadata_cols=config.METADATA_COLS,
            role_features=config.ROLE_FEATURES,
            percentage_cols=config.PERCENTAGE_COLS,
            filter_col=config.FILTER_COL
        )
        
        # Esegui l'intera pipeline
        dataframes_x90 = processor.prepare_data()

        print("\n--- PIPELINE COMPLETATA. ---")
        
        # Verifica su un ruolo (es. FW)
        role_to_check = 'FW'
        print(f"\n--- Controllo Dati Finali ({role_to_check}) ---")
        df_role = dataframes_x90.get(role_to_check)
        
        if df_role is not None:
            print(f"Dimensioni DF {role_to_check}: {df_role.shape}")
            
            # Verifica presenza colonne fisiche
            cols_phys = ['Ht.', 'Wt.']
            print(f"\nVerifica Colonne Fisiche {cols_phys}:")
            if all(col in df_role.columns for col in cols_phys):
                print(" -> OK: Colonne presenti.")
                print(df_role[['Player', 'Ht.', 'Wt.']].sample(10))
                
                # Verifica che non siano state divise per 90s (valori troppo piccoli)
                # Wt è in kg (es. 70, 80). Se Wt diventa 0.8, è stato diviso.
                
                sample_wt = pd.to_numeric(df_role['Wt.'], errors='coerce').dropna()
                if not sample_wt.empty:
                    mean_wt = sample_wt.mean()
                    print(f" -> Media Peso (Wt.): {mean_wt:.2f}")
                    if mean_wt < 10:
                        print(" -> WARNING: Il peso sembra troppo basso! È stato diviso per 90s?")
                    else:
                        print(" -> OK: Il peso sembra coerente (non diviso per 90s).")
            else:
                print(" -> ERROR: Colonne fisiche MANCANTI!")

        else:
            print(f"Nessun dato {role_to_check} trovato.")

    except Exception as e:
        print(f"\n--- ERRORE IMPREVISTO DURANTE IL TEST ---")
        print(e)
        traceback.print_exc()