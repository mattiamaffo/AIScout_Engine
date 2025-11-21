# ⚽ AIScout - AI-Powered Football Scouting Tool

**AIScout** è un'applicazione web avanzata per lo scouting calcistico che utilizza il Machine Learning per identificare talenti, trovare giocatori simili e analizzare profili statistici complessi.

Originariamente sviluppata come applicazione desktop, è stata migrata in una Web App moderna basata su **Dash** e pronta per il deploy in cloud (es. Render.com).

---

## 🎯 Obiettivi del Progetto

L'obiettivo di AIScout è supportare osservatori, analisti e appassionati di calcio nel processo di identificazione dei talenti (Talent Identification) attraverso un approccio data-driven.

L'applicazione permette di rispondere a domande come:

- _"Chi è il giocatore statisticamente più simile a Rodri in Sud America?"_
- _"Sto cercando un terzino offensivo Under 23 con alti valori di assist e progressione palla."_
- _"Quali sono i profili emergenti nel campionato belga simili ai top player europei?"_

---

## 🚀 Funzionalità Principali

### 1. 🔍 Ricerca per Similarità (Player Search)

- Cerca un qualsiasi giocatore nel database (oltre 15 campionati coperti).
- L'algoritmo **k-Nearest Neighbors (k-NN)** trova istantaneamente i giocatori più simili basandosi su decine di metriche statistiche.
- Visualizzazione dei risultati in tabella o tramite **grafico 3D** nello spazio vettoriale PCA.

### 2. 🛠️ Identikit (Player Builder)

- Costruisci il tuo giocatore ideale da zero.
- Filtra per **Ruolo** (es. Attaccante), **Stile di Gioco** (es. "Bomber", "Falso 9"), **Età**, **Campionato** e **Nazionalità**.
- Imposta soglie specifiche per le statistiche chiave (es. _xG > 0.5_, _Tackle vinti > 2.0_).
- Il motore trova i giocatori che meglio si adattano ai criteri definiti.

### 3. 📊 Database Explorer

- Esplora l'intero database di giocatori.
- Filtri avanzati e ordinamento per metriche anagrafiche e tecniche.

---

## 🧠 Il Motore AI (SimEngine)

Il cuore di AIScout è il `SimEngine`, una pipeline di Machine Learning che elabora i dati grezzi per calcolare le similarità.

1.  **Preprocessing:** I dati vengono normalizzati e convertiti in metriche _per 90 minuti_ (p90).
2.  **Dimensionality Reduction (PCA):** Utilizza l'Analisi delle Componenti Principali per ridurre la complessità dei dati mantenendo il 95% della varianza informativa.
3.  **Clustering (K-Means):** I giocatori vengono raggruppati in "Cluster" che rappresentano stili di gioco specifici (es. _Regista Arretrato_, _Terzino di Spinta_).
4.  **Similarity Search (k-NN):** Utilizza la _Cosine Similarity_ per calcolare la distanza vettoriale tra i giocatori all'interno dello stesso cluster o ruolo.

---

## 🛠️ Tech Stack

- **Backend/Frontend:** Python, Dash, Dash Bootstrap Components.
- **Data Science:** Pandas, Scikit-learn, NumPy.
- **Visualizzazione:** Plotly (Grafici 3D interattivi).
- **Deployment:** Gunicorn (WSGI Server).
- **Data Storage:** Parquet (per performance elevate di lettura), Joblib (per serializzazione modelli).

---

## 📂 Struttura del Progetto

```
AIScout/
├── app.py                  # Entry point dell'applicazione Dash
├── SimEngine.py            # Motore di similarità (caricamento modelli e query)
├── layout.py               # Definizione dell'interfaccia grafica (Frontend)
├── data.py                 # Gestione caricamento dati e filtri database
├── config.py               # Configurazioni globali (percorsi, costanti)
├── requirements.txt        # Dipendenze Python
├── Procfile                # Configurazione per il deploy su Render/Heroku
├── assets/                 # CSS, immagini e loghi
├── data/                   # Dataset in formato CSV e Parquet
└── artifacts/              # Modelli ML pre-addestrati (PCA, Scalers, k-NN)
```

---

## 💻 Installazione e Avvio Locale

1.  **Clona il repository:**

    ```bash
    git clone https://github.com/tuo-username/AIScout.git
    cd AIScout
    ```

2.  **Crea un virtual environment (opzionale ma consigliato):**

    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

3.  **Installa le dipendenze:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Avvia l'applicazione:**
    ```bash
    python app.py
    ```
    L'app sarà disponibile su `http://127.0.0.1:8050`.

---

## ☁️ Deployment (Render.com)

L'applicazione è configurata per essere deployata facilmente su Render.com come **Web Service**.

1.  Collega il repository GitHub a Render.
2.  Imposta i seguenti parametri:
    - **Runtime:** Python 3
    - **Build Command:** `pip install -r requirements.txt`
    - **Start Command:** `gunicorn app:server`
3.  Deploy! 🚀

---

## ℹ️ Note sui Dati

I dati utilizzati coprono la stagione **2024-2025** (e precedenti) e includono metriche avanzate come _Expected Goals (xG)_, _Progressive Carries_, _Defensive Actions_, ecc.
I campionati coperti includono: Top 5 Europei, Championship, Eredivisie, Primeira Liga, Jupiler Pro League, Brasileirão, Primera División Argentina.
