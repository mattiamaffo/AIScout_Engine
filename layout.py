from dash import dcc, html # type: ignore
import config
from data import all_roles_options, with_blank, SORT_BY_OPTIONS, PLAYER_SEARCH_OPTIONS # Importa le opzioni
import dash_bootstrap_components as dbc # type: ignore



# --- Layout Scheda 1: Search Player ---
search_player_layout = html.Div([
    html.Div(
        className='search-button-container', # Nuovo contenitore
        children=[
            # La barra di ricerca esistente
            dcc.Dropdown(
                id='search-bar', 
                options=PLAYER_SEARCH_OPTIONS, 
                placeholder='Digita il nome di un giocatore...',
                className='search-bar-container-wrapper',
                optionHeight=50, 
                clearable=True
            ),
            
            # Il nuovo bottone di ricerca
            html.Button(
                [html.I(className="fas fa-search"), " Trova Simili"], # Icona + Testo
                id='search-button', # ID per la callback
                className='search-button' # Classe per lo stile
            )
        ]
    ),
    html.P("Numero giocatori correlati (K)", className='slider-label'),
    html.Div(
        className='slider-container-wrapper',
        children=[
            dcc.Slider(
                id='k-slider-visible',
                min=1,
                max=20,
                step=1,
                value=10,
                marks={1: '1', 5: '5', 10: '10', 15: '15', 20: '20'}
            )
        ]
    ),
    
    # Filtri opzionali per Search Player
    html.Div(className='search-filters', children=[
        html.Label(className='filter-checkbox-label', children=[
            dcc.Checklist(
                id='search-filter-nation',
                options=[{'label': ' Filtra per stessa Nazione', 'value': 'filter'}],
                value=[],
                className='filter-checkbox'
            )
        ]),
        html.Label(className='filter-checkbox-label', children=[
            dcc.Checklist(
                id='search-filter-comp',
                options=[{'label': ' Filtra per stesso Campionato', 'value': 'filter'}],
                value=[],
                className='filter-checkbox'
            )
        ])
    ]),
])

# --- Layout Scheda 2: Identikit (Redesigned modern layout) ---
identikit_layout = html.Div(className='identikit-shell', children=[
    html.Div(className='identikit-top', children=[
        html.Div(className='identikit-title', children=[
            html.H3('Identikit'),
            html.P('Costruisci il tuo giocatore ideale', className='identikit-sub')
        ]),
        # keep nav spacing consistent but minimal header
    ]),

    html.Div(className='identikit-main', children=[
        # LEFT: compact modern form
        html.Div(className='identikit-form', children=[
            dcc.Dropdown(
                id='identikit-pos',
                options=with_blank([{'label': p, 'value': p} for p in config.RUOLI]),
                placeholder='Posizione (opzionale - cerca in tutti)',
                clearable=True,
                className='identikit-control'
            ),

            dcc.Dropdown(
                id='identikit-cluster',
                options=with_blank([]),
                placeholder='Stile / Cluster (es. Mediano)',
                clearable=True,
                className='identikit-control'
            ),

            dcc.Input(id='identikit-age', type='number', placeholder='Età Max', className='identikit-control', min=0, max=50),

            dcc.Dropdown(
                id='identikit-league',
                options=with_blank([{'label': l, 'value': l} for l in config.LEAGUES_LIST]),
                placeholder='Campionato',
                clearable=True,
                className='identikit-control'
            ),

            dcc.Dropdown(
                id='identikit-nation',
                options=with_blank([]),
                placeholder='Nazione',
                clearable=True,
                className='identikit-control'
            ),

            html.Div(className='identikit-hint', children='Similarità basata solo su caratteristiche di gioco'),
            html.Div(className='identikit-actions', children=[
                html.Button('Cerca', id='identikit-find-button', n_clicks=0, className='btn-identikit-primary'),
                html.Button('Reset', id='identikit-reset-button', n_clicks=0, className='btn-identikit-reset')
            ])
        ]),

        # RIGHT: preview / role features
        html.Div(className='identikit-preview', children=[
            html.Div(className='preview-card', children=[
                html.H5('Caratteristiche del Ruolo', className='preview-title'),
                html.Div(id='identikit-role-features', className='preview-features')
            ])
        ])
    ]),

    # LEGEND: Features explanation
    html.Div(className='identikit-legend', children=[
        html.H5('Legenda Caratteristiche', className='legend-title'),
        html.Div(className='legend-grid', children=[
            # Metriche Offensive
            html.Div(className='legend-item', children=[
                html.Span('Gls', className='legend-key'),
                html.Span('Goal segnati', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('Ast', className='legend-key'),
                html.Span('Assist forniti', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('G+A', className='legend-key'),
                html.Span('Goal + Assist', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('xG', className='legend-key'),
                html.Span('Expected Goals (gol attesi)', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('npxG', className='legend-key'),
                html.Span('Non-Penalty Expected Goals', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('G-PK', className='legend-key'),
                html.Span('Goal senza rigori', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('xAG', className='legend-key'),
                html.Span('Expected Assisted Goals', className='legend-value')
            ]),
            # Passaggi e Creazione
            html.Div(className='legend-item', children=[
                html.Span('KP', className='legend-key'),
                html.Span('Key Passes (passaggi chiave)', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('PPA', className='legend-key'),
                html.Span('Passaggi nell\'area avversaria', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('PrgP', className='legend-key'),
                html.Span('Passaggi progressivi', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('Cmp%', className='legend-key'),
                html.Span('Percentuale completamento passaggi', className='legend-value')
            ]),
            # Possesso e Movimento
            html.Div(className='legend-item', children=[
                html.Span('Touches', className='legend-key'),
                html.Span('Tocchi di palla', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('Carries', className='legend-key'),
                html.Span('Conduzioni palla', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('PrgC', className='legend-key'),
                html.Span('Conduzioni progressive', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('PrgR', className='legend-key'),
                html.Span('Ricezioni progressive', className='legend-value')
            ]),
            # Difesa
            html.Div(className='legend-item', children=[
                html.Span('Tkl', className='legend-key'),
                html.Span('Tackle tentati', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('TklW', className='legend-key'),
                html.Span('Tackle vinti', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('Int', className='legend-key'),
                html.Span('Intercettazioni', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('Tkl+Int', className='legend-key'),
                html.Span('Tackle + Intercettazioni', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('Blocks', className='legend-key'),
                html.Span('Tiri bloccati', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('Clr', className='legend-key'),
                html.Span('Respinte difensive', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('Recov', className='legend-key'),
                html.Span('Recuperi palla', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('Err', className='legend-key'),
                html.Span('Errori che portano a tiri', className='legend-value')
            ]),
            # Errori e Altro
            html.Div(className='legend-item', children=[
                html.Span('Dis', className='legend-key'),
                html.Span('Palloni persi', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('Mis', className='legend-key'),
                html.Span('Errori di controllo', className='legend-value')
            ]),
            # Portieri
            html.Div(className='legend-item', children=[
                html.Span('GA', className='legend-key'),
                html.Span('Goal subiti', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('Saves', className='legend-key'),
                html.Span('Parate effettuate', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('Save%', className='legend-key'),
                html.Span('Percentuale parate', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('CS', className='legend-key'),
                html.Span('Clean Sheets (porta inviolata)', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('CS%', className='legend-key'),
                html.Span('Percentuale Clean Sheets', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('PKA', className='legend-key'),
                html.Span('Rigori subiti', className='legend-value')
            ]),
            html.Div(className='legend-item', children=[
                html.Span('PKsv', className='legend-key'),
                html.Span('Rigori parati', className='legend-value')
            ])
        ])
    ])
])

# --- Layout Scheda 3: Database ---
database_layout = html.Div(className='db-container', children=[
    dcc.Store(id='db-pagination-store', data={'page': 1, 'total_pages': 1, 'total_records': 0}),

    html.Button(
        [html.I(className="fas fa-filter"), " Mostra Filtri"],
        id='mobile-filter-btn',
        n_clicks=0,
        className='mobile-filter-button'
    ),

    html.Div(id='db-filter-bar', className='db-filter-bar', children=[
        dcc.Input(
            id='db-filter-name', 
            placeholder='Cerca per Nome...', 
            className='db-filter-input db-filter-name'
        ),
        dcc.Dropdown(
            id='db-filter-pos',
            options=with_blank([{'label': p, 'value': p} for p in config.RUOLI]),
            placeholder='Posizione...',
            className='db-filter-dropdown db-filter-pos',
            searchable=False
        ),
        dcc.Dropdown(
            id='db-filter-role',
            options=with_blank(all_roles_options),
            placeholder='Ruolo...',
            className='db-filter-dropdown db-filter-role',
            searchable=False
        ),
        dcc.Input(
            id='db-filter-age-min', 
            placeholder='Età Min...', 
            className='db-filter-input db-filter-age-min',
            type='number',
            min=0
        ),
        dcc.Input(
            id='db-filter-age-max', 
            placeholder='Età Max...', 
            className='db-filter-input db-filter-age-max',
            type='number',
            min=0
        ),
        dcc.Dropdown(
            id='db-filter-league',
            options=with_blank([{'label': l, 'value': l} for l in config.LEAGUES_LIST]),
            placeholder='Campionato...',
            className='db-filter-dropdown db-filter-league',
            searchable=False
        ),
        dcc.Dropdown(
        id='db-sort-by',
        options=with_blank(SORT_BY_OPTIONS),
        placeholder='Ordina per...',
        className='db-filter-dropdown db-filter-sort', # Nuova classe per lo stile
        searchable=False
        )
    ]),
    html.Div(className='db-player-list-box', children=[
        html.Div(className='player-row header', children=[
            html.Span("#", className='row-index'),
            html.Span("Giocatore", className='row-name'),
            html.Span("Pos", className='row-pos'),
            html.Span("Età", className='row-age'),
            html.Span("Nazione", className='row-nat'),
            html.Span("Campionato", className='row-comp')
        ]),
        html.Div(id='db-player-rows', className='player-rows')
    ]),
    html.Div(className='pagination-controls', children=[
        html.Button(html.I(className='fas fa-arrow-left'), id='db-prev-page', className='pagination-button'),
        html.Span("Pagina 1 di X", id='db-page-info'),
        html.Button(html.I(className='fas fa-arrow-right'), id='db-next-page', className='pagination-button')
    ])
])

# --- Funzione Layout Principale ---

def create_main_layout():
    """
    Crea il layout principale dell'app.
    """
    return html.Div(
        id='main-container',
        className='layout-home',
        style={'height': '100vh', 'boxSizing': 'border-box', 'position': 'relative'},
        children=[
            # --- Store per i trigger di ricerca ---
            dcc.Store(id='search-trigger-store'),
            
            # --- NUOVO: Store per i RISULTATI (Dati + Info Giocatore) ---
            # Questo permette di passare i dati tra tabella, grafico e download senza ricalcolare
            dcc.Store(id='results-store'),

            # --- NUOVO: Componente per il Download CSV ---
            dcc.Download(id="download-dataframe-csv"),

            html.Img(id='app-logo', src='/assets/FullLogo_Transparent.png'),
            html.P("Trova, confronta e scopri talenti calcistici in pochi click!", id='app-subtitle', className='app-subtitle'),
            
            html.Div(id='app-navbar', className='segmented-control', children=[
                html.Button(html.I(className="fas fa-search"), id='tab-search', n_clicks=0, className='icon-nav-item active'),
                html.Button(html.I(className="fas fa-file-alt"), id='tab-identikit', n_clicks=0, className='icon-nav-item'),
                html.Button(html.I(className="fas fa-database"), id='tab-database', n_clicks=0, className='icon-nav-item')
            ]),
            # Global hidden holder for k-slider (keeps the id available to callbacks)
            dcc.Input(id='k-slider', type='number', value=10, style={'display': 'none'}),
            
            # Include all tab layouts simultaneously (shown/hidden via CSS)
            html.Div(id='tab-content-search', children=search_player_layout, style={'display': 'block'}),
            html.Div(id='tab-content-identikit', children=identikit_layout, style={'display': 'none'}),
            html.Div(id='tab-content-database', children=database_layout, style={'display': 'none'}),
            
            html.Div(id='output-display', style={'marginTop': '1rem', 'color': '#31333F'}),
            

            # --- Popup (Modal) Aggiornato ---
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Giocatori Simili")),
                    dbc.ModalBody(
                        dcc.Loading(
                            id="modal-loading-spinner",
                            type="default",
                            # Il contenuto verrà iniettato qui dalla callback
                            children=html.Div(id="modal-results-content") 
                        )
                    ),
                    dbc.ModalFooter(
                        html.Div(style={'display': 'flex', 'gap': '10px', 'width': '100%', 'justifyContent': 'space-between'}, children=[
                            
                            # --- Gruppo Bottoni Sinistra (Azioni) ---
                            html.Div(style={'display': 'flex', 'gap': '10px'}, children=[
                                dbc.Button(
                                    [html.I(className="fas fa-table me-2"), "Tabella"], 
                                    id="btn-view-table", 
                                    color="light", 
                                    className="me-1",
                                    n_clicks=0,
                                    active=True # Default attivo
                                ),
                                dbc.Button(
                                    [html.I(className="fas fa-cube me-2"), "Spazio 3D"], 
                                    id="btn-view-3d", 
                                    color="primary", 
                                    outline=True,
                                    n_clicks=0
                                ),
                            ]),

                            # --- Gruppo Bottoni Destra (Download & Chiudi) ---
                            html.Div(style={'display': 'flex', 'gap': '10px'}, children=[
                                dbc.Button(
                                    [html.I(className="fas fa-download me-2"), "CSV"], 
                                    id="btn-download-csv", 
                                    color="success", 
                                    outline=True,
                                    n_clicks=0
                                ),
                                dbc.Button(
                                    "Chiudi", 
                                    id="modal-close-button", 
                                    color="secondary",
                                    n_clicks=0
                                )
                            ])
                        ])
                    ),
                ],
                id="results-modal",
                is_open=False,
                size="lg",
                backdrop="static",
                scrollable=True
            ),
        ]
    )