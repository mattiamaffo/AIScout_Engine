from dash import dcc, html # type: ignore
from data import PLAYER_SEARCH_OPTIONS

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
            
            html.Div(className='search-filters', children=[
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
