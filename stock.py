import pandas as pd
import plotly.graph_objects as go
import datetime
from datetime import date
import requests
import json

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px

# Display all rows and columns
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)

# Default values
DEFAULT_TICKER = "TSLA"
DEFAULT_START_DATE = "2010-06-29"
DEFAULT_END_DATE = date.today().strftime("%Y-%m-%d")

# API endpoint
API_URL = "http://localhost:5000/api"

# Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Dropdown options for statistics view
dropdown_options = [
    {'label': 'Yearly Statistics', 'value': 'Yearly Statistics'},
    {'label': 'All Years Statistics', 'value': 'All Years Statistics'}
]

# Initial year list (will be updated based on data)
current_year = datetime.datetime.now().year
year_list = [i for i in range(2010, current_year + 1)]

app.layout = html.Div([
    html.H1("Stock Dashboard", style={'textAlign': 'center', 'color': '#003366'}),
    
    html.Div([
        html.Div([
            html.Label("Enter Stock Ticker:"),
            dcc.Input(
                id='ticker-input',
                type='text',
                value=DEFAULT_TICKER,
                style={'width': '100%', 'padding': '8px', 'margin-bottom': '10px'}
            ),
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),
        
        html.Div([
            html.Label("Start Date:"),
            dcc.DatePickerSingle(
                id='start-date-picker',
                date=DEFAULT_START_DATE,
                display_format='YYYY-MM-DD',
                style={'width': '100%'}
            ),
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),
        
        html.Div([
            html.Label("End Date:"),
            dcc.DatePickerSingle(
                id='end-date-picker',
                date=DEFAULT_END_DATE,
                display_format='YYYY-MM-DD',
                style={'width': '100%'}
            ),
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),
        
        html.Button(
            'Load Stock Data', 
            id='submit-button', 
            n_clicks=0,
            style={'width': '100%', 'padding': '10px', 'margin-top': '20px', 'background-color': '#003366', 'color': 'white'}
        ),
    ], style={'margin-bottom': '20px', 'border': '1px solid #ddd', 'padding': '10px', 'border-radius': '5px'}),
    
    html.Div(id='data-loaded-message', style={'margin': '10px 0', 'color': 'green'}),
    
    html.Div([
        html.Label("Select Statistics:"),
        dcc.Dropdown(
            id='stat-select',
            options=dropdown_options,
            value='Yearly Statistics',
            placeholder='Select a statistic type'
        )
    ]),

    html.Div([
        html.Label("Select Year:"),
        dcc.Dropdown(
            id='select-year',
            options=[{'label': i, 'value': i} for i in year_list],
            value=year_list[-1]
        )
    ]),

    html.Div(id='output-container', className='chart-grid', style={'padding': '20px'}),
    
    # Store the loaded data in browser
    dcc.Store(id='stock-data-store'),
    dcc.Store(id='years-available'),
    
    # Hidden div for initialization
    html.Div(id='initialization-div', style={'display': 'none'})
])

# Callback to load stock data when the user clicks the button or on initialization
@app.callback(
    [Output('stock-data-store', 'data'),
     Output('data-loaded-message', 'children'),
     Output('years-available', 'data'),
     Output('select-year', 'options'),
     Output('select-year', 'value')],
    [Input('submit-button', 'n_clicks'),
     Input('initialization-div', 'children')],
    [State('ticker-input', 'value'),
     State('start-date-picker', 'date'),
     State('end-date-picker', 'date')]
)
def load_stock_data(n_clicks, init_trigger, ticker, start_date, end_date):
    # Determine which input triggered the callback
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    # If it's the initialization trigger, try to load data from the database first
    if trigger_id == 'initialization-div':
        # Check if data for the default ticker is already available
        result = check_ticker_data(DEFAULT_TICKER)
        
        if result:
            # Data is available, load it
            df_json = result.get('data')
            available_years = result.get('available_years', [])
            year_options = [{'label': i, 'value': i} for i in available_years]
            
            # Get the data source and customize the message
            data_source = result.get('source', 'database')  # Default to database for backward compatibility
            if data_source == 'database':
                message = f"Data for {DEFAULT_TICKER} retrieved from database!"
            else:
                message = f"Data for {DEFAULT_TICKER} loaded from Yahoo Finance!"
            
            return df_json, message, available_years, year_options, available_years[-1] if available_years else None
        
        # If no data is available, just return empty values
        return None, "Please load stock data by clicking the 'Load Stock Data' button", None, [], None
    
    # If it's the button click or n_clicks is 0 (initial load)
    if n_clicks is None:
        # This is to prevent the callback from running on initial page load for the button
        raise dash.exceptions.PreventUpdate
    
    # Use default values if not provided
    if not ticker:
        return None, "Please enter a valid ticker symbol", None, [], None
    
    try:
        # Prepare data for API request
        payload = {
            "ticker": ticker.upper(),
            "start_date": start_date,
            "end_date": end_date
        }
        
        # Send POST request to API to load stock data
        response = requests.post(f"{API_URL}/stock/load", json=payload)
        
        # Check if request was successful
        if response.status_code != 200:
            error_msg = response.json().get('message', 'Unknown error occurred')
            return None, error_msg, None, [], None
        
        # Parse response
        result = response.json()
        
        if not result.get('success', False):
            return None, result.get('message', 'Failed to load data'), None, [], None
        
        # Extract data from response
        df_json = result.get('data')
        available_years = result.get('available_years', [])
        year_options = [{'label': i, 'value': i} for i in available_years]
        
        # Get the data source and customize the message
        data_source = result.get('source', 'unknown')
        if data_source == 'database':
            message = f"Data for {ticker.upper()} retrieved from database!"
        else:
            message = f"Data for {ticker.upper()} loaded from Yahoo Finance!"
        
        return df_json, message, available_years, year_options, available_years[-1] if available_years else None
    
    except Exception as e:
        return None, f"Error loading data: {str(e)}", None, [], None

# Disable Year dropdown when All Years Statistics is selected
@app.callback(
    Output('select-year', 'disabled'),
    Input('stat-select', 'value')
)
def toggle_year_dropdown(stat_type):
    return stat_type == 'All Years Statistics'

# Chart output callback
@app.callback(
    Output('output-container', 'children'),
    [Input('stock-data-store', 'data'),
     Input('stat-select', 'value'),
     Input('select-year', 'value'),
     Input('ticker-input', 'value')]
)
def update_output(json_data, stat_type, year, ticker):
    if json_data is None:
        return html.Div("Please load stock data first by entering a ticker symbol and date range, then click 'Load Stock Data'.")
    
    # Convert the JSON data back to a DataFrame
    df2 = pd.read_json(json_data, orient='split')
    
    # Use the ticker value for display (default to "Stock" if not available)
    stock_name = ticker.upper() if ticker else "Stock"
    
    if stat_type == 'All Years Statistics':
        # Get the date range for display
        start_year = df2['date'].dt.year.min()
        end_year = df2['date'].dt.year.max()
        
        # Candlestick Chart
        fig1 = go.Figure(data=[go.Candlestick(x=df2['date'],
                                             open=df2['Open'],
                                             high=df2['High'],
                                             low=df2['Low'],
                                             close=df2['Adj Close'])])

        fig1.update_layout(
            title=f'{stock_name} Stock Candlestick Chart ({start_year}-{end_year})',
            yaxis_title='Price',
            xaxis_title='Date',
            xaxis_rangeslider_visible=True,
            width=1900,
            height=700
        )

        # Volume Chart
        df2['Year'] = df2['date'].dt.year
        yearly_volume = df2.groupby('Year')['Volume'].mean().reset_index()
        fig2 = px.area(yearly_volume, x='Year', y='Volume',
                      title=f'Average {stock_name} Trading Volume Per Year ({start_year}-{end_year})', 
                      width=1900,
                      height=700,
                      markers=True)

        fig2.update_layout(xaxis_title='Date')

        # Daily Return Chart
        df2['year'] = df2['date'].dt.year
        df2['daily_return'] = (df2['Adj Close'].pct_change()) * 100
        yearly_return = df2.groupby('year')['daily_return'].mean().reset_index()
        yearly_return['return_category'] = yearly_return['daily_return'].apply(
            lambda x: 'Positive' if x > 0 else 'Negative'
        )

        fig3 = px.bar(
            yearly_return,
            x='year',
            y='daily_return',
            color='return_category',
            color_discrete_map={'Positive': 'green', 'Negative': 'red'}
        ).update_layout(
            title=f"Average Daily Returns Per Year for {stock_name}",
            yaxis_title='Percent Daily Return (%)',
            xaxis_title='Date',
            legend_title_text="Return Category",
            width=1900,
            height=700
        )

        # Drawdown Chart
        df2['Cumulative Max'] = df2['Adj Close'].cummax()
        df2['Drawdown'] = (df2['Adj Close'] / df2['Cumulative Max'] - 1) * 100
        fig4 = px.area(df2, x='date', y='Drawdown',
                      title=f'{stock_name} Drawdowns Over All Years')
        fig4.update_layout(
            yaxis_title='Percent Drawdown (%)',
            xaxis_title='Date',
            width=1900,
            height=700
        )

        return [dcc.Graph(figure=fig1), dcc.Graph(figure=fig2), dcc.Graph(figure=fig3), dcc.Graph(figure=fig4)]

    elif stat_type == 'Yearly Statistics' and year:
        year_data = df2[df2['date'].dt.year == year]
        
        if year_data.empty:
            return html.Div(f"No data available for {stock_name} in {year}.")

        # Candlestick Chart
        fig1_year = go.Figure(data=[go.Candlestick(x=year_data['date'],
                                              open=year_data['Open'],
                                              high=year_data['High'],
                                              low=year_data['Low'],
                                              close=year_data['Adj Close'])])

        fig1_year.update_layout(
            title=f'{stock_name} Stock Candlestick Chart for {year}',
            yaxis_title='Price',
            xaxis_title='Date',
            xaxis_rangeslider_visible=True,
            width=1900,
            height=700
        )

        # Volume Chart
        fig2_year = px.area(year_data, x='date', y='Volume',
                          title=f'{stock_name} Daily Trading Volume for {year}',
                          width=1900,
                          height=700)

        fig2_year.update_layout(xaxis_title='Date')

        # Daily Return for given Year
        year_data['daily_return'] = (year_data['Adj Close'].pct_change()) * 100
        yearly_return2 = year_data.groupby('date')['daily_return'].mean().reset_index()
        yearly_return2['return_category'] = yearly_return2['daily_return'].apply(
            lambda x: 'Positive' if x > 0 else 'Negative'
        )

        fig3_year = px.bar(
            yearly_return2,
            x='date',
            y='daily_return',
            color='return_category',
            color_discrete_map={'Positive': 'green', 'Negative': 'red'}
        ).update_layout(
            title=f"{stock_name} Average Daily Returns for {year}",
            yaxis_title='Percent Daily Return (%)',
            xaxis_title='Date',
            legend_title_text="Return Category",
            width=1900,
            height=700
        )

        # Drawdown Chart
        year_data['Cumulative Max'] = year_data['Adj Close'].cummax()
        year_data['Drawdown'] = (year_data['Adj Close'] / year_data['Cumulative Max'] - 1) * 100
        fig4_year = px.area(year_data, x='date', y='Drawdown',
                           title=f'{stock_name} Drawdowns for {year}')

        fig4_year.update_layout(
            yaxis_title='Percent Drawdown (%)',
            xaxis_title='Date',
            width=1900,
            height=700
        )

        return [dcc.Graph(figure=fig1_year), dcc.Graph(figure=fig2_year), dcc.Graph(figure=fig3_year), dcc.Graph(figure=fig4_year)]

    return []




# Function to check if data is already available for a ticker
def check_ticker_data(ticker):
    try:
        # Send GET request to API to check if data exists
        response = requests.get(f"{API_URL}/stock/data/{ticker}")
        
        if response.status_code == 200 and response.json().get('success', False):
            return response.json()
        
        return None
    except:
        return None

if __name__ == '__main__':
    # Start the Flask API in a separate process
    import subprocess
    import sys
    import time
    import os
    
    # Check if the API is already running
    try:
        requests.get(f"{API_URL}/stock/tables")
        print("API is already running")
    except:
        print("Starting API server...")
        # Start the API server in a separate process
        api_process = subprocess.Popen([sys.executable, 'stock_api.py'], 
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
        
        # Wait for the API to start
        time.sleep(2)
        print("API server started")
    
    # Run the Dash app
    app.run(debug=True, port=8070)
