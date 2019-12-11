from flask import Flask, render_template, request, redirect, url_for, jsonify  # For flask implementation
from pymongo import MongoClient
import os

app = Flask(__name__)

client = MongoClient("localhost") #host uri
db = client['Pedlar'] #Select the database

# create new backtest record 

@app.route("/user", methods=['POST'])
def user_record():
    req_data = request.get_json()
    user = req_data.get('user', 0)
    agent = req_data.get('agent', 'sample')
    # check if exist in Mongo 
    usertable = db['Users']
    existing_user_no = db['Users'].count()
    new_user_id = existing_user_no + 1
    targetuser = usertable.find_one({'user_id':user})
    # create new tradesession id
    backtest_table = db['Backtests']
    existing_backtest_no = db['Backtests'].count()
    tradesessionid = existing_backtest_no + 1
    if targetuser is None:
        exist = False
        usertable.insert_one({'user_id': new_user_id})
        backtest_table.insert_one({'user_id':new_user_id, 'agent':agent, 'backtest_id':tradesessionid})
        return jsonify(username=new_user_id, exist=exist, tradesession=tradesessionid)
    else:
        exist = True
        backtest_table.insert_one({'user_id':user, 'agent':agent, 'backtest_id':tradesessionid})
        return jsonify(username=user, exist=exist, tradesession=tradesessionid)

# update leaderboard after backtest 
@app.route("/tradesession", methods=['POST'])
def tradesession():
    req_data = request.get_json()
    user = req_data.get('user_id', 0)
    agent = req_data.get('agent', 'sample')
    tradesessionid = req_data.get('tradesession', 0)
    pnl = req_data.get('pnl', -10000)
    sharpe = req_data.get('sharpe', -100)
    # Add to leaderboard table 
    leaderboard = db['Leaderboard']
    leaderboard.insert_one({'user_id':user, 'agent':agent, 'backtest_id':tradesessionid, 'pnl':pnl, 'sharpe':sharpe})
    return jsonify(username=user, tradesession=tradesessionid)

@app.route("/trade", methods=['POST'])
def add_portfolio_record():
    req_data = request.get_json()
    tradesession = 'Backtest_{}'.format(req_data.get('backtest_id', 0))
    usertrades = db[tradesession]
    usertrades.insert_one(req_data)
    return ('', 204)



if __name__ == "__main__":
    app.run()