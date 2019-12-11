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
server = Flask(__name__)

# Load extensions here for now
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt(server)

from flask_login import LoginManager
login_manager = LoginManager(server)
login_manager.login_view = "login"

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(server)

# CSS
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', '/static/main.css']

# Setting up dash applications
dash_app1 = Dash(__name__, server = server, url_base_pathname='/leaderboard/', external_stylesheets=external_stylesheets )
dash_app2 = Dash(__name__, server = server, url_base_pathname='/orderbook/', external_stylesheets=external_stylesheets )

from flask import render_template, redirect, url_for, request, jsonify
from flask_login import login_user, login_required, current_user, logout_user

from forms import UserPasswordForm



@server.route('/login', methods=['GET', 'POST'])
def login():
  """Login user if not already logged in."""
  form = UserPasswordForm()
  if form.validate_on_submit():
        # For convenience we create users while they login
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if user.is_correct_password(form.password.data):
                login_user(user)
                user.last_login = datetime.datetime.now()
                db.session.commit()
                return redirect(url_for('index'))
            return redirect(url_for('login'))
        # Create new user
        user = User(username=form.username.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('index'))
  return render_template('login.html', form=form)


@server.route('/')
@login_required
def index():
  """Index page."""
  return render_template('index.html')


def reset_account():
    """Reset current active account."""
    # Delete user orders
    Order.query.filter_by(user_id=current_user.id).delete()
    # Reset balance
    current_user.balance = 0
    db.session.commit()
    app.logger.info("Reset user: %s", current_user.username)
    return redirect(url_for('index'))

def delete_account():
    """Delete current active account."""
    user = User.query.get(current_user.id)
    logout_user()
    db.session.delete(user)
    db.session.commit()
    server.logger.info("Delete user: %s", user.username)
    return redirect(url_for('login'))

def account_handler(action):
    """Handle account actions."""
    form = UserPasswordForm()
    if form.validate_on_submit():
        # Check username and password again
        if (form.username.data == current_user.username and
            current_user.is_correct_password(form.password.data)):
            # Perform requests account action
            if action == "account_reset":
                return reset_account()
            if action == "account_delete":
                return delete_account()
        return redirect(url_for(action))
    return render_template('account.html', form=form,
                            form_header=action.replace('_', ' ').title())

@server.route('/account_reset', methods=['GET', 'POST'])
@login_required
def account_reset():
    """Handler for account reset."""
    return account_handler("account_reset")

@server.route('/account_delete', methods=['GET', 'POST'])
@login_required
def account_delete():
    """Handler for account delete."""
    return account_handler("account_delete")

@server.route('/logout')
def logout():
    """Logout and redirect user."""
    logout_user()
    return redirect(url_for('login'))

# Plotly Applications

@server.route('/leaderboard')
def render_dashboard():
    return redirect('/dash1')

@server.route('/orderbook')
def render_dashboard2():
    return redirect('/dash2')

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