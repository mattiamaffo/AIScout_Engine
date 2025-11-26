from dash import dcc, html # type: ignore

ai_assistant_layout = html.Div(className='glass-card ai-layout-wrapper', children=[
    html.Div(className='glass-card-content', children=[
        # --- Header Section ---
        html.Div(className='ai-header', children=[
            html.Div(children=[
                html.I(className="fas fa-robot"),
                html.Div(children=[
                    html.H4("AI Tactical Assistant"),
                    html.P("Chiedi informazioni su giocatori, tattiche e strategie")
                ])
            ]),
            html.Button(
                html.I(className="fas fa-trash-alt"),
                id='reset-chat-btn',
                className='chat-reset-btn',
                n_clicks=0,
                title="Nuova Chat"
            )
        ]),

        # --- Chat Window (Scrollable) ---
        html.Div(
            id='chat-window',
            className='chat-window',
            children=[
                # Messaggio di benvenuto iniziale
                html.Div(className='ai-message', children=[
                    html.Div(className='ai-message-label', children="🤖 AI Assistant"),
                    html.Div(className='ai-message-text', children="Ciao! Sono il tuo assistente tattico AIScout. Posso aiutarti a trovare giocatori simili, analizzare profili tattici e rispondere a domande sul calcio. Presto sarò collegato al cervello AI completo!")
                ])
            ]
        ),

        # --- Input Footer ---
        html.Div(className='chat-input-footer', children=[
            dcc.Input(
                id='user-input',
                type='text',
                placeholder='Scrivi la tua domanda... (es: "Trova giocatori simili a Haaland")',
                className='chat-input',
                debounce=False,
                n_submit=0,
                disabled=True # Disabilitato all'avvio
            ),
            html.Button(
                html.I(className="fas fa-paper-plane"),
                id='send-btn',
                className='chat-send-btn',
                n_clicks=0,
                disabled=True # Disabilitato all'avvio
            )
        ])
    ])
])
