import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
from flask import Flask, request, jsonify
from datetime import date
import json

# Display all rows and columns
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)

# Database connection
engine = create_engine('postgresql://postgres:anirudh9@localhost:5432/postgres')

# Create Flask app
app = Flask(__name__)

@app.route('/api/stock/load', methods=['POST'])
def load_stock_data():
    """
    Load stock data from Yahoo Finance and save to database
    
    Expected JSON payload:
    {
        "ticker": "TSLA",
        "start_date": "2010-06-29",
        "end_date": "2023-06-24"
    }
    
    If data already exists in the database for the requested ticker and date range,
    it will be returned without fetching from Yahoo Finance.
    """
    try:
        # Get data from request
        data = request.get_json()
        ticker = data.get('ticker', 'TSLA')
        start_date = data.get('start_date', '2010-06-29')
        end_date = data.get('end_date', date.today().strftime("%Y-%m-%d"))
        
        # Validate inputs
        if not ticker:
            return jsonify({
                'success': False,
                'message': 'Please provide a valid ticker symbol'
            }), 400
        
        # Create a unique table name based on the ticker
        table_name = f"{ticker.lower()}_data"
        
        # Check if table exists
        query = f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = '{table_name}'
        );
        """
        exists = pd.read_sql_query(query, engine).iloc[0, 0]
        
        # If table exists, check if it has data for the requested date range
        if exists:
            # Get min and max dates from the existing data
            date_query = f"""
            SELECT MIN(\"Date\") as min_date, MAX(\"Date\") as max_date 
            FROM {table_name};
            """
            date_range = pd.read_sql_query(date_query, engine)
            db_min_date = date_range['min_date'][0].strftime('%Y-%m-%d')
            db_max_date = date_range['max_date'][0].strftime('%Y-%m-%d')
            
            # Convert input dates to datetime for comparison
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            db_min_dt = pd.to_datetime(db_min_date)
            db_max_dt = pd.to_datetime(db_max_date)
            
            # Check if requested date range is within existing data
            if start_dt >= db_min_dt and end_dt <= db_max_dt:
                # Data already exists, retrieve it from database
                query = f"""
                SELECT * FROM {table_name}
                WHERE \"Date\" BETWEEN '{start_date}' AND '{end_date}';
                """
                df2 = pd.read_sql_query(query, engine)
                
                # If we got data back, return it
                if not df2.empty:
                    df2['date'] = pd.to_datetime(df2['Date'])  # Align with SQL column
                    df2.drop(columns=['Date'], inplace=True)
                    
                    # Get available years for the dropdown
                    available_years = sorted(df2['date'].dt.year.unique().tolist())
                    
                    # Convert DataFrame to JSON
                    df_json = df2.to_json(date_format='iso', orient='split')
                    
                    return jsonify({
                        'success': True,
                        'message': f'Data for {ticker.upper()} retrieved from database!',
                        'data': df_json,
                        'available_years': available_years,
                        'source': 'database'
                    })
        
        # If we get here, we need to download data from Yahoo Finance
        print(f"Downloading data for {ticker} from {start_date} to {end_date} from Yahoo Finance...")
        df = yf.download(ticker.upper(), start=start_date, end=end_date, auto_adjust=False)
        
        if df.empty:
            return jsonify({
                'success': False,
                'message': f'No data found for {ticker}. Please check the ticker symbol and date range.'
            }), 404
        
        # Process the data
        df.columns = df.columns.droplevel(1) if isinstance(df.columns, pd.MultiIndex) else df.columns
        df = df.reset_index()
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Determine if we should append or replace data
        if_exists_action = 'replace'
        if exists:
            # If table exists and we're adding new data, use append
            # This is a simplification - in a real app you might want to handle overlaps more carefully
            if start_dt < db_min_dt or end_dt > db_max_dt:
                if_exists_action = 'append'
                # In a more sophisticated version, you'd merge the datasets and handle duplicates
        
        # Save to CSV (optional)
        csv_filename = f"{ticker.lower()}_data.csv"
        df.to_csv(csv_filename, index=False)
        
        # Save to SQL
        df.to_sql(table_name, engine, if_exists=if_exists_action, index=False)
        
        # If we appended data, we need to remove duplicates
        if if_exists_action == 'append':
            # Use pandas to handle duplicates instead of raw SQL
            # Read all data
            all_data = pd.read_sql_query(f"SELECT * FROM {table_name};", engine)
            
            # Drop duplicates based on Date
            all_data_deduped = all_data.drop_duplicates(subset=['Date'])
            
            # Replace the table with deduplicated data
            all_data_deduped.to_sql(table_name, engine, if_exists='replace', index=False)
        
        # Read from SQL to verify
        query = f"SELECT * FROM {table_name};"
        df2 = pd.read_sql_query(query, engine)
        df2['date'] = pd.to_datetime(df2['Date'])  # Align with SQL column
        df2.drop(columns=['Date'], inplace=True)
        
        # Get available years for the dropdown
        available_years = sorted(df2['date'].dt.year.unique().tolist())
        
        # Convert DataFrame to JSON
        df_json = df2.to_json(date_format='iso', orient='split')
        
        return jsonify({
            'success': True,
            'message': f'Data for {ticker.upper()} loaded successfully from Yahoo Finance!',
            'data': df_json,
            'available_years': available_years,
            'source': 'yahoo_finance'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error loading data: {str(e)}'
        }), 500

@app.route('/api/stock/data/<ticker>', methods=['GET'])
def get_stock_data(ticker):
    """
    Get stock data from database
    """
    print("MY ticker is :", ticker)
    try:
        # Create a unique table name based on the ticker
        table_name = f"{ticker.lower()}_data"
        
        # Check if table exists
        query = f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = '{table_name}'
        );
        """
        exists = pd.read_sql_query(query, engine).iloc[0, 0]
        
        if not exists:
            return jsonify({
                'success': False,
                'message': f'No data found for {ticker}. Please load the data first.'
            }), 404
        
        # Read from SQL
        query = f"SELECT * FROM {table_name};"
        df = pd.read_sql_query(query, engine)
        df['date'] = pd.to_datetime(df['Date'])  # Align with SQL column
        df.drop(columns=['Date'], inplace=True)
        
        # Convert DataFrame to JSON
        df_json = df.to_json(date_format='iso', orient='split')
        
        # Get available years for the dropdown
        available_years = sorted(df['date'].dt.year.unique().tolist())
        
        return jsonify({
            'success': True,
            'data': df_json,
            'available_years': available_years,
            'source': 'database'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving data: {str(e)}'
        }), 500

@app.route('/api/stock/tables', methods=['GET'])
def get_available_tables():
    """
    Get list of available stock tables in the database
    """
    try:
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name LIKE '%_data';
        """
        tables = pd.read_sql_query(query, engine)
        
        # Extract ticker symbols from table names
        tickers = [table.replace('_data', '').upper() for table in tables['table_name']]
        
        return jsonify({
            'success': True,
            'tickers': tickers
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving tables: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Changed port to 5001 to avoid conflict with AirPlay