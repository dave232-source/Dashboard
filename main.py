# Bibliotheken importieren
import mysql.connector
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objs as go
import dash_bootstrap_components as dbc
import math

# Verbindung zur MySQL-Datenbank herstellen
conn = mysql.connector.connect(
    host='localhost',
    user='sensor_user',
    password='CanSat',
    database='sensor_data'
)

# Datenbankcursor erstellen
cursor = conn.cursor()

# Stylesheet für die Gestaltung der Oberfläche
app = dash.Dash(external_stylesheets=[dbc.themes.MINTY])

# DatePicker hinzufügen, um das Datum auszuwählen
app.layout = html.Div(style={'backgroundColor': 'gray'}, children=[
    html.H1("Dashboard Misson-CanSat-HTL Rankweil:", style={'color': 'blue'}),

    dcc.DatePickerSingle(
        id='date-picker',
        display_format='YYYY-MM-DD',
        style={'marginBottom': 10},
    ),

    html.Label('Schirmfläche (A in m^2):', style={'color': 'white'}),
    dcc.Input(id='input-a', type='number', value=0.0, step=0.01),
    html.Label('Satellitenmasse (M in kg):', style={'color': 'white'}),
    dcc.Input(id='input-m', type='number', value=0.0, step=0.01),

    html.Div([
        html.Label('Druck am Referenzniveau (p0 in hPa):', style={'color': 'white'}),
        dcc.Input(id='input-p0', type='number', value=101300, step=0.01),
    ], style={'marginBottom': 10}),

    html.Div(id='date-output', style={'fontSize': 18, 'color': 'white'}),
    html.Div(id='min-pressure-output', style={'fontSize': 18, 'color': 'white'}),
    html.Div(id='ejection-height', style={'fontSize': 18, 'color': 'white'}),
    html.Div(id='fall-velocity', style={'fontSize': 18, 'color': 'white'}),
    html.Div(id='temperature-plot-output'),
    html.Div(id='pressure-plot-output')
])

# Callback-Funktion für die Aktualisierung der Graphen basierend auf dem ausgewählten Datum
@app.callback(
    Output('date-output', 'children'),
    Output('ejection-height', 'children'),
    Output('fall-velocity', 'children'),
    Output('temperature-plot-output', 'children'),
    Output('pressure-plot-output', 'children'),
    Output('min-pressure-output', 'children'),
    Input('date-picker', 'date'),
    Input('input-a', 'value'),
    Input('input-m', 'value'),
    Input('input-p0', 'value')
)
def update_content(selected_date, A, M, p0):
    if selected_date and A and M and p0:
        # SQL-Abfrage
        query = f"SELECT data, timestamp FROM sensor_data WHERE DATE(timestamp) = '{selected_date}'"

        # Datenbankverbindung öffnen und Cursor erstellen
        conn = mysql.connector.connect(
            host='localhost',
            user='sensor_user',
            password='CanSat',
            database='sensor_data'
        )
        cursor = conn.cursor()

        # SQL-Abfrage ausführen
        cursor.execute(query)

        # Listen zum Speichern der Temperatur- und Zeitdaten für das ausgewählte Datum erstellen
        temperatures = []
        timestamps = []
        pressure = []

        # Daten aus der Abfrage abrufen und in den Listen speichern
        for row in cursor.fetchall():
            data_parts = row[0].strip("()").split(',')
            if len(data_parts) >= 2:
                temperature_value_raw = data_parts[0]
                pressure_value_raw = data_parts[1].strip(" '")
                timestamp_value = row[1]

                if temperature_value_raw and pressure_value_raw and timestamp_value:
                    try:
                        temperatures.append(float(temperature_value_raw))
                        pressure.append(float(pressure_value_raw))
                        timestamps.append(timestamp_value)
                    except ValueError:
                        print(f"Ignoring invalid data: {temperature_value_raw}, {pressure_value_raw}")

        # Verbindung und Cursor schließen
        cursor.close()
        conn.close()

        # Kleinster Luftdruckwert:
        min_pressure = None

        # Durchlaufe die Liste, um den kleinsten Wert zu finden
        for value in pressure:
            if min_pressure is None or value < min_pressure:
                min_pressure = value

        # Auswurfhöhe berechnen
        ejection_height = -7740 * math.log(min_pressure / p0)

        # Erstelle die Figure-Objekte für den Temperaturgraphen
        temperature_fig = {
            'data': [
                go.Scatter(
                    x=timestamps,
                    y=temperatures,
                    mode='lines+markers',
                ),
            ],
            'layout': go.Layout(
                title='Temperaturverlauf:',
                xaxis={'title': 'Zeit'},
                yaxis={'title': 'Temperatur (°C)', 'range': [0, 23]},
                plot_bgcolor='lightgray',
                paper_bgcolor='lightgray',
            )
        }

        # Erstelle die Figure-Objekte für den Luftdruckgraphen
        pressure_fig = {
            'data': [
                go.Scatter(
                x=timestamps,
                y=pressure,
                mode='lines+markers',
                ),
            ],
            'layout': go.Layout(
                title='Luftdruckverlauf:',
                xaxis={'title': 'Zeit'},
                yaxis={'title': 'Luftdruck'},
                plot_bgcolor='lightgray',
                paper_bgcolor='lightgray',
            )
        }

        # Wichtige Konstanten zur Berechnung der Fallgeschwindigkeit
        g = 9.81  # Gravitationskonstante (m/s^2)
        cw = 1.2  # Widerstandsbeiwert
        pLuft = 1.3  # Luftdichte (kg/m^3)

        if A and M:
            vE_squared = (2 * M * g) / (cw * pLuft * A)
            vE = vE_squared ** 0.5  # Berechnung der Fallgeschwindigkeit

            return (
                f'- Datum ausgewählt: {selected_date}',
                f'- Auswurfhöhe: {ejection_height:.2f} m',  # Berechnete Auswurfhöhe
                f'- Fallgeschwindigkeit: {vE:.2f} m/s',
                dcc.Graph(figure=temperature_fig),
                dcc.Graph(figure=pressure_fig),
                f'- Kleinster Luftdruckwert: {min_pressure:.2f} hPa'
            )
        else:
            return 'Bitte Werte für A und M eingeben!', '', '', None, None, ''
    else:
        # Wenn kein Datum ausgewählt wurde, zeige eine Nachricht
        return 'Bitte ein Datum auswählen!', '', '', None, None, ''

if __name__ == '__main__':
    app.run_server(debug=True)
