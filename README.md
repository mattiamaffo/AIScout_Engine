# ⚽ AIScout - AI-Powered Football Scouting Tool

**AIScout** è un'applicazione web avanzata per lo scouting calcistico che unisce la potenza del **Machine Learning Statistico** con l'intelligenza dei **Large Language Models (LLM)** per rivoluzionare l'identificazione dei talenti.

Originariamente nata come tool di analisi quantitativa, la versione **2.0.0** introduce un **Agente AI Autonomo** capace di ragionare, cercare informazioni sul web e generare report tattici, trasformando i dati grezzi in insight narrativi.

<img width="2816" height="1536" alt="AIScout_informative_italian" src="https://github.com/user-attachments/assets/4cc233ab-8842-4e6a-bc07-00eca0f52653" />

-----

## 🎯 Obiettivi del Progetto

L'obiettivo di AIScout è fornire uno strumento ibrido che risponda sia alle esigenze matematiche ("Chi ha stats simili?") che a quelle qualitative ("Come gioca questo calciatore?").

L'applicazione permette di rispondere a domande complesse come:

  - *"Chi è il giocatore statisticamente più simile a Rodri in Sud America?"*
  - *"Analizzami tatticamente Joshua Zirkzee e dimmi i suoi punti deboli."*
  - *"Cercami un terzino offensivo under-23 simile a Dimarco ma che costi meno."*

-----

## 🚀 Funzionalità Principali

### 1\. 🤖 AI Tactical Assistant (NUOVO v2.0)

Un chatbot intelligente integrato direttamente nella dashboard, alimentato da **Llama 3** (via Groq) e orchestrato da **DSPy**.

  - **Router Intelligente:** L'agente capisce l'intento dell'utente (Ricerca Statistica vs Analisi Tattica) e sceglie autonomamente lo strumento giusto.
  - **Report Generativi:** Crea dossier di scouting dettagliati (Profilo, Tattica, Pro/Contro) unendo i dati interni con informazioni fresche dal web (Tavily).
  - **Memoria a Lungo Termine:** Utilizza **Qdrant** (Vector DB) per salvare i report generati e apprendere dalle ricerche passate.

### 2\. 🔍 Ricerca per Similarità (SimEngine)

  - Cerca un qualsiasi giocatore nel database (oltre 15 campionati coperti).
  - L'algoritmo **k-Nearest Neighbors (k-NN)** trova istantaneamente i "gemelli statistici" basandosi su vettori multidimensionali.
  - Visualizzazione dei risultati in tabella o tramite **grafico 3D interattivo** nello spazio PCA.

### 3\. 🛠️ Identikit (Player Builder)

  - Costruisci il tuo giocatore ideale da zero impostando filtri per Ruolo, Stile di Gioco, Età e Campionato.
  - Imposta soglie specifiche per le statistiche chiave (es. *xG \> 0.5*, *Tackle vinti \> 2.0*).

### 4\. 📊 Database Explorer

  - Esplora l'intero database con filtri avanzati e ordinamento per metriche anagrafiche e tecniche.

-----

## 🧠 Il Cervello Ibrido (Architecture v2.0)

AIScout 2.0 utilizza un'architettura a due motori che lavorano in sinergia:

### A. Il Motore Matematico (`SimEngine`)

Gestisce i dati quantitativi "Hard Data":

1.  **League Exchange Rate:** Ponderazione dinamica delle statistiche in base alla difficoltà del campionato (es. 1 gol in Premier League vale più di 1 gol in Serie B).
2.  **Dimensionality Reduction (PCA):** Comprime centinaia di metriche in poche componenti principali.
3.  **Clustering (K-Means):** Classifica i giocatori per stile di gioco reale (es. *Regista*, *Incontrista*).

### B. Il Motore Cognitivo (`AIScout Brain`)

Gestisce i dati qualitativi "Soft Data" e il ragionamento:

1.  **LLM (Groq/Llama 3):** Il cervello che processa il linguaggio naturale e scrive i report.
2.  **Orchestrator (DSPy):** Gestisce il flusso di pensiero (Chain of Thought) per garantire output strutturati e precisi.
3.  **Web Search (Tavily):** Recupera informazioni aggiornate in tempo reale (infortuni, note tattiche recenti).
4.  **Vector Memory (Qdrant/FastEmbed):** Archivia semanticamente la conoscenza acquisita.

-----

## 🛠️ Tech Stack Aggiornato

  - **Frontend:** Python, Dash, Dash Bootstrap Components.
  - **Data Science:** Pandas, Scikit-learn, NumPy.
  - **AI & LLM:**
      - **Groq API:** Inferenza Llama 3 ad alta velocità.
      - **DSPy:** Framework per la programmazione di agenti LM.
      - **Tavily:** Motore di ricerca ottimizzato per AI agent.
      - **Qdrant & FastEmbed:** Database vettoriale e generazione embeddings leggera.
  - **Deployment:** Gunicorn (WSGI Server) su Render.com.

-----

## 📂 Struttura del Progetto

```
AIScout/
├── app.py                  # Entry point e gestione Callback UI
├── aiscout_brain.py        # (NUOVO) Modulo AI: Router, DSPy, Qdrant, Tavily
├── SimEngine.py            # Motore di similarità matematica
├── layout.py               # Definizione dell'interfaccia grafica
├── data.py                 # Gestione caricamento dati e filtri
├── config.py               # Configurazioni globali
├── requirements.txt        # Dipendenze Python
├── assets/                 # CSS, immagini e loghi
├── data/                   # Dataset Parquet e CSV
└── artifacts/              # Modelli ML pre-addestrati (.joblib)
```

-----

## 💻 Installazione e Setup (v2.0)

1.  **Clona il repository:**

    ```bash
    git clone https://github.com/tuo-username/AIScout.git
    cd AIScout
    ```

2.  **Crea un file `.env`:**
    Il progetto ora richiede chiavi API per funzionare. Crea un file `.env` nella root:

    ```env
    GROQ_API_KEY=gsk_...
    TAVILY_API_KEY=tvly-...
    QDRANT_URL=https://...
    QDRANT_API_KEY=...
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

-----

## ☁️ Deployment (Render.com)

L'applicazione è **Cloud-Native**. Per il deploy su Render:

1.  Collega il repository GitHub.
2.  Imposta il **Build Command:** `pip install -r requirements.txt`.
3.  Imposta lo **Start Command:** `gunicorn app:server`.
4.  **Importante:** Inserisci le variabili d'ambiente (`GROQ_API_KEY`, ecc.) nella dashboard di Render sotto la sezione "Environment".

-----

## ℹ️ Note sui Dati

I dati utilizzati coprono la stagione **2024-2025** e includono metriche avanzate normalizzate p90.
I campionati coperti includono: Top 5 Europei, Championship, Eredivisie, Primeira Liga, Jupiler Pro League, Brasileirão, Primera División Argentina, Liga MX e Serie B.
