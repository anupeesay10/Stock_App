## Welcome to the Stock Application! 💰📈

This is a Dash application that allows users to input a stock by a ticker value and a date range to display four charts: Candlestick chart, trading volume, daily returns, and drawdowns.
The user has the option to choose between showing the charts for all years of the date range or the charts for a specific year. There is NO analysis for this project. This is solely an app 
that can displays the charts. 

The program consists of two files that interact with each other: "stock.py" and "stock_api.py". Below is the data flow diagram that shows how the two files interact with each other:

# Data Flow:



<img width="418" height="500" alt="stock_data_flow_2" src="https://github.com/user-attachments/assets/996f939f-6197-4f33-b2db-cc3e52bed24b" />


"stock.py" is the frontend Dash application and "stock_api.py"
is the backend Flask API. If the data given by the ticker and date 
range values are valid and correspond to existing data within the database, 
the existing data is used to create and display the charts. Otherwise, the data is retrieved from Yahoo Finance using yfinance library.
The new data that is retrieved is then stored in the database for any future use. 

# To view this project:
1. Clone the repository
2. Open the project in an IDE of your choice
3. Open and run "stock.py"

**Important Note:** Any .csv files in this repository are data retrieved from Yahoo Finance from prior use that were also stored into a .csv file along with in the database. They do **NOT** affect the application from running normally.

# I hope you enjoy this application! 
