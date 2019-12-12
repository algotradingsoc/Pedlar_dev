"""pedlarweb entry point."""

import datetime 
import pandas as pd 

# Setting up multiple apps
from dash import Dash
from werkzeug.wsgi import DispatcherMiddleware
from flask import Flask, render_template, redirect, url_for, request, jsonify
from werkzeug.serving import run_simple
from flask import render_template, redirect, url_for, request, jsonify

# Dash application
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input,Output 
import dash_table

# datafeed functions 
import sys, os
sys.path.append(os.path.join(os.path.dirname(sys.path[0]),'pedlar'))
import pedlar.iex,pedlar.truefx

# database
# TO-DO push password to env var 
import pymongo 



# Setting up flask server 
server = Flask(__name__,instance_relative_config=True)
# Load configuration
server.config.from_pyfile('config.py')

# CSS
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', '/static/main.css']

# Setting up dash applications
dash_app1 = Dash(__name__, server = server, url_base_pathname='/leaderboard/', external_stylesheets=external_stylesheets )
dash_app2 = Dash(__name__, server = server, url_base_pathname='/orderbook/', external_stylesheets=external_stylesheets )
dash_app3 = Dash(__name__, server = server, url_base_pathname='/sample/', external_stylesheets=external_stylesheets )


# mongo functions 
def mongo2df(client,dbname,collectionname):
    
    db = client.get_database(dbname)
    df = pd.DataFrame(list(db[collectionname].find({})))
    try:
        df.drop(['_id'], axis=1,inplace=True)
        df.drop_duplicates(keep='last', inplace=True)
    except:
        print('Record not found',collectionname)
    client.close()
    return df 

@server.route('/')
def main_page():
    return render_template('index.html')


# Plotly Applications

@server.route('/leaderboard')
def render_dashboard():
    return redirect('/dash1')

@server.route('/orderbook')
def render_dashboard2():
    return redirect('/dash2')

@server.route('/sample')
def render_dashboard3():
    return redirect('/dash3')


# Dash samples 



dash_app1.layout = html.Div(children=[
    html.Div(id='leaderboard-header'),
    dash_table.DataTable(
    id='leaderboard',
    columns=[],
    ),
    dcc.Interval(
        id='interval-leaderboard',
        interval=5*1000, # in milliseconds
        n_intervals=0
    )
])

@dash_app1.callback(Output('leaderboard-header', 'children'),
              [Input('interval-leaderboard', 'n_intervals')])
def update_leaderboard_header(n):
    now = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
    return [
        html.Span('Current Datetime: {}'.format(now))
    ]


@dash_app1.callback(Output('leaderboard', 'columns'),
              [Input('interval-leaderboard', 'n_intervals')])
def update_leaderboard(n):
    try:
        password = os.environ.get('algosocdbpw', 'algosocadmin')
        client = pymongo.MongoClient("mongodb+srv://algosocadmin:{}@icalgosoc-9xvha.mongodb.net/test?retryWrites=true&w=majority".format(password))
        data = mongo2df(client,'Pedlar_dev','Leaderboard')
        names = data.columns 
        return [{"name": i, "id": i} for i in names]
    except:
        return []

@dash_app1.callback(Output('leaderboard', 'data'),
              [Input('interval-leaderboard', 'n_intervals')])
def update_leaderboard_data(n):
    try:
        password = os.environ.get('algosocdbpw', 'algosocadmin')
        client = pymongo.MongoClient("mongodb+srv://algosocadmin:{}@icalgosoc-9xvha.mongodb.net/test?retryWrites=true&w=majority".format(password))
        data = mongo2df(client,'Pedlar_dev','Leaderboard')
        return data.to_dict('records')
    except:
        return []


dash_app2.layout = html.Div(children=[
    html.Span('Orderbook'),
    dash_table.DataTable(
    id='orderbook',
    columns=[],
    ),
    dcc.Interval(
        id='interval-orderbook',
        interval=2*1000, # in milliseconds
        n_intervals=0
    )
])


@dash_app2.callback(Output('orderbook', 'columns'),
              [Input('interval-orderbook', 'n_intervals')])
def update_orderbook(n):
    try:
        session, session_data, flag_parse_data, authrorize = truefx.config(api_format ='csv', flag_parse_data = True)
        truefxdata = truefx.read_tick(session, session_data, flag_parse_data, authrorize)
        names = truefxdata.columns 
        return [{"name": i, "id": i} for i in names]
    except:
        return []

@dash_app2.callback(Output('orderbook', 'data'),
              [Input('interval-orderbook', 'n_intervals')])
def update_orderbook_data(n):
    try:
        session, session_data, flag_parse_data, authrorize = truefx.config(api_format ='csv', flag_parse_data = True)
        truefxdata = truefx.read_tick(session, session_data, flag_parse_data, authrorize)
        df = truefxdata 
        return df.to_dict('records')
    except:
        return []



dash_app3.layout = html.Div(children=[
    html.H1(children='Hello Dash'),

    html.Div(children='''
        Dash: A web application framework for Python.
    '''),

    dcc.Graph(
        id='example-graph',
        figure={
            'data': [
                {'x': [1, 2, 3], 'y': [4, 1, 2], 'type': 'bar', 'name': 'SF'},
                {'x': [1, 2, 3], 'y': [2, 4, 5], 'type': 'bar', 'name': u'Montréal'},
            ],
            'layout': {
                'title': 'Dash Data Visualization'
            }
        }
    )
])



# Linking diffrent application

app = DispatcherMiddleware(server, {
    '/dash1': dash_app1.server,
    '/dash2': dash_app2.server,
    '/dash3': dash_app3.server,
})

if __name__ == "__main__":
    live = False
    if live:
        run_simple('127.0.0.1', 5000, app, use_reloader=False, use_debugger=True)
    else:
        run_simple('127.0.0.1', 5000, app, use_reloader=False, use_debugger=True)