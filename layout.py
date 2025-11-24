from dash import dcc, html # type: ignore
import config
from data import all_roles_options, with_blank, SORT_BY_OPTIONS, PLAYER_SEARCH_OPTIONS # Importa le opzioni
import dash_bootstrap_components as dbc # type: ignore
from version import get_full_version_string


# --- Layout Scheda 1: Search Player ---
search_player_layout = html.Div(
    className='glass-card',
    children=[
        html.Div(className='glass-card-content', children=[
            html.H2("Trova, confronta e scopri talenti calcistici in pochi click!", className='glass-subtitle'),
            
            html.Div(
                className='search-button-container', 
                children=[
                    dcc.Dropdown(
                        id='search-bar', 
                        options=PLAYER_SEARCH_OPTIONS, 
                        placeholder='Digita il nome di un giocatore...',
                        className='search-bar-container-wrapper',
                        optionHeight=55, 
                        clearable=True
                    ),
                    
                    html.Button(
                        "Trova Simili", 
                        id='search-button', 
                        className='search-button' 
                    )
                ]
            ),
            
            html.Div(className='slider-section', children=[
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
            ]),
            
            html.Div(className='search-filters', style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '1rem', 'width': '100%'}, children=[
                html.Div(className='toggle-container', children=[
                    dcc.Checklist(
                        id='search-filter-nation',
                        options=[{'label': ' Filtra per stessa Nazione', 'value': 'filter'}],
                        value=[],
                        className='toggle-switch',
                        inputClassName='toggle-input',
                        labelClassName='toggle-label'
                    )
                ]),
                html.Div(className='toggle-container', children=[
                    dcc.Checklist(
                        id='search-filter-comp',
                        options=[{'label': ' Filtra per stesso Campionato', 'value': 'filter'}],
                        value=[],
                        className='toggle-switch',
                        inputClassName='toggle-input',
                        labelClassName='toggle-label'
                    )
                ]),
                html.Div(className='toggle-container', children=[
                    dcc.Checklist(
                        id='search-filter-height',
                        options=[{'label': ' Filtra per Altezza simile (±5cm)', 'value': 'filter'}],
                        value=[],
                        className='toggle-switch',
                        inputClassName='toggle-input',
                        labelClassName='toggle-label'
                    )
                ]),
                html.Div(className='toggle-container', children=[
                    dcc.Checklist(
                        id='search-filter-weight',
                        options=[{'label': ' Filtra per Peso simile (±5kg)', 'value': 'filter'}],
                        value=[],
                        className='toggle-switch',
                        inputClassName='toggle-input',
                        labelClassName='toggle-label'
                    )
                ])
            ]),
        ])
    ]
)

# --- Layout Scheda 2: Identikit (Redesigned modern layout) ---
identikit_layout = html.Div(className='glass-card', style={'maxWidth': '1200px', 'marginTop': '2rem'}, children=[
    html.Div(className='glass-card-content', children=[
        html.Div(className='identikit-header', children=[
            html.H3('Identikit', className='glass-subtitle'),
            html.P('Costruisci il tuo giocatore ideale', className='identikit-sub')
        ]),

        html.Div(className='identikit-grid-container', children=[
            # LEFT: Form Section
            html.Div(className='identikit-form-section', children=[
                html.H5("Parametri di Ricerca", className="section-title"),
                
                # Position & Cluster Row
                html.Div(className='form-row', children=[
                    html.Div(className='form-group', children=[
                        html.Label("Posizione", className="form-label"),
                        dcc.Dropdown(
                            id='identikit-pos',
                            options=with_blank([{'label': p, 'value': p} for p in config.RUOLI]),
                            placeholder='Seleziona Posizione...',
                            clearable=True,
                            className='identikit-dropdown'
                        ),
                    ]),
                    html.Div(className='form-group', children=[
                        html.Label("Stile / Cluster", className="form-label"),
                        dcc.Dropdown(
                            id='identikit-cluster',
                            options=with_blank([]),
                            placeholder='Seleziona Stile...',
                            clearable=True,
                            className='identikit-dropdown'
                        ),
                    ]),
                ]),

                # Age & League Row
                html.Div(className='form-row', children=[
                    html.Div(className='form-group', children=[
                        html.Label("Età Massima", className="form-label"),
                        dcc.Input(
                            id='identikit-age', 
                            type='number', 
                            placeholder='Es. 25', 
                            className='identikit-input', 
                            min=16, max=45
                        ),
                    ]),
                    html.Div(className='form-group', children=[
                        html.Label("Campionato", className="form-label"),
                        dcc.Dropdown(
                            id='identikit-league',
                            options=with_blank([{'label': l, 'value': l} for l in config.LEAGUES_LIST]),
                            placeholder='Tutti i Campionati',
                            clearable=True,
                            className='identikit-dropdown'
                        ),
                    ]),
                ]),

                # Nation Row
                html.Div(className='form-row', children=[
                    html.Div(className='form-group full-width', children=[
                        html.Label("Nazione", className="form-label"),
                        dcc.Dropdown(
                            id='identikit-nation',
                            options=with_blank([]),
                            placeholder='Tutte le Nazioni',
                            clearable=True,
                            className='identikit-dropdown'
                        ),
                    ]),
                ]),

                html.Div(className='identikit-actions', children=[
                    html.Button('Cerca', id='identikit-find-button', n_clicks=0, className='search-button'),
                    html.Button('Reset', id='identikit-reset-button', n_clicks=0, className='reset-button')
                ])
            ]),

            # RIGHT: Features Section
            html.Div(className='identikit-features-section', children=[
                html.H5('Caratteristiche del Ruolo', className='section-title'),
                html.Div(id='identikit-role-features', className='features-container')
            ])
        ]),

        # LEGEND: Collapsible
        html.Details(className='identikit-legend-details', children=[
            html.Summary("Mostra Legenda Caratteristiche", className='legend-summary'),
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
                ]),
            ])
        ])
    ])
])

# --- Layout Scheda 3: Database ---
database_layout = html.Div(className='glass-card db-layout-wrapper', style={'maxWidth': '95%', 'marginTop': '2rem'}, children=[
    dcc.Store(id='db-pagination-store', data={'page': 1, 'total_pages': 1, 'total_records': 0}),

    html.Div(className='glass-card-content', children=[
        # --- Header Section ---
        html.Div(className='db-header', children=[
            html.H3("Database Scouting", className='glass-subtitle'),
            html.P("Esplora, filtra e analizza l'intero database giocatori", className='identikit-sub')
        ]),

        # --- Filters Section ---
        html.Div(className='db-filters-container', children=[
            # Row 1: Search Name (Full Width)
            html.Div(className='db-search-row', children=[
                html.I(className="fas fa-search search-icon"),
                dcc.Input(
                    id='db-filter-name', 
                    placeholder='Cerca giocatore per nome...', 
                    className='db-search-input',
                    debounce=True
                )
            ]),
            
            # Row 2: Grid Filters
            html.Div(className='db-filters-grid', children=[
                # Position
                html.Div(className='filter-group', children=[
                    html.Label("Posizione", className='filter-label'),
                    dcc.Dropdown(
                        id='db-filter-pos',
                        options=with_blank([{'label': p, 'value': p} for p in config.RUOLI]),
                        placeholder='Tutte',
                        className='db-dropdown',
                        searchable=False,
                        clearable=True
                    )
                ]),
                # Role
                html.Div(className='filter-group', children=[
                    html.Label("Ruolo", className='filter-label'),
                    dcc.Dropdown(
                        id='db-filter-role',
                        options=with_blank(all_roles_options),
                        placeholder='Tutti',
                        className='db-dropdown',
                        searchable=False,
                        clearable=True
                    )
                ]),
                # Age Min
                html.Div(className='filter-group', children=[
                    html.Label("Età Min", className='filter-label'),
                    dcc.Input(
                        id='db-filter-age-min', 
                        placeholder='16', 
                        className='db-input-number',
                        type='number',
                        min=15, max=45
                    )
                ]),
                # Age Max
                html.Div(className='filter-group', children=[
                    html.Label("Età Max", className='filter-label'),
                    dcc.Input(
                        id='db-filter-age-max', 
                        placeholder='45', 
                        className='db-input-number',
                        type='number',
                        min=15, max=45
                    )
                ]),
                # League
                html.Div(className='filter-group', children=[
                    html.Label("Campionato", className='filter-label'),
                    dcc.Dropdown(
                        id='db-filter-league',
                        options=with_blank([{'label': l, 'value': l} for l in config.LEAGUES_LIST]),
                        placeholder='Tutti',
                        className='db-dropdown',
                        searchable=False,
                        clearable=True
                    )
                ]),
                # Sort By
                html.Div(className='filter-group', children=[
                    html.Label("Ordina per", className='filter-label'),
                    dcc.Dropdown(
                        id='db-sort-by',
                        options=with_blank(SORT_BY_OPTIONS),
                        placeholder='Seleziona...',
                        className='db-dropdown',
                        searchable=False,
                        clearable=True
                    )
                ]),
            ])
        ]),

        # --- Results Table Section ---
        html.Div(className='db-results-wrapper', children=[
            html.Div(className='db-table-header', children=[
                html.Span("#", className='col-header col-index'),
                html.Span("Giocatore", className='col-header col-name'),
                html.Span("Pos", className='col-header col-pos'),
                html.Span("Età", className='col-header col-age'),
                html.Span("Naz", className='col-header col-nat'),
                html.Span("Camp", className='col-header col-league'),
            ]),
            
            # Rows Container (Scrollable)
            html.Div(id='db-player-rows', className='db-table-body')
        ]),

        # --- Pagination Footer ---
        html.Div(className='db-pagination-footer', children=[
            html.Button(html.I(className='fas fa-chevron-left'), id='db-prev-page', className='pagination-btn'),
            html.Span("Pagina 1 di 1", id='db-page-info', className='pagination-info'),
            html.Button(html.I(className='fas fa-chevron-right'), id='db-next-page', className='pagination-btn')
        ])
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
        style={'minHeight': '100vh', 'boxSizing': 'border-box', 'position': 'relative'},
        children=[
            # --- Store per i trigger di ricerca ---
            dcc.Store(id='search-trigger-store'),
            
            # --- NUOVO: Store per i RISULTATI (Dati + Info Giocatore) ---
            # Questo permette di passare i dati tra tabella, grafico e download senza ricalcolare
            dcc.Store(id='results-store'),

            # --- NUOVO: Componente per il Download CSV ---
            dcc.Download(id="download-dataframe-csv"),
            
            # --- NUOVO: Interval per startup (Fix Error) ---
            dcc.Interval(id='startup-interval', interval=1000, n_intervals=0, max_intervals=1),

            html.Img(id='app-logo', src='/assets/new_logo.png'),
            
            # --- Numero di Versione (Bottom Left) ---
            html.Div(
                className='app-version',
                children=get_full_version_string(),
                title='Versione AIScout'
            ),
            
            html.Div(id='app-navbar', className='segmented-control', children=[
                html.Div(className='nav-slider'),
                html.Button(html.I(className="fas fa-search"), id='tab-search', n_clicks=0, className='icon-nav-item active'),
                html.Button(html.I(className="fas fa-file-alt"), id='tab-identikit', n_clicks=0, className='icon-nav-item'),
                html.Button(html.I(className="fas fa-database"), id='tab-database', n_clicks=0, className='icon-nav-item')
            ]),
            # Global hidden holder for k-slider (keeps the id available to callbacks)
            dcc.Input(id='k-slider', type='number', value=10, style={'display': 'none'}),
            
            # Include all tab layouts simultaneously (shown/hidden via CSS)
            html.Div(id='tab-content-search', children=search_player_layout, style={'display': 'block'}, className='tab-content-animated'),
            html.Div(id='tab-content-identikit', children=identikit_layout, style={'display': 'none'}, className='tab-content-animated'),
            html.Div(id='tab-content-database', children=database_layout, style={'display': 'none'}, className='tab-content-animated'),
            

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