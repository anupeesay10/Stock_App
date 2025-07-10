Welcome to the Stock Application! 📈

This is a Dash application that allows users to input a stock by a ticker value and a date range to display four charts: Candlestick chart, trading volume, daily returns, and drawdowns.
The user has the option to choose between showing the charts for all years of the date range or the charts for a specific year. There is NO analysis for this project. This is solely an app 
that can displays the charts. 

The program consists of two files that interact with each other: "stock.py" and "stock_api.py". Below is the data flow diagram that shows how the two files interact with each other:

Data Flow:

[User Interface]
     ↓  ↑
     |  |
     |  | HTTP Requests/Responses
     |  |
     ↓  ↑
[stock.py - Dash App]
     ↓  ↑
     |  |
     |  | HTTP Requests/Responses (using requests library)
     |  |
     ↓  ↑
[stock_api.py - Flask API]
     ↓  ↑
     |  |
     |  | SQL Queries
     |  |
     ↓  ↑
[PostgreSQL Database]
     ↓  ↑
     |  |
     |  | API Calls (when needed)
     |  |
     ↓  ↑
[Yahoo Finance API]


