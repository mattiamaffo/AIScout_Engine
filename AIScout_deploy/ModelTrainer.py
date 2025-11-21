import pandas as pd # type: ignore
import numpy as np # type: ignore
from sklearn.preprocessing import StandardScaler, OneHotEncoder # type: ignore
from sklearn.decomposition import PCA # type: ignore
from sklearn.neighbors import NearestNeighbors # type: ignore
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt # type: ignore
import joblib # type: ignore
import os
import sys
from pathlib import Path
from sklearn.cluster import KMeans # type: ignore

# --- Configurazione Percorsi ---
BASE_DIR = Path(__file__).resolve().parent

# --- Importazioni dal Progetto ---
import config
from PlayerDataPreprocessor import PlayerDataPreprocessor


class ModelTrainer:
    """
    Gestisce l'intero flusso di addestramento del modello di similarità,
    inclusi Scaling, PCA e k-NN per ogni ruolo.
    """
    
    def __init__(self, dataframes_x90: Dict[str, pd.DataFrame], metadata_cols: List[str], optimal_k: Dict[str, int]):
        """
        Inizializza il trainer con i dati x90 pronti.
        
        :param dataframes_x90: Dizionario di DataFrame (uno per ruolo) post-pulizia e x90.
        :param metadata_cols: Lista di colonne da non includere nello scaling/PCA (da config).
        """
        self.dataframes_x90 = dataframes_x90
        # Definiamo i metadati da escludere (Rk è l'indice, quindi non è nelle colonne)
        self.metadata_to_exclude = [col for col in metadata_cols if col != 'Rk']
        
        # Attributi per salvare i risultati del training
        self.scaled_dataframes = {}
        self.scalers = {}

        self.optimal_k = optimal_k
        
        # Attributi futuri per PCA e k-NN
        self.pca_dataframes = {}
        self.pcas = {}
        self.knn_models = {}

        # One-Hot Encoders per ruolo (per Nation, Team, Comp)
        self.ohe_encoders = {}
        # Lista ordinata delle colonne finali delle feature per ogni ruolo
        self.feature_columns = {}

        # Attributi futuri per il clustering
        self.kmeans_models = {}

    def _scale_features(self):
        """
        [Metodo Privato] Applica lo Standard Scaling ai dati x90 numerici 
        e salva i DataFrame scalati e gli oggetti Scaler.
        """
        print("\n--- Esecuzione Standard Scaling per Ruolo ---")
        
        for ruolo, df_x90 in self.dataframes_x90.items():
            if df_x90.empty:
                print(f"   -> DataFrame {ruolo} vuoto, skipping scaling.")
                continue
            
            df = df_x90.copy()
            
            # 1. PRESERVA Nation, Team, Comp come SOLO metadati (non usati nel training)
            # STRATEGIA: La similarità sarà basata SOLO su caratteristiche di gioco
            # L'utente può filtrare i risultati per Nation/Comp DOPO la ricerca nell'UI
            categorical_metadata = ['Nation', 'Team', 'Comp']
            cat_metadata_cols = [c for c in categorical_metadata if c in df.columns]
            cat_metadata = df[cat_metadata_cols].copy() if cat_metadata_cols else pd.DataFrame()
            
            # Non facciamo più One-Hot Encoding per nessuna variabile categorica
            # Questo elimina completamente il bias geografico/di campionato
            ohe_info = {}  # Vuoto - nessun encoder necessario
            
            # 2. Identifica le colonne numeriche da scalare (ora includono le OHE appena create)
            feature_cols = [
                col for col in df.columns 
                if col not in self.metadata_to_exclude and col not in ['Ruolo_Primario', '90s']
            ]
            
            scaler = StandardScaler()
            
            if not feature_cols:
                print(f"   -> Attenzione: Nessuna colonna di feature trovata da scalare per {ruolo}.")
                self.scaled_dataframes[ruolo] = df
                self.scalers[ruolo] = scaler
                # salva comunque encoders e feature column info
                if ohe_info:
                    self.ohe_encoders[ruolo] = ohe_info
                self.feature_columns[ruolo] = []
                continue

            try:
                # 3. Addestra lo Scaler e Trasforma i dati
                X_scaled = scaler.fit_transform(df[feature_cols].values)
            except ValueError:
                print(f"   -> Errore {ruolo}: Dati non numerici. Tento coercizione forzata...")
                df[feature_cols] = df[feature_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
                X_scaled = scaler.fit_transform(df[feature_cols].values)

            # 4. Ricrea il DataFrame Scalato
            df_scaled_features = pd.DataFrame(X_scaled, columns=feature_cols, index=df.index)
            
            # 5. Riunisce le colonne Metadati (incluso Team, Nation, Comp originali)
            # Identifica i metadati esistenti nel dataframe
            existing_metadata_cols = [col for col in df.columns if col not in feature_cols]
            metadata_df = df[existing_metadata_cols].copy() if existing_metadata_cols else pd.DataFrame(index=df.index)
            
            # Aggiungi i metadati categorici preservati (se non già presenti)
            if not cat_metadata.empty:
                for col in cat_metadata.columns:
                    if col not in metadata_df.columns:
                        metadata_df[col] = cat_metadata[col]
            
            df_scaled = pd.concat([metadata_df, df_scaled_features], axis=1)
            
            # 6. Salva i risultati negli attributi della classe
            self.scaled_dataframes[ruolo] = df_scaled
            self.scalers[ruolo] = scaler
            # Salva anche gli encoders e la lista ordinata di colonne feature
            if ohe_info:
                self.ohe_encoders[ruolo] = ohe_info

            self.feature_columns[ruolo] = feature_cols
            print(f"   -> Scaling per {ruolo} completato. Scaler salvato.")

    def _apply_pca(self):
        """
        [Metodo Privato] Applica la PCA ai dati scalati.
        Utilizza n_components=0.95 per mantenere il 95% della varianza.
        """
        print("\n---Applicazione PCA (Principal Component Analysis) ---")
        
        for ruolo, df_scaled in self.scaled_dataframes.items():
            if df_scaled.empty:
                print(f"   -> DataFrame {ruolo} vuoto, skipping PCA.")
                continue
            
            # 1. Isola nuovamente le feature scalate
            feature_cols = [
                col for col in df_scaled.columns 
                if col not in self.metadata_to_exclude and col not in ['Ruolo_Primario', '90s']
            ]
            
            if not feature_cols:
                print(f"   -> Nessuna feature da processare per PCA in {ruolo}.")
                continue
            
            X_scaled_data = df_scaled[feature_cols].values
            
            # 2. Inizializza PCA per mantenere il 95% della varianza
            pca = PCA(n_components=0.95)
            
            # 3. Addestra la PCA e trasforma i dati
            X_pca = pca.fit_transform(X_scaled_data)
            
            # 4. Salva l'oggetto PCA addestrato (fondamentale per le query future)
            self.pcas[ruolo] = pca
            
            # 5. Crea il nuovo DataFrame PCA
            pc_columns = [f'PC{i+1}' for i in range(X_pca.shape[1])]
            df_pca_features = pd.DataFrame(X_pca, columns=pc_columns, index=df_scaled.index)
            
            # 6. Riunisce i metadati
            metadata_df = df_scaled.drop(columns=feature_cols)
            df_pca_final = pd.concat([metadata_df, df_pca_features], axis=1)
            
            # 7. Salva il DataFrame finale
            self.pca_dataframes[ruolo] = df_pca_final
            
            print(f"   -> PCA per {ruolo} completata.")
            print(f"      Varianza mantenuta: {pca.explained_variance_ratio_.sum()*100:.2f}%")
            print(f"      Dimensioni originali: {len(feature_cols)}, Dimensioni ridotte: {pca.n_components_}")

    def _fit_clusters(self):
        """
        Addestra i modelli K-Means usando i 'k' ottimali da config.
        Aggiunge l'etichetta 'Cluster' ai DataFrame PCA.
        """
        print("\n--- Addestramento Clustering (K-Means) ---")
        for ruolo, df_pca in self.pca_dataframes.items():
            if df_pca.empty: continue
            
            k = self.optimal_k.get(ruolo)
            if not k:
                print(f"   -> Attenzione: k ottimale non trovato per {ruolo}. Skipping clustering.")
                continue
                
            pc_columns = [col for col in df_pca.columns if 'PC' in col]
            if not pc_columns: continue
            
            X_pca_data = df_pca[pc_columns].values
            
            # Inizializza e addestra K-Means
            kmeans = KMeans(n_clusters=k, init='k-means++', n_init=10, random_state=42)
            kmeans.fit(X_pca_data)
            
            # Salva il modello K-Means
            self.kmeans_models[ruolo] = kmeans
            
            # Aggiunge l'etichetta del cluster al DataFrame PCA (FONDAMENTALE)
            self.pca_dataframes[ruolo]['Cluster'] = kmeans.labels_
            
            print(f"   -> Clustering K-Means per {ruolo} completato (k={k}). Colonna 'Cluster' aggiunta.")
        
    def _fit_knn(self):
        """
        Modificato: Addestra un modello k-NN per OGNI CLUSTER in ogni ruolo.
        """
        print("\n--- Addestramento k-NN (per Cluster) ---")
        
        for ruolo, df_pca in self.pca_dataframes.items():
            if df_pca.empty: continue
            
            if 'Cluster' not in df_pca.columns:
                print(f"   -> Attenzione: Nessun cluster trovato per {ruolo}. Skipping k-NN.")
                continue
            
            # Inizializza il dizionario annidato per il ruolo
            self.knn_models[ruolo] = {}
            
            # Itera su ogni cluster trovato in quel ruolo
            for cluster_id in sorted(df_pca['Cluster'].unique()):
                
                # Filtra i dati solo per questo cluster
                cluster_df = df_pca[df_pca['Cluster'] == cluster_id]
                
                pc_columns = [col for col in cluster_df.columns if 'PC' in col]
                X_cluster_data = cluster_df[pc_columns].values
                
                # Controlla se ci sono abbastanza giocatori nel cluster per il k-NN
                # Chiediamo k=10, quindi k+1=11. 
                # Se ci sono meno di 11 giocatori, k deve essere il num di giocatori.
                n_players_in_cluster = X_cluster_data.shape[0]
                
                if n_players_in_cluster <= 1:
                    print(f"   -> Skipping {ruolo} - Cluster {cluster_id} (troppo pochi giocatori)")
                    continue

                # k per k-NN non può essere più grande del numero di campioni
                k_neighbors = min(11, n_players_in_cluster) # 11 = 10 vicini + 1 sé stesso
                
                knn = NearestNeighbors(n_neighbors=k_neighbors, metric='cosine')
                knn.fit(X_cluster_data)
                
                # Salva il modello nel dizionario annidato
                self.knn_models[ruolo][cluster_id] = knn
                
            print(f"   -> {len(self.knn_models[ruolo])} modelli k-NN (uno per cluster) addestrati per {ruolo}.")

    def analyze_cluster_inertia(self, roles_to_analyze: List[str], max_k: int = 10, plot_output_dir: str = "plots"):
        """
        Esegue l'analisi "Elbow Method" per i ruoli specificati 
        e mostra i grafici per aiutare a scegliere il 'k' ottimale.
        """
        print("\n" + "="*50)
        print("--- Analisi Cluster (Elbow Method) ---")
        print("="*50)
        
        k_range = range(2, max_k + 1)
        
        for ruolo in roles_to_analyze:
            if ruolo not in self.pca_dataframes or self.pca_dataframes[ruolo].empty:
                print(f"   -> Skipping {ruolo} (dati non disponibili)")
                continue
                
            df_pca = self.pca_dataframes[ruolo]
            pc_columns = [col for col in df_pca.columns if 'PC' in col]
            
            if not pc_columns:
                print(f"   -> Skipping {ruolo} (nessuna componente PCA trovata)")
                continue
                
            X_data = df_pca[pc_columns].values
            inertia_values = []
            
            print(f"   -> Calcolo inerzia per {ruolo} (k=2 a {max_k})...")
            
            for k in k_range:
                # Inizializza, addestra e calcola l'inerzia
                kmeans = KMeans(n_clusters=k, init='k-means++', n_init=10, random_state=42)
                kmeans.fit(X_data)
                inertia_values.append(kmeans.inertia_)
                
            # Chiama la funzione esterna per plottare
            plot_elbow_method(inertia_values, k_range, ruolo, plot_output_dir)
        
        print("\n--- Analisi Elbow completata. Osserva i grafici per scegliere il 'k' ottimale. ---")        

    def train(self):
        """
        Esegue l'intero flusso di addestramento: 
        Scaling -> PCA -> Clustering -> k-NN per Cluster.
        """
        self._scale_features()
        self._apply_pca()
        self._fit_clusters()
        self._fit_knn()      
        
        print("\n--- Addestramento Modello (con Cluster) Completato. ---")
    
    def save_artifacts(self, output_dir="artifacts"):
        """
        Salva tutti gli oggetti addestrati (Scalers, PCAs, k-NNs) 
        e i DataFrame PCA su disco.
        """
        print(f"\n--- Salvataggio artefatti in '{output_dir}' ---")
        # Converte in Path per uniformità
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        joblib.dump(self.scalers, output_path / "scalers.joblib")
        joblib.dump(self.pcas, output_path / "pcas.joblib")
        joblib.dump(self.kmeans_models, output_path / "kmeans_models.joblib") # <-- Salva K-Means
        joblib.dump(self.knn_models, output_path / "knn_models.joblib") # <-- Salva i k-NN annidati
        # Salva i One-Hot Encoders (se presenti) e la lista delle colonne di feature per ruolo
        joblib.dump(self.ohe_encoders, output_path / "ohe_encoders.joblib")
        joblib.dump(self.feature_columns, output_path / "feature_columns.joblib")
        
        # Salva i dati PCA (che ora includono la colonna 'Cluster')
        joblib.dump(self.pca_dataframes, output_path / "pca_dataframes.joblib")
        
        print(f"   -> Artefatti salvati con successo in '{output_dir}'.")
        
    # --- Metodi Getter ---
    def get_scaled_data(self):
        return self.scaled_dataframes
        
    def get_scalers(self):
        return self.scalers
    
    def get_pca_data(self):
        return self.pca_dataframes
        
    def get_pcas(self):
        return self.pcas
        
    def get_knn_models(self):
        """Restituisce i modelli k-NN addestrati per ogni ruolo."""
        return self.knn_models

def plot_pca_space(df_pca: pd.DataFrame, ruolo: str, num_players_to_label: int = 15):
    """
    Crea uno scatter plot delle prime due componenti principali (PC1 vs PC2)
    e etichetta un campione di giocatori.
    """
    if df_pca is None or df_pca.empty or 'PC1' not in df_pca.columns or 'PC2' not in df_pca.columns:
        print(f"\nImpossibile visualizzare lo spazio PCA per {ruolo}: dati insufficienti o assenti.")
        return
        
    print(f"\n--- Visualizzazione Spazio PCA (PC1 vs PC2) per {ruolo} ---")

    
    plt.figure(figsize=(14, 10))
    
    # Scatter plot di tutti i giocatori
    plt.scatter(df_pca['PC1'], df_pca['PC2'], alpha=0.5, label='Giocatori')
    
    # Etichetta un campione casuale di giocatori per evitare sovrapposizioni
    if 'Player' in df_pca.columns:
        df_sample = df_pca.sample(n=min(num_players_to_label, len(df_pca)))
        for i, row in df_sample.iterrows():
            plt.text(row['PC1'], row['PC2'], row['Player'], fontsize=9, ha='center')
            
    plt.title(f'Spazio Vettoriale PCA (PC1 vs PC2) - {ruolo}')
    plt.xlabel('Principal Component 1 (PC1)')
    plt.ylabel('Principal Component 2 (PC2)')
    plt.grid(True)
    plt.legend()
    plt.show()

def plot_elbow_method(inertia_values: List[float], k_range: range, ruolo: str, output_dir: str = "plots"):
    """
    Crea e SALVA un grafico "Elbow" (a gomito) per l'inerzia K-Means.
    """
    plt.figure(figsize=(10, 6))
    plt.plot(k_range, inertia_values, 'bo-') 
    plt.xlabel('Numero di Cluster (k)')
    plt.ylabel('Inerzia (Somma delle distanze quadratiche)')
    plt.title(f'Analisi Elbow Method per Ruolo: {ruolo}')
    plt.grid(True)
    plt.xticks(list(k_range)) 
    
    # Assicura che la directory esista
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Definisci il nome del file
    save_path = output_path / f"elbow_plot_{ruolo}.png"
    
    # Salva il file
    plt.savefig(save_path)
    
    # Chiudi il plot per liberare memoria
    plt.close()
    
    print(f"   -> Grafico Elbow per {ruolo} salvato in: {save_path}")
    # Rimuovi plt.show()
    # plt.show()


# Alla fine di ModelTrainer.py

if __name__ == "__main__":
    
    print("--- ESECUZIONE: ADDESTRAMENTO FINALE (con nuovi 'k') ---")
    
    # 1. Carica i dati (usando PlayerDataPreprocessor)
    processor = PlayerDataPreprocessor(
            master_file_path=config.MASTER_CSV_PATH_FINAL, 
            min_minutes=config.MIN_MINUTES,
            ruoli=config.RUOLI,
            metadata_cols=config.METADATA_COLS,
            role_features=config.ROLE_FEATURES,
            percentage_cols=config.PERCENTAGE_COLS,
            filter_col=config.FILTER_COL
        )
    dataframes_x90 = processor.prepare_data()
    
    # 2. Addestra il modello (usando i k da config.OPTIMAL_K)
    trainer = ModelTrainer(
        dataframes_x90, 
        config.METADATA_COLS, 
        config.OPTIMAL_K 
    )
    trainer.train() # Esegue Scaling -> PCA -> Clustering -> k-NN per-cluster
    
    # 3. Salva i nuovi artefatti
    trainer.save_artifacts("artifacts")
    
    print("\n--- Addestramento e salvataggio (con cluster) completati. ---")
    print("--- Ora esegui 'cluster_analyzer.py' per profilare i nuovi cluster. ---")