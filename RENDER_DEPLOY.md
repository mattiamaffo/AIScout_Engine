# Deploy su Render.com - Guida

## Modifiche Apportate

Sono stati corretti i path per funzionare correttamente su Render.com:

### Path Unificati

- **Prima**: Il codice usava logiche diverse per ambiente sviluppo vs produzione (`sys.frozen`, `sys._MEIPASS`)
- **Dopo**: Tutti i file usano path relativi consistenti basati su `Path(__file__).resolve().parent`

### File Modificati

1. `app.py` - Semplificato path per `FULL_DATASET_PATH`
2. `data.py` - Rimossa logica frozen/exe, path relativi unificati
3. `config.py` - Path relativi consistenti
4. `SimEngine.py` - Rimossa funzione `get_base_path()`
5. `PlayerDataPreprocessor.py` - Rimossa funzione `get_base_path()`
6. `ModelTrainer.py` - Rimossa funzione `get_base_path()`

## Struttura Cartelle su Render

```
/opt/render/project/
├── app.py
├── data.py
├── config.py
├── SimEngine.py
├── layout.py
├── ModelTrainer.py
├── PlayerDataPreprocessor.py
├── requirements.txt
├── Procfile
├── data/
│   ├── dataset_master_unified_2526.parquet  ← File principale
│   └── dataset_master_unified_2526.csv
└── artifacts/
    ├── database_df_cache.joblib
    ├── feature_columns.joblib
    ├── feature_stats.json
    ├── kmeans_models.joblib
    ├── knn_models.joblib
    ├── ohe_encoders.joblib
    ├── pca_dataframes.joblib
    ├── pcas.joblib
    └── scalers.joblib
```

## Verifica Deploy

### 1. Controlla i Log su Render

Cerca questi messaggi di successo:

```
--- Avvio Caricamento Dati Sincrono ---
[5%] Avvio caricamento dati...
[10%] Caricamento modelli PCA...
[20%] Caricamento Database Giocatori...
[30%] Lettura file Parquet (potrebbe richiedere tempo)...
--- DATABASE_DF caricato dalla cache! ---
--- Inizializzazione SimilarityEngine ---
--- Motore di Similarità Caricato ---
```

### 2. Errori Comuni

#### Errore: File dataset non trovato

```
ERRORE: File dataset non trovato in: /opt/render/project/data/dataset_master_unified_2526.parquet
```

**Soluzione**: Assicurati che il file `.parquet` sia presente nella repository e committato correttamente:

```bash
git add data/dataset_master_unified_2526.parquet
git commit -m "Aggiunto dataset parquet"
git push
```

#### Errore: Permission denied

Se Render non può creare la cache:

- È normale, l'app creerà la cache in memoria
- Il caricamento potrebbe essere leggermente più lento

### 3. Test dell'Applicazione

Dopo il deploy, testa:

1. Apertura homepage ✓
2. Tab "Cerca Giocatore" - ricerca funzionante ✓
3. Tab "Identikit" - filtri e ricerca ✓
4. Tab "Database" - visualizzazione tabella ✓
5. Popup risultati con grafico 3D ✓

## File Necessari

Assicurati che questi file siano nella repository:

- ✅ `data/dataset_master_unified_2526.parquet` (file principale)
- ✅ Tutti i file in `artifacts/` (modelli pre-addestrati)
- ✅ `requirements.txt` (dipendenze Python)
- ✅ `Procfile` (configurazione Gunicorn)

## Comando di Avvio

Il `Procfile` contiene:

```
web: gunicorn app:server
```

Questo avvia l'applicazione Dash usando Gunicorn.

## Troubleshooting

### Log Dettagliati

Per vedere più dettagli, l'app stampa:

- Path del BASE_DIR
- Contenuto della directory
- Stato del caricamento dati

Cerca questi messaggi nei log di Render per diagnosticare problemi.

### Cache Artifacts

La prima esecuzione su Render creerà automaticamente:

- `database_df_cache.joblib` (se ha permessi di scrittura)

Nei deploy successivi, la cache velocizzerà l'avvio.

## Performance

**Primo caricamento**: 30-60 secondi (lettura parquet + elaborazione)
**Caricamenti successivi**: 10-20 secondi (con cache)

La cache viene salvata in `artifacts/database_df_cache.joblib`.
