import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
import plotly.graph_objects as go
import datetime
from datetime import date

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

# Database connection
engine = create_engine('postgresql://postgres:anirudh9@localhost:5432/postgres')

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
    dcc.Store(id='years-available')
])

# Callback to load stock data when the user clicks the button
@app.callback(
    [Output('stock-data-store', 'data'),
     Output('data-loaded-message', 'children'),
     Output('years-available', 'data'),
     Output('select-year', 'options'),
     Output('select-year', 'value')],
    [Input('submit-button', 'n_clicks')],
    [State('ticker-input', 'value'),
     State('start-date-picker', 'date'),
     State('end-date-picker', 'date')]
)
def load_stock_data(n_clicks, ticker, start_date, end_date):
    if n_clicks == 0:
        # Initial load with default values
        ticker = DEFAULT_TICKER
        start_date = DEFAULT_START_DATE
        end_date = DEFAULT_END_DATE
    
    # Validate inputs
    if not ticker:
        return None, "Please enter a valid ticker symbol", None, [], None
    
    try:
        # Download stock data
        df = yf.download(ticker.upper(), start=start_date, end=end_date, auto_adjust=False)
        
        if df.empty:
            return None, f"No data found for {ticker}. Please check the ticker symbol and date range.", None, [], None
        
        # Process the data
        df.columns = df.columns.droplevel(1) if isinstance(df.columns, pd.MultiIndex) else df.columns
        df = df.reset_index()
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Create a unique table name based on the ticker
        table_name = f"{ticker.lower()}_data"
        
        # Save to CSV (optional)
        csv_filename = f"{ticker.lower()}_data.csv"
        df.to_csv(csv_filename, index=False)
        
        # Save to SQL
        df.to_sql(table_name, engine, if_exists='replace', index=False)
        
        # Read from SQL
        query = f"SELECT * FROM {table_name};"
        df2 = pd.read_sql_query(query, engine)
        df2['date'] = pd.to_datetime(df2['Date'])  # Align with SQL column
        df2.drop(columns=['Date'], inplace=True)
        
        # Get available years for the dropdown
        available_years = sorted(df2['date'].dt.year.unique().tolist())
        year_options = [{'label': i, 'value': i} for i in available_years]
        
        # Store the data as JSON for Dash
        df_json = df2.to_json(date_format='iso', orient='split')
        
        return df_json, f"Data for {ticker.upper()} loaded successfully!", available_years, year_options, available_years[-1]
    
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


if __name__ == '__main__':
    app.run(debug=True, port=8070)