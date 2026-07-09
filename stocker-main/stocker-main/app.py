from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from functools import wraps
import boto3
import hashlib
import os
import uuid
import json
from datetime import datetime
from decimal import Decimal
from config.aws_config import AWS_REGION, DYNAMODB_TABLE_USERS, DYNAMODB_TABLE_PORTFOLIO, \
    DYNAMODB_TABLE_ORDERS, DYNAMODB_TABLE_STOCKS
from utils.stock_data import get_stock_price, get_market_data, search_stocks
from utils.helpers import decimal_to_float

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'stocker-secret-key-change-in-production')

# DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)


# ─── Auth Decorator ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ─── Auth Routes ──────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()

        if not all([username, email, password, full_name]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        table = dynamodb.Table(DYNAMODB_TABLE_USERS)

        # Check if email already exists
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('email').eq(email)
        )
        if response['Items']:
            flash('Email already registered.', 'danger')
            return render_template('register.html')

        user_id = str(uuid.uuid4())
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        table.put_item(Item={
            'UserID': user_id,
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'full_name': full_name,
            'balance': Decimal('100000.00'),  # Starting virtual balance: $1,00,000
            'role': 'user',
            'created_at': datetime.utcnow().isoformat(),
        })

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        table = dynamodb.Table(DYNAMODB_TABLE_USERS)
        response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('email').eq(email)
        )

        if not response['Items']:
            flash('Invalid credentials.', 'danger')
            return render_template('login.html')

        user = response['Items'][0]
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        if user['password_hash'] != password_hash:
            flash('Invalid credentials.', 'danger')
            return render_template('login.html')

        session['user_id'] = user['UserID']
        session['username'] = user['username']
        session['full_name'] = user['full_name']
        session['role'] = user.get('role', 'user')
        flash(f"Welcome back, {user['full_name']}!", 'success')
        return redirect(url_for('dashboard'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# ─── Dashboard ────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']

    # Fetch user info
    users_table = dynamodb.Table(DYNAMODB_TABLE_USERS)
    user = users_table.get_item(Key={'UserID': user_id}).get('Item', {})

    # Fetch portfolio
    portfolio_table = dynamodb.Table(DYNAMODB_TABLE_PORTFOLIO)
    portfolio_response = portfolio_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('UserID').eq(user_id)
    )
    holdings = portfolio_response.get('Items', [])

    # Enrich holdings with current prices
    total_invested = Decimal('0')
    total_current = Decimal('0')
    enriched_holdings = []

    for h in holdings:
        symbol = h['symbol']
        qty = int(h['quantity'])
        avg_price = float(h['avg_buy_price'])
        current_price = get_stock_price(symbol)
        current_val = current_price * qty
        invested_val = avg_price * qty
        pnl = current_val - invested_val
        pnl_pct = (pnl / invested_val * 100) if invested_val else 0

        enriched_holdings.append({
            'symbol': symbol,
            'company': h.get('company', symbol),
            'quantity': qty,
            'avg_buy_price': avg_price,
            'current_price': current_price,
            'current_value': current_val,
            'pnl': pnl,
            'pnl_pct': round(pnl_pct, 2),
        })

        total_invested += Decimal(str(invested_val))
        total_current += Decimal(str(current_val))

    # Recent orders
    orders_table = dynamodb.Table(DYNAMODB_TABLE_ORDERS)
    orders_response = orders_table.query(
        IndexName='UserID-index',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('UserID').eq(user_id),
        Limit=5,
        ScanIndexForward=False
    )
    recent_orders = orders_response.get('Items', [])

    balance = float(user.get('balance', 0))
    total_invested_f = float(total_invested)
    total_current_f = float(total_current)
    portfolio_pnl = total_current_f - total_invested_f
    portfolio_pnl_pct = (portfolio_pnl / total_invested_f * 100) if total_invested_f else 0

    # Market overview
    market_data = get_market_data()

    return render_template('dashboard.html',
                           user=user,
                           holdings=enriched_holdings,
                           recent_orders=recent_orders,
                           balance=balance,
                           total_invested=total_invested_f,
                           total_current=total_current_f,
                           portfolio_pnl=portfolio_pnl,
                           portfolio_pnl_pct=round(portfolio_pnl_pct, 2),
                           market_data=market_data)


# ─── Trade Routes ─────────────────────────────────────────────────────────────
@app.route('/trade')
@login_required
def trade():
    symbol = request.args.get('symbol', 'AAPL')
    stock_data = get_stock_price(symbol, full=True)
    user_id = session['user_id']

    users_table = dynamodb.Table(DYNAMODB_TABLE_USERS)
    user = users_table.get_item(Key={'UserID': user_id}).get('Item', {})

    portfolio_table = dynamodb.Table(DYNAMODB_TABLE_PORTFOLIO)
    try:
        holding = portfolio_table.get_item(
            Key={'UserID': user_id, 'symbol': symbol.upper()}
        ).get('Item', {})
    except Exception:
        holding = {}

    popular_stocks = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'NVDA', 'META', 'NFLX']

    return render_template('trade.html',
                           symbol=symbol.upper(),
                           stock_data=stock_data,
                           balance=float(user.get('balance', 0)),
                           holding=holding,
                           popular_stocks=popular_stocks)


@app.route('/execute_trade', methods=['POST'])
@login_required
def execute_trade():
    user_id = session['user_id']
    symbol = request.form.get('symbol', '').upper()
    action = request.form.get('action', '')  # 'buy' or 'sell'
    quantity = int(request.form.get('quantity', 0))

    if not symbol or action not in ('buy', 'sell') or quantity <= 0:
        flash('Invalid trade request.', 'danger')
        return redirect(url_for('trade', symbol=symbol))

    current_price = get_stock_price(symbol)
    total_cost = Decimal(str(current_price * quantity))

    users_table = dynamodb.Table(DYNAMODB_TABLE_USERS)
    user = users_table.get_item(Key={'UserID': user_id}).get('Item', {})
    balance = Decimal(str(user.get('balance', 0)))

    portfolio_table = dynamodb.Table(DYNAMODB_TABLE_PORTFOLIO)
    orders_table = dynamodb.Table(DYNAMODB_TABLE_ORDERS)

    if action == 'buy':
        if balance < total_cost:
            flash(f'Insufficient balance. You need ${total_cost:.2f} but have ${float(balance):.2f}.', 'danger')
            return redirect(url_for('trade', symbol=symbol))

        # Deduct balance
        users_table.update_item(
            Key={'UserID': user_id},
            UpdateExpression='SET balance = balance - :cost',
            ExpressionAttributeValues={':cost': total_cost}
        )

        # Update portfolio
        try:
            existing = portfolio_table.get_item(
                Key={'UserID': user_id, 'symbol': symbol}
            ).get('Item')
        except Exception:
            existing = None

        if existing:
            old_qty = int(existing['quantity'])
            old_avg = float(existing['avg_buy_price'])
            new_qty = old_qty + quantity
            new_avg = ((old_avg * old_qty) + (current_price * quantity)) / new_qty
            portfolio_table.update_item(
                Key={'UserID': user_id, 'symbol': symbol},
                UpdateExpression='SET quantity = :q, avg_buy_price = :ap',
                ExpressionAttributeValues={
                    ':q': new_qty,
                    ':ap': Decimal(str(round(new_avg, 4)))
                }
            )
        else:
            portfolio_table.put_item(Item={
                'UserID': user_id,
                'symbol': symbol,
                'quantity': quantity,
                'avg_buy_price': Decimal(str(current_price)),
                'company': symbol,
            })

        flash(f'✅ Bought {quantity} shares of {symbol} @ ${current_price:.2f}', 'success')

    elif action == 'sell':
        try:
            existing = portfolio_table.get_item(
                Key={'UserID': user_id, 'symbol': symbol}
            ).get('Item')
        except Exception:
            existing = None

        if not existing or int(existing['quantity']) < quantity:
            flash(f'Insufficient shares. You own {int(existing["quantity"]) if existing else 0} shares.', 'danger')
            return redirect(url_for('trade', symbol=symbol))

        # Add balance
        users_table.update_item(
            Key={'UserID': user_id},
            UpdateExpression='SET balance = balance + :proceeds',
            ExpressionAttributeValues={':proceeds': total_cost}
        )

        # Update portfolio
        new_qty = int(existing['quantity']) - quantity
        if new_qty == 0:
            portfolio_table.delete_item(Key={'UserID': user_id, 'symbol': symbol})
        else:
            portfolio_table.update_item(
                Key={'UserID': user_id, 'symbol': symbol},
                UpdateExpression='SET quantity = :q',
                ExpressionAttributeValues={':q': new_qty}
            )

        flash(f'✅ Sold {quantity} shares of {symbol} @ ${current_price:.2f}', 'success')

    # Record order
    orders_table.put_item(Item={
        'OrderID': str(uuid.uuid4()),
        'UserID': user_id,
        'symbol': symbol,
        'action': action,
        'quantity': quantity,
        'price': Decimal(str(current_price)),
        'total': total_cost,
        'status': 'executed',
        'timestamp': datetime.utcnow().isoformat(),
    })

    return redirect(url_for('trade', symbol=symbol))


# ─── Portfolio ────────────────────────────────────────────────────────────────
@app.route('/portfolio')
@login_required
def portfolio():
    user_id = session['user_id']

    portfolio_table = dynamodb.Table(DYNAMODB_TABLE_PORTFOLIO)
    response = portfolio_table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key('UserID').eq(user_id)
    )
    holdings = response.get('Items', [])

    enriched = []
    total_invested = 0
    total_current = 0

    for h in holdings:
        symbol = h['symbol']
        qty = int(h['quantity'])
        avg_price = float(h['avg_buy_price'])
        current_price = get_stock_price(symbol)
        current_val = current_price * qty
        invested_val = avg_price * qty
        pnl = current_val - invested_val
        pnl_pct = (pnl / invested_val * 100) if invested_val else 0

        enriched.append({
            'symbol': symbol,
            'company': h.get('company', symbol),
            'quantity': qty,
            'avg_buy_price': avg_price,
            'current_price': current_price,
            'current_value': current_val,
            'invested_value': invested_val,
            'pnl': pnl,
            'pnl_pct': round(pnl_pct, 2),
        })
        total_invested += invested_val
        total_current += current_val

    users_table = dynamodb.Table(DYNAMODB_TABLE_USERS)
    user = users_table.get_item(Key={'UserID': user_id}).get('Item', {})

    return render_template('portfolio.html',
                           holdings=enriched,
                           total_invested=total_invested,
                           total_current=total_current,
                           total_pnl=total_current - total_invested,
                           balance=float(user.get('balance', 0)))


# ─── Transaction History ──────────────────────────────────────────────────────
@app.route('/history')
@login_required
def history():
    user_id = session['user_id']
    orders_table = dynamodb.Table(DYNAMODB_TABLE_ORDERS)
    response = orders_table.query(
        IndexName='UserID-index',
        KeyConditionExpression=boto3.dynamodb.conditions.Key('UserID').eq(user_id),
        ScanIndexForward=False
    )
    orders = response.get('Items', [])
    for o in orders:
        o['price'] = float(o.get('price', 0))
        o['total'] = float(o.get('total', 0))

    return render_template('history.html', orders=orders)


# ─── Market/Search API ────────────────────────────────────────────────────────
@app.route('/api/stock/<symbol>')
@login_required
def api_stock(symbol):
    data = get_stock_price(symbol.upper(), full=True)
    return jsonify(data)


@app.route('/api/search')
@login_required
def api_search():
    q = request.args.get('q', '')
    results = search_stocks(q)
    return jsonify(results)


@app.route('/market')
@login_required
def market():
    market_data = get_market_data()
    return render_template('market.html', market_data=market_data)


# ─── Profile ──────────────────────────────────────────────────────────────────
@app.route('/profile')
@login_required
def profile():
    user_id = session['user_id']
    users_table = dynamodb.Table(DYNAMODB_TABLE_USERS)
    user = users_table.get_item(Key={'UserID': user_id}).get('Item', {})
    user['balance'] = float(user.get('balance', 0))
    return render_template('profile.html', user=user)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
