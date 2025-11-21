import pandas as pd # type: ignore
import joblib   # type: ignore
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
from config import CLUSTER_NAMES_MAP

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

class SimilarityEngine:
    """
    Carica i modelli addestrati (artefatti) ed esegue le query di similarità.
    Gestisce le ricerche parziali e l'ambiguità dei nomi.
    """
    
    def __init__(self, artifacts_dir: str = "artifacts"):
        """
        Inizializza il motore. Carica solo le statistiche leggere.
        Gli artefatti pesanti vengono caricati in modo pigro (lazy loading).
        """
        print("--- Inizializzazione Motore di Similarità (Lazy Loading) ---")
        self.artifacts_dir = Path(artifacts_dir) if not isinstance(artifacts_dir, Path) else artifacts_dir
        
        # Flag per indicare se gli artefatti sono stati caricati
        self.artifacts_loaded = False
        
        # Inizializza attributi a None/Empty
        self.scalers = {}
        self.pcas = {}
        self.kmeans_models = {}
        self.knn_models = {}
        self.pca_dataframes = {}
        self.feature_columns = {}
        self.cluster_names = CLUSTER_NAMES_MAP
        
        # Carica SUBITO le statistiche delle feature (sono leggere e servono per la UI)
        try:
            import json
            stats_path = self.artifacts_dir / "feature_stats.json"
            if stats_path.exists():
                with open(stats_path, 'r') as f:
                    self.feature_stats = json.load(f)
                print(f"   -> Statistiche feature caricate.")
            else:
                self.feature_stats = {}
        except Exception as e:
            print(f"   Statistiche feature non disponibili: {e}")
            self.feature_stats = {}

    def load_artifacts(self, progress_callback=None):
        """
        Metodo pubblico per forzare il caricamento degli artefatti (es. all'avvio dell'app).
        """
        self._ensure_artifacts_loaded(progress_callback)

    def _ensure_artifacts_loaded(self, progress_callback=None):
        """
        Carica gli artefatti pesanti se non sono già stati caricati.
        """
        print(f"DEBUG: _ensure_artifacts_loaded chiamato. Loaded={self.artifacts_loaded}")
        if self.artifacts_loaded:
            print("DEBUG: Artefatti già caricati. Esco.")
            return

        print("--- Caricamento Artefatti Pesanti in corso... ---")
        if progress_callback:
            progress_callback(75, "Caricamento Scalers...")
        
        try:
            self.scalers = joblib.load(self.artifacts_dir / "scalers.joblib")
            
            if progress_callback:
                progress_callback(80, "Caricamento PCA...")
            self.pcas = joblib.load(self.artifacts_dir / "pcas.joblib")
            
            if progress_callback:
                progress_callback(85, "Caricamento Modelli KMeans...")
            self.kmeans_models = joblib.load(self.artifacts_dir / "kmeans_models.joblib")
            
            if progress_callback:
                progress_callback(90, "Caricamento Modelli k-NN...")
            self.knn_models = joblib.load(self.artifacts_dir / "knn_models.joblib")
            
            if progress_callback:
                progress_callback(95, "Caricamento Dataframes PCA...")
            self.pca_dataframes = joblib.load(self.artifacts_dir / "pca_dataframes.joblib")
            
            try:
                self.feature_columns = joblib.load(self.artifacts_dir / "feature_columns.joblib")
            except Exception:
                self.feature_columns = {}
                
            self.artifacts_loaded = True
            print("--- Artefatti caricati con successo. ---")
            
            if progress_callback:
                progress_callback(100, "Avvio Applicazione...")
            
        except FileNotFoundError as e:
            print(f"ERRORE CRITICO: File artefatto mancante in '{self.artifacts_dir}'. {e}")
            raise
        except Exception as e:
            print(f"ERRORE CRITICO durante il caricamento artefatti: {e}")
            raise

    def _get_style_name(self, ruolo: str, cluster_id: int) -> str:
        """Helper per ottenere il nome dello stile di gioco in modo sicuro."""
        try:
            # Assicura che l'ID sia un intero
            cluster_id = int(cluster_id)
            return self.cluster_names[ruolo][cluster_id]
        except KeyError:
            return f"Cluster {cluster_id}" # Fallback se il nome non è mappato
    
    def _get_cluster_id_from_name(self, ruolo: str, style_name: str) -> int:
        """Helper per ottenere l'ID del cluster dal nome dello stile."""
        try:
            # Cerca il cluster_id corrispondente al nome dello stile
            for cluster_id, name in self.cluster_names[ruolo].items():
                if name == style_name:
                    return int(cluster_id)
            # Se non trovato, restituisce None
            return None
        except KeyError:
            return None
        
    def _find_player(self, search_term: str) -> Tuple[str, Any]:
        """
        Metodo privato per trovare un giocatore nel database.
        Restituisce lo stato, il ruolo, l'ID (Rk/Indice), il nome, il Cluster ID e il Nome Stile.
        """
        self._ensure_artifacts_loaded() # <-- Lazy Load
        
        matches = []
        for ruolo, df in self.pca_dataframes.items():
            if 'Player' not in df.columns or 'Cluster' not in df.columns:
                continue # Salta se il dataframe non è valido
                
            # Cerca il termine nel nome del giocatore (ignorando spazi bianchi e maiuscole)
            # es. " tammy abraham " -> "tammy abraham"
            search_term_clean = search_term.strip().lower()
            player_names_clean = df['Player'].str.strip().str.lower()
            
            found_df = df[player_names_clean.str.contains(search_term_clean, na=False)]
            
            if not found_df.empty:
                for idx, row in found_df.iterrows(): # idx è l'ID_Univoco (l'indice)
                    cluster_id = int(row['Cluster'])
                    style_name = self._get_style_name(ruolo, cluster_id)
                    
                    matches.append({
                        'ID_Univoco': idx, # <-- Indice Univoco (es. Player_Comp)
                        'Player': row['Player'],
                        'Team': row['Team'],
                        'Age': row['Age'],
                        'Role': ruolo,
                        'ClusterID': cluster_id,
                        'StyleName': style_name 
                    })
        
        if len(matches) == 0:
            return ("ERROR", f"Giocatore '{search_term}' non trovato.")
        
        if len(matches) == 1:
            match = matches[0]
            # Restituisce il payload completo
            return ("FOUND", (match['Role'], match['ID_Univoco'], match['Player'], match['ClusterID'], match['StyleName']))
            
        if len(matches) > 1:
            # Mostra anche lo stile nelle scelte ambigue
            choices_df = pd.DataFrame(matches).set_index('ID_Univoco')
            return ("AMBIGUOUS", choices_df[['Player', 'Team', 'Age', 'Role', 'StyleName']])
            
        return ("ERROR", "Errore di logica imprevisto.")
    
    def _find_player_data_by_id(self, player_id_univoco: str) -> Tuple[str, Any, int, str]:
        """Helper per trovare i dati di un giocatore (ruolo, riga, cluster, stile) tramite ID."""
        self._ensure_artifacts_loaded() # <-- Lazy Load
        for ruolo, df in self.pca_dataframes.items():
            # Controlla se l'ID (indice) è in questo dataframe di ruolo
            if player_id_univoco in df.index:
                player_row = df.loc[player_id_univoco]
                cluster_id = int(player_row['Cluster'])
                style_name = self._get_style_name(ruolo, cluster_id)
                # Restituisce tutto il necessario
                return (ruolo, player_row, cluster_id, style_name)
        
        # Se arriva qui, il giocatore non è stato trovato (non dovrebbe accadere
        # ora che la dropdown è filtrata, ma è una sicurezza)
        raise KeyError(f"Player with ID {player_id_univoco} not found in any PCA dataframe.")
    
    # --- NUOVO METODO DI RICERCA PER L'APP (AGGIUNGI QUESTO) ---
    # SimEngine.py

    def find_similar_players_by_id(self, player_id_univoco: str, k: int = 10) -> Tuple[pd.DataFrame, Any, Dict]:
        """
        Trova giocatori simili e restituisce anche le coordinate PCA del target.
        Returns: (DataFrame_Simili, Nome_Stile, Dict_Coordinate_Target)
        """
        try:
            # 1. Trova i dati del giocatore (incluso il vettore PCA completo)
            # _find_player_data_by_id chiama già _ensure_artifacts_loaded
            ruolo, player_row, cluster_id, style_name = self._find_player_data_by_id(player_id_univoco)
            
            print(f"\n--- Ricerca per ID in corso: {player_id_univoco} ({player_row['Player']}) ---")
            
            # --- MODIFICA CHIAVE: Estrai le coordinate del TARGET ---
            target_coords = {
                'PC1': float(player_row['PC1']),
                'PC2': float(player_row['PC2']),
                'PC3': float(player_row['PC3'])
            }

            # 2. Prepara gli asset
            knn_model = self.knn_models[ruolo][cluster_id]
            df_pca_full = self.pca_dataframes[ruolo]
            df_cluster = df_pca_full[df_pca_full['Cluster'] == cluster_id].copy()
            pc_columns = [col for col in df_cluster.columns if 'PC' in col]
            
            # 3. Estrai il vettore target per il k-NN
            player_vector = player_row[pc_columns].values.reshape(1, -1)

            # 4. Esegui la query k-NN
            dn_samples_in_cluster = len(df_cluster)
            n_neighbors_request = min(k + 1, dn_samples_in_cluster)
            
            distances, indices = knn_model.kneighbors(player_vector, n_neighbors=n_neighbors_request)
            
            # 5. Mappa i risultati
            result_indices_with_self = indices[0]
            result_distances_with_self = distances[0]
            player_ids = df_cluster.index[result_indices_with_self]
            results_df = df_pca_full.loc[player_ids]
            results_df['Similarita (Distanza)'] = result_distances_with_self
            results_df = results_df.sort_values(by='Similarita (Distanza)')
            
            # 6. Escludi il giocatore stesso
            if not results_df.empty and results_df.index[0] == player_id_univoco:
                results_df = results_df.iloc[1:]
            
            top_k_df = results_df.head(k).copy()
            top_k_df['Stile di Gioco'] = top_k_df['Cluster'].apply(
                lambda x: self._get_style_name(ruolo, int(x))
            )
            
            # 7. Formatta output (Includendo PC1, PC2, PC3 per i vicini)
            output_cols = ['Player', 'Ht.', 'Wt.', 'Comp', 'Team', 'Similarita (Distanza)', 'Valore_Mercato', 'PC1', 'PC2', 'PC3']
            final_cols = [col for col in output_cols if col in top_k_df.columns]
            
            final_df = top_k_df[final_cols].reset_index()
            final_df = final_df.rename(columns={'index': 'ID_Univoco'})
            
            # --- MODIFICA: Ritorna anche target_coords ---
            return (final_df, style_name, target_coords)

        except KeyError as e:
            print(f"ERRORE: Dati non trovati per ID '{player_id_univoco}'. Dettagli: {e}")
            return (pd.DataFrame(), None, {})
        except Exception as e:
            print(f"ERRORE imprevisto durante la ricerca k-NN by ID: {e}")
            return (pd.DataFrame(), None, {})


    def find_similar_by_identikit(self, role: str, feature_dict: Dict[str, Any], k: int = 10, requested_cluster_id: int = None) -> Tuple[pd.DataFrame, str, Dict]:
        """
        Costruisce un vettore target a partire da un dizionario di feature (identikit),
        applica One-Hot encoding (se presenti gli encoders), scala, proietta con PCA,
        individua il cluster tramite KMeans e interroga il k-NN dedicato al cluster.
        
        Se requested_cluster_id è specificato, cerca SOLO in quel cluster invece di usare KMeans.

        Restituisce: (final_df, style_name, target_coords)
        """
        self._ensure_artifacts_loaded() # <-- Lazy Load
        try:
            ruolo = role
            if ruolo not in self.pcas or ruolo not in self.scalers:
                print(f"ERRORE: Ruolo '{ruolo}' non trovato negli artefatti.")
                return (pd.DataFrame(), None, {})

            # Recupera le colonne di feature nell'ordine usato in training
            feature_cols = self.feature_columns.get(ruolo)
            if not feature_cols:
                print(f"ERRORE: Feature columns non disponibili per ruolo {ruolo}.")
                return (pd.DataFrame(), None, {})

            # Calcola le medie delle features per questo ruolo dal dataset originale
            import numpy as np # type: ignore
            df_pca_full = self.pca_dataframes[ruolo]
            
            # Estrai solo le colonne feature numeriche dal dataset
            available_features = [col for col in feature_cols if col in df_pca_full.columns]
            feature_means = df_pca_full[available_features].mean().to_dict()
            
            # Costruisci un DataFrame single-row con le medie come baseline
            input_row = pd.DataFrame([feature_means], columns=available_features)
            
            # Aggiungi eventuali colonne mancanti con 0
            for col in feature_cols:
                if col not in input_row.columns:
                    input_row[col] = 0.0
            
            # Riordina le colonne come in training
            input_row = input_row[feature_cols]

            # Sovrascrivi SOLO le colonne con valori > 0 da feature_dict
            # Questo permette di specificare solo le features desiderate senza "inquinare" con zeri
            for kf, kv in feature_dict.items():
                if kf in input_row.columns:
                    try:
                        val = float(kv)
                        if val > 0:  # Include solo valori positivi
                            input_row.at[0, kf] = val
                            print(f"   Feature '{kf}' impostata a {val}")
                    except Exception:
                        pass  # Ignora valori non numerici

            # NOTA: Nation, Team, Comp NON sono più usati nel training
            # Sono solo metadati per filtraggio POST-ricerca nell'UI
            # Il modello si basa ESCLUSIVAMENTE su caratteristiche di gioco

            # Ora applichiamo scaler -> pca
            scaler = self.scalers[ruolo]
            pca = self.pcas[ruolo]

            # Assicura l'ordine delle colonne come in training
            X_scaled = scaler.transform(input_row[feature_cols].values)
            X_pca = pca.transform(X_scaled)

            # Costruisci target_coords
            target_coords = {}
            if X_pca.shape[1] >= 1:
                target_coords['PC1'] = float(X_pca[0, 0])
            if X_pca.shape[1] >= 2:
                target_coords['PC2'] = float(X_pca[0, 1])
            if X_pca.shape[1] >= 3:
                target_coords['PC3'] = float(X_pca[0, 2])

            # Determina il cluster da utilizzare
            if requested_cluster_id is not None:
                # Usa il cluster specificato dall'utente
                cluster_id = int(requested_cluster_id)
                print(f"--- Cluster SPECIFICATO dall'utente: {cluster_id} ---")
            else:
                # Individua cluster usando KMeans
                kmeans = self.kmeans_models.get(ruolo)
                if kmeans is None:
                    print(f"ERRORE: KMeans non trovato per ruolo {ruolo}.")
                    return (pd.DataFrame(), None, target_coords)
                # KMeans si aspetta lo stesso spazio PCA
                cluster_id = int(kmeans.predict(X_pca)[0])
                print(f"--- Cluster PREDETTO da KMeans: {cluster_id} ---")
            
            style_name = self._get_style_name(ruolo, cluster_id)

            # Recupera il dataframe del cluster e il modello k-NN
            df_pca_full = self.pca_dataframes[ruolo]
            df_cluster = df_pca_full[df_pca_full['Cluster'] == cluster_id].copy()
            pc_columns = [col for col in df_cluster.columns if 'PC' in col]

            if df_cluster.empty:
                print(f"ERRORE: Nessun giocatore nel cluster {cluster_id} per ruolo {ruolo}.")
                return (pd.DataFrame(), style_name, target_coords)

            knn_model = self.knn_models.get(ruolo, {}).get(cluster_id)
            if knn_model is None:
                print(f"ERRORE: k-NN non trovato per ruolo {ruolo} cluster {cluster_id}.")
                return (pd.DataFrame(), style_name, target_coords)

            # Prepara il vettore target nello spazio PCA (attenzione alle dimensioni)
            # Se PCA ha più componenti, utilizziamo tutte per la query
            player_vector = X_pca.reshape(1, -1)

            # Determina n_neighbors richiesto (rispetta il massimo del modello)
            available = len(df_cluster)
            n_neighbors_request = min(k + 1, available)
            distances, indices = knn_model.kneighbors(player_vector, n_neighbors_request)

            result_indices_with_self = indices[0]
            result_distances_with_self = distances[0]
            player_ids = df_cluster.index[result_indices_with_self]
            results_df = df_pca_full.loc[player_ids].copy()
            results_df['Similarita (Distanza)'] = result_distances_with_self
            results_df = results_df.sort_values(by='Similarita (Distanza)')

            # Escludi eventuale entry identica (non presente perché ghost non è nel DF)
            top_k_df = results_df.head(k).copy()
            top_k_df['Stile di Gioco'] = top_k_df['Cluster'].apply(lambda x: self._get_style_name(ruolo, int(x)))

            output_cols = ['Player', 'Ht.', 'Wt.', 'Comp', 'Team', 'Similarita (Distanza)', 'Valore_Mercato', 'PC1', 'PC2', 'PC3']
            final_cols = [col for col in output_cols if col in top_k_df.columns]
            final_df = top_k_df[final_cols].reset_index()
            final_df = final_df.rename(columns={'index': 'ID_Univoco'})

            return (final_df, style_name, target_coords)

        except Exception as e:
            print(f"ERRORE imprevisto in find_similar_by_identikit: {e}")
            return (pd.DataFrame(), None, {})

    def find_similar_by_identikit_all_clusters(self, role: str, feature_dict: Dict[str, Any], k: int = 10) -> Tuple[pd.DataFrame, str, Dict]:
        """
        Cerca giocatori simili tra TUTTI i cluster di un ruolo specifico.
        Combina i risultati di tutti i cluster del ruolo e restituisce i top k più simili.
        
        Restituisce: (final_df, style_name, target_coords)
        """
        self._ensure_artifacts_loaded() # <-- Lazy Load
        try:
            ruolo = role
            if ruolo not in self.pcas or ruolo not in self.scalers:
                print(f"ERRORE: Ruolo '{ruolo}' non trovato negli artefatti.")
                return (pd.DataFrame(), None, {})

            # Recupera le colonne di feature nell'ordine usato in training
            feature_cols = self.feature_columns.get(ruolo)
            if not feature_cols:
                print(f"ERRORE: Feature columns non disponibili per ruolo {ruolo}.")
                return (pd.DataFrame(), None, {})

            # Calcola le medie delle features per questo ruolo dal dataset originale
            import numpy as np # type: ignore
            df_pca_full = self.pca_dataframes[ruolo]
            
            # Estrai solo le colonne feature numeriche dal dataset
            available_features = [col for col in feature_cols if col in df_pca_full.columns]
            feature_means = df_pca_full[available_features].mean().to_dict()
            
            # Costruisci un DataFrame single-row con le medie come baseline
            input_row = pd.DataFrame([feature_means], columns=available_features)
            
            # Aggiungi eventuali colonne mancanti con 0
            for col in feature_cols:
                if col not in input_row.columns:
                    input_row[col] = 0.0
            
            # Riordina le colonne come in training
            input_row = input_row[feature_cols]

            # Sovrascrivi SOLO le colonne con valori > 0 da feature_dict
            # Questo permette di specificare solo le features desiderate senza "inquinare" con zeri
            for kf, kv in feature_dict.items():
                if kf in input_row.columns:
                    try:
                        val = float(kv)
                        if val > 0:  # Include solo valori positivi
                            input_row.at[0, kf] = val
                            print(f"   Feature '{kf}' impostata a {val}")
                    except Exception:
                        pass  # Ignora valori non numerici

            # NOTA: Nation, Team, Comp NON sono più usati nel training
            # Sono solo metadati per filtraggio POST-ricerca nell'UI
            # Il modello si basa ESCLUSIVAMENTE su caratteristiche di gioco

            # Ora applichiamo scaler -> pca
            scaler = self.scalers[ruolo]
            pca = self.pcas[ruolo]

            # Assicura l'ordine delle colonne come in training
            X_scaled = scaler.transform(input_row[feature_cols].values)
            X_pca = pca.transform(X_scaled)

            # Costruisci target_coords
            target_coords = {}
            if X_pca.shape[1] >= 1:
                target_coords['PC1'] = float(X_pca[0, 0])
            if X_pca.shape[1] >= 2:
                target_coords['PC2'] = float(X_pca[0, 1])
            if X_pca.shape[1] >= 3:
                target_coords['PC3'] = float(X_pca[0, 2])
            
            # Ottieni tutti i cluster disponibili per questo ruolo
            df_pca_full = self.pca_dataframes[ruolo]
            available_clusters = df_pca_full['Cluster'].unique()
            
            all_results = []
            
            # Itera su tutti i cluster del ruolo
            for cluster_id in available_clusters:
                df_cluster = df_pca_full[df_pca_full['Cluster'] == cluster_id].copy()
                
                if df_cluster.empty:
                    continue
                
                knn_model = self.knn_models.get(ruolo, {}).get(int(cluster_id))
                if knn_model is None:
                    continue
                
                # Esegui la query k-NN per questo cluster
                player_vector = X_pca.reshape(1, -1)
                available = len(df_cluster)
                n_neighbors_request = min(k * 2, available)  # Richiedi più risultati per ogni cluster
                distances, indices = knn_model.kneighbors(player_vector, n_neighbors_request)
                
                result_indices = indices[0]
                result_distances = distances[0]
                player_ids = df_cluster.index[result_indices]
                results_df = df_pca_full.loc[player_ids].copy()
                results_df['Similarita (Distanza)'] = result_distances
                results_df['Cluster'] = cluster_id  # Mantieni cluster
                
                all_results.append(results_df)
            
            # Combina tutti i risultati
            if not all_results:
                return (pd.DataFrame(), f"{ruolo} (Tutti i Cluster)", target_coords)
            
            combined_df = pd.concat(all_results, ignore_index=False)
            combined_df = combined_df.sort_values(by='Similarita (Distanza)')
            
            # Prendi i top k risultati globali
            top_k_df = combined_df.head(k).copy()
            top_k_df['Stile di Gioco'] = top_k_df['Cluster'].apply(
                lambda x: self._get_style_name(ruolo, int(x))
            )
            
            output_cols = ['Player', 'Ht.', 'Wt.', 'Comp', 'Team', 'Similarita (Distanza)', 'Valore_Mercato', 'PC1', 'PC2', 'PC3']
            final_cols = [col for col in output_cols if col in top_k_df.columns]
            final_df = top_k_df[final_cols].reset_index()
            final_df = final_df.rename(columns={'index': 'ID_Univoco'})
            
            return (final_df, f"{ruolo} (Tutti i Cluster)", target_coords)
            
        except Exception as e:
            print(f"ERRORE imprevisto in find_similar_by_identikit_all_clusters: {e}")
            return (pd.DataFrame(), None, {})

    def find_similar_by_identikit_all_roles(self, feature_dict: Dict[str, Any], k: int = 10) -> Tuple[pd.DataFrame, str, Dict]:
        """
        Cerca giocatori simili tra TUTTI i ruoli quando non viene specificato un cluster.
        Combina i risultati di tutti i ruoli e restituisce i top k più simili.
        
        Restituisce: (final_df, style_name, target_coords)
        """
        self._ensure_artifacts_loaded() # <-- Lazy Load
        try:
            all_results = []
            
            # Itera su tutti i ruoli disponibili
            for ruolo in self.pca_dataframes.keys():
                if ruolo not in self.pcas or ruolo not in self.scalers:
                    continue
                
                feature_cols = self.feature_columns.get(ruolo)
                if not feature_cols:
                    continue
                
                # Calcola le medie delle features per questo ruolo dal dataset originale
                import numpy as np # type: ignore
                df_pca_full = self.pca_dataframes[ruolo]
                
                # Estrai solo le colonne feature numeriche dal dataset
                available_features = [col for col in feature_cols if col in df_pca_full.columns]
                feature_means = df_pca_full[available_features].mean().to_dict()
                
                # Costruisci un DataFrame single-row con le medie come baseline
                input_row = pd.DataFrame([feature_means], columns=available_features)
                
                # Aggiungi eventuali colonne mancanti con 0
                for col in feature_cols:
                    if col not in input_row.columns:
                        input_row[col] = 0.0
                
                # Riordina le colonne come in training
                input_row = input_row[feature_cols]
                
                # Sovrascrivi SOLO le colonne con valori > 0 da feature_dict
                for kf, kv in feature_dict.items():
                    if kf in input_row.columns:
                        try:
                            val = float(kv)
                            if val > 0:  # Include solo valori positivi
                                input_row.at[0, kf] = val
                        except Exception:
                            pass  # Ignora valori non numerici
                
                # Applica scaler -> pca per questo ruolo
                scaler = self.scalers[ruolo]
                pca = self.pcas[ruolo]
                X_scaled = scaler.transform(input_row[feature_cols].values)
                X_pca = pca.transform(X_scaled)
                
                # Individua cluster usando KMeans
                kmeans = self.kmeans_models.get(ruolo)
                if kmeans is None:
                    continue
                
                cluster_id = int(kmeans.predict(X_pca)[0])
                
                # Recupera il dataframe del cluster e il modello k-NN
                df_pca_full = self.pca_dataframes[ruolo]
                df_cluster = df_pca_full[df_pca_full['Cluster'] == cluster_id].copy()
                
                if df_cluster.empty:
                    continue
                
                knn_model = self.knn_models.get(ruolo, {}).get(cluster_id)
                if knn_model is None:
                    continue
                
                # Esegui la query k-NN per questo ruolo/cluster
                player_vector = X_pca.reshape(1, -1)
                available = len(df_cluster)
                n_neighbors_request = min(k * 2, available)  # Richiedi più risultati per ogni ruolo
                distances, indices = knn_model.kneighbors(player_vector, n_neighbors_request)
                
                result_indices = indices[0]
                result_distances = distances[0]
                player_ids = df_cluster.index[result_indices]
                results_df = df_pca_full.loc[player_ids].copy()
                results_df['Similarita (Distanza)'] = result_distances
                results_df['Role'] = ruolo  # Aggiungi colonna ruolo
                results_df['Cluster'] = cluster_id  # Mantieni cluster
                
                all_results.append(results_df)
            
            # Combina tutti i risultati
            if not all_results:
                return (pd.DataFrame(), "Tutti i Ruoli", {})
            
            combined_df = pd.concat(all_results, ignore_index=False)
            combined_df = combined_df.sort_values(by='Similarita (Distanza)')
            
            # Prendi i top k risultati globali
            top_k_df = combined_df.head(k).copy()
            top_k_df['Stile di Gioco'] = top_k_df.apply(
                lambda row: self._get_style_name(row['Role'], int(row['Cluster'])), axis=1
            )
            
            # Calcola coordinate medie come target_coords (rappresentativo)
            target_coords = {}
            if 'PC1' in top_k_df.columns and len(top_k_df) > 0:
                target_coords['PC1'] = float(top_k_df['PC1'].mean())
            if 'PC2' in top_k_df.columns and len(top_k_df) > 0:
                target_coords['PC2'] = float(top_k_df['PC2'].mean())
            if 'PC3' in top_k_df.columns and len(top_k_df) > 0:
                target_coords['PC3'] = float(top_k_df['PC3'].mean())
            
            output_cols = ['Player', 'Ht.', 'Wt.', 'Comp', 'Team', 'Similarita (Distanza)', 'Valore_Mercato', 'PC1', 'PC2', 'PC3', 'Role']
            final_cols = [col for col in output_cols if col in top_k_df.columns]
            final_df = top_k_df[final_cols].reset_index()
            final_df = final_df.rename(columns={'index': 'ID_Univoco'})
            
            return (final_df, "Tutti i Ruoli", target_coords)
            
        except Exception as e:
            print(f"ERRORE imprevisto in find_similar_by_identikit_all_roles: {e}")
            return (pd.DataFrame(), None, {})


    # SimEngine.py

    def find_similar_players(self, search_term: str, k: int = 10) -> Tuple[pd.DataFrame, Any]: # <-- Modificato tipo di Ritorno
        """
        Il motore di similarità.
        Cerca un giocatore, identifica il suo stile di gioco, e trova i k vicini 
        SOLO all'interno di quello stile.
        
        MODIFICATO: Restituisce (DataFrame_Risultati, Stile_Giocatore_Cercato)
        """
        
        # 1. Trova il giocatore e il suo stile
        status, payload = self._find_player(search_term)
        
        if status == "ERROR":
            print(payload)
            return (pd.DataFrame(), None) # <-- MODIFICATO
        
        if status == "AMBIGUOUS":
            print(f"--- Ricerca Ambigua ---")
            print(f"Il termine '{search_term}' corrisponde a {len(payload)} giocatori:")
            print(payload)
            print("\nEsegui una nuova ricerca con un nome più specifico.")
            return (payload, None) # <-- MODIFICATO
            
        # Caso 1 (Trovato)
        if status == "FOUND":
            player_role, player_id, player_name, player_cluster, player_style = payload
            
            print(f"\n--- Ricerca in corso per: {player_name} (Trovato) ---")
            print(f"   -> Ruolo: {player_role}")
            print(f"   -> Stile di Gioco: {player_style} (Cluster {player_cluster})")
            
            try:
                # ... (Logica k-NN invariata) ...
                
                # 2. Prepara gli asset specifici per il cluster
                knn_model = self.knn_models[player_role][player_cluster]
                df_pca_full = self.pca_dataframes[player_role]
                df_cluster = df_pca_full[df_pca_full['Cluster'] == player_cluster].copy()
                pc_columns = [col for col in df_cluster.columns if 'PC' in col]
                
                # 3. Estrai il vettore target
                player_data = df_cluster.loc[player_id]
                player_vector = player_data[pc_columns].values.reshape(1, -1)

                # 4. Esegui la query k-NN
                distances, indices = knn_model.kneighbors(player_vector)
                
                # 5. Mappa i risultati
                result_indices_with_self = indices[0]
                result_distances_with_self = distances[0]
                player_ids = df_cluster.index[result_indices_with_self]
                results_df = df_pca_full.loc[player_ids]
                results_df['Similarita (Distanza)'] = result_distances_with_self
                results_df = results_df.sort_values(by='Similarita (Distanza)')
                
                # 6. Escludi il giocatore stesso e prendi i top k
                if not results_df.empty and results_df.index[0] == player_id:
                    results_df = results_df.iloc[1:]
                top_k_df = results_df.head(k).copy()
                top_k_df['Stile di Gioco'] = top_k_df['Cluster'].apply(
                    lambda x: self._get_style_name(player_role, int(x))
                )
                
                # ... (Creazione final_df invariata) ...
                output_cols = ['Player', 'Ht.', 'Wt.', 'Comp', 'Team', 'Similarita (Distanza)', 'Valore_Mercato']
                final_cols = [col for col in output_cols if col in top_k_df.columns]
                final_df = top_k_df[final_cols].reset_index()
                final_df = final_df.rename(columns={'index': 'ID_Univoco'})
                
                # --- MODIFICA CHIAVE ---
                # Restituisci sia i risultati CHE lo stile del giocatore cercato
                return (final_df, player_style)

            except KeyError:
                print(f"ERRORE: Modello k-NN o dati PCA non trovati per il ruolo '{player_role}' e cluster '{player_cluster}'.")
                return (pd.DataFrame(), None) # <-- MODIFICATO
            except Exception as e:
                print(f"ERRORE imprevisto durante la ricerca k-NN: {e}")
                return (pd.DataFrame(), None) # <-- MODIFICATO

            except KeyError:
                print(f"ERRORE: Modello k-NN o dati PCA non trovati per il ruolo '{player_role}' e cluster '{player_cluster}'.")
                return pd.DataFrame()
            except Exception as e:
                print(f"ERRORE imprevisto durante la ricerca k-NN: {e}")
                return pd.DataFrame()

# --- BLOCCO DI TEST PER IL MOTORE ---
if __name__ == "__main__":
    
    # Imposta pandas per una stampa migliore
    pd.set_option('display.max_rows', 10)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)

    print("--- Test Esecuzione similarity_engine.py (QUERY FINALE CON CLUSTER) ---")
    
    try:
        # 1. Inizializza il motore (carica i file da "artifacts")
        engine = SimilarityEngine(artifacts_dir="artifacts")
        
        # --- TEST 1: Ricerca Specifica (Sostituisci con un nome reale) ---
        print("\n" + "="*30 + " TEST 1 (Attaccante) " + "="*30)
        target_player_1 = "Mohamed Salah" # <<< MODIFICA QUI
        
        similar_players_1, role_1 = engine.find_similar_players(target_player_1, k=10)
        
        if not similar_players_1.empty:
            print(f"\nRisultati per {target_player_1}:")
            print(similar_players_1)
        
        # --- TEST 2: Ricerca Specifica (Sostituisci con un nome reale) ---
        print("\n" + "="*30 + " TEST 2 (Centrocampista) " + "="*30)
        target_player_2 = "Rodri" # <<< MODIFICA QUI
        
        similar_players_2, role_2 = engine.find_similar_players(target_player_2, k=10)
        
        if not similar_players_2.empty:
            print(f"\nRisultati per {target_player_2}:")
            print(similar_players_2)

    except Exception as e:
        print(f"ERRORE: Impossibile eseguire la ricerca. Dettagli: {e}")