from flask import Flask, render_template, request, redirect, url_for, jsonify  # For flask implementation
from pymongo import MongoClient
import os

app = Flask(__name__)

client = MongoClient("localhost") #host uri
db = client['Pedlar'] #Select the database


@app.route("/trade", methods=['POST'])
def add_trade_record():
    req_data = request.get_json()
    tradesession = 'Backtest_{}'.format(req_data.get('backtest_id', 0))
    usertrades = db[tradesession]
    usertrades.insert_one(req_data)
    return ('', 204)

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
        return jsonify(username=new_user_id, exist=exist, tradesession=tradesessionid)
    else:
        exist = True
        return jsonify(username=user, exist=exist, tradesession=tradesessionid)

@app.route("/tradesession", methods=['POST'])
def tradesession():
    req_data = request.get_json()
    user = req_data.get('user_id', 0)
    pnl = req_data.get('pnl', 0)
    # check if exist in Mongo 
    backtest_table = db['Backtests']
    existing_backtest_no = db['Backtests'].count()
    tradesessionid = existing_backtest_no + 1
    # generate tradesession code 
    backtest_table.insert_one({'user_id':user, 'pnl':pnl, 'backtest_id':tradesessionid})
    return jsonify(username=user, tradesession=tradesessionid)


if __name__ == "__main__":
    app.run()