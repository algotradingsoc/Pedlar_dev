"""pedlarweb entry point."""

import datetime 

# Setting up multiple apps
from dash import Dash
from werkzeug.wsgi import DispatcherMiddleware
from flask import Flask, render_template, redirect, url_for, request, jsonify
from werkzeug.serving import run_simple


# Dash application
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output


# Setting up flask server 
server = Flask(__name__,instance_relative_config=True)
# Load configuration
server.config.from_pyfile('config.py')

# CSS
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', '/static/main.css']

# Setting up dash applications
dash_app1 = Dash(__name__, server = server, url_base_pathname='/leaderboard/', external_stylesheets=external_stylesheets )
dash_app2 = Dash(__name__, server = server, url_base_pathname='/orderbook/', external_stylesheets=external_stylesheets )

from flask import render_template, redirect, url_for, request, jsonify

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


# Dash samples 

dash_app1.layout = html.Div(children=[
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

dash_app2.layout = html.Div(children=[
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
})

if __name__ == "__main__":
    live = False
    if live:
        run_simple('127.0.0.1', 5000, app, use_reloader=False, use_debugger=True)
    else:
        run_simple('127.0.0.1', 5000, app, use_reloader=False, use_debugger=True)