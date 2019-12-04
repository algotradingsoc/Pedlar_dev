# Setting up multiple apps
from dash import Dash
from werkzeug.wsgi import DispatcherMiddleware
import flask
from werkzeug.serving import run_simple
# Dash application
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

import plotly.graph_objs as go

import pandas as pd

# Prepare static data to load into application
# Realtime data please refer to https://dash.plot.ly/live-updates
# Iframe https://community.plot.ly/t/embedding-dash-into-webpage/10645/3

# cavity,clashdiff,hbond,localclash,sbond,sbridge,Mean,SD

# CSS
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css',
        '/static/main.css']

# Setting up flask server and dash applications
server = flask.Flask(__name__)
dash_app1 = Dash(__name__, server = server, url_base_pathname='/leaderboard', external_stylesheets=external_stylesheets )
dash_app2 = Dash(__name__, server = server, url_base_pathname='/orderbook', external_stylesheets=external_stylesheets )



# Setting up the Flask server and applications

@server.route('/')
def homepage():
    return flask.render_template('homepage.html')

@server.route('/overview')
def overview():
    return flask.render_template('overview.html')

# Plotly Applications

@server.route('/leaderboard')
def render_dashboard():
    return flask.redirect('/dash1')

@server.route('/orderbook')
def render_dashboard2():
    return flask.redirect('/dash2')


# Linking diffrent application

app = DispatcherMiddleware(server, {
    '/dash1': dash_app1.server,
    '/dash2': dash_app2.server,
})

if __name__ == "__main__":
    live = False
    if live:
        run_simple('127.0.0.1', 20200, app, use_reloader=False, use_debugger=True)
    else:
        run_simple('127.0.0.1', 20200, app, use_reloader=False, use_debugger=True)