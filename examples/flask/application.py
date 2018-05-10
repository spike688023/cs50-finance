import os
import datetime
from time import strftime

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Ensure environment variable is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():

    # get user info
    row = db.execute("SELECT * FROM users WHERE id = :user_id",
                     user_id=session["user_id"])

    cash = row[0]["cash"]
    username = row[0]["username"]

    """Show portfolio of stocks"""
    transitions = []
    all = db.execute("SELECT * FROM :username", username=username)

    for i in all:
        transitions.append((i["stockname"], usd(i["price"]), i["quantity"], usd(i["total"])))

    return render_template("index.html", transitions=transitions, cash=usd(cash)), 200


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    feedback = {}
    shares = request.form.get("shares")
    symbol = request.form.get("symbol")
    user_id = session["user_id"]
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not symbol:
            return apology("missing symbol", 400)

        # Ensure username was submitted
        if not shares:
            return apology("missing shares", 400)

        if not str(shares).isnumeric():
            return apology("must be postive interger", 400)

        # stock exist or not
        if lookup(symbol) == None:
            return apology("non exist", 400)

        else:
            feedback = lookup(symbol)

        # create table test
        # it works
        db.execute("CREATE TABLE IF NOT EXISTS history (id integer, stockname text, price real, quantity integer,dt datetime)")

        # get user info
        row = db.execute("SELECT * FROM users WHERE id = :user_id",
                         user_id=user_id)

        cash = row[0]["cash"]
        username = row[0]["username"]
        price = feedback["price"]

        cash = cash - (feedback["price"] * int(shares))
        if cash < 0:
            return apology("not enough money", 400)

        session["cash"] = cash

        db.execute("UPDATE users SET cash = :cash WHERE id = :id",
                   cash=cash, id=user_id)

        # Query database for username
        db.execute("INSERT INTO history (id, stockname, price, quantity, dt) VALUES (:id, :stockname, :price, :quantity, :dt)",
                   id=user_id, stockname=symbol, price=price, quantity=shares, dt=datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S'))

        # get data from user's table and to update it.
        look = db.execute("SELECT * FROM :username WHERE stockname = :stockname",
                          username=username, stockname=symbol)

        if look == []:
            # insert
            db.execute("INSERT INTO :username (stockname, price, quantity, total) VALUES (:stockname, :price, :quantity, :total)",
                       username=username, stockname=symbol, price=price, quantity=shares, total=price * int(shares))
        else:
            # take data out and update it
            shares = int(shares) + look[0]["quantity"]
            total = int(shares) * price
            db.execute("UPDATE :username SET quantity = :shares WHERE stockname = :stockname",
                       username=username, shares=shares, stockname=symbol)

            db.execute("UPDATE :username SET total = :total WHERE stockname = :stockname",
                       username=username, total=total, stockname=symbol)

        session["status"] = "Bought!!"
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = []
    all = db.execute("SELECT * FROM history WHERE id=:id", id=session["user_id"])

    for i in all:
        transactions.append((i["stockname"].upper(), i["quantity"], usd(i["price"]), i["dt"]))

    session["status"] = ""
    return render_template("history.html", transactions=transactions, status="")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]
        session["cash"] = rows[0]["cash"]
        session["status"] = "Welcome!!"

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("symbol"):
            return apology("missing symbol", 400)

        if lookup(request.form.get("symbol")) == None:
            return apology("username taken", 400)

        else:
            feedback = lookup(request.form.get("symbol"))
            session["status"] = ""
            return render_template("quoted.html", price=usd(feedback["price"]), stockname=feedback["symbol"])

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    username = request.form.get("username")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not username:
            return apology("must provide username")

        # Ensure password was submitted
        elif not password:
            return apology("must provide password")

        # Ensure password (again) was submitted
        elif not confirmation:
            return apology("must provide password (again)")

        # password was not matched
        if password != confirmation:
            return apology("passwords don't match")

        # Query database for username
        feedback = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                              username=username, hash=generate_password_hash(password))

        if feedback == None:
            return apology("username taken")
            #
        else:
            session["user_id"] = feedback
            session["cash"] = 10000.00
            session["username"] = username
        # Remember which user has logged in

        # everyone has its private data about stock
        db.execute("CREATE TABLE IF NOT EXISTS :username (stockname text, price real, quantity integer, total real)",
                   username=username)

        session["status"] = "Registered!!"

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html"), 200


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    symbol = request.form.get("symbol")
    shares = request.form.get("shares")
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not symbol:
            return apology("missing symbol", 400)

        # Ensure password was submitted
        elif not shares:
            return apology("missing shares", 400)

        row = db.execute("SELECT * FROM :username WHERE stockname=:symbol", username=session["username"], symbol=symbol.lower())

        if row == []:
            return apology("no stock can sell", 400)

        if not str(shares).isnumeric():
            return apology("must be postive interger", 400)

        quantity = row[0]["quantity"]
        price = row[0]["price"]
        diff = quantity - int(shares)

        if quantity < int(shares):
            return apology("not enough shares", 400)

        if quantity > int(shares):
            # update quantity
            db.execute("UPDATE :username SET quantity = :shares WHERE stockname = :symbol",
                       username=session["username"], shares=quantity - int(shares), symbol=symbol.lower())

            # update total
            db.execute("UPDATE :username SET total = :total WHERE stockname = :symbol",
                       username=session["username"], total=(diff * price), symbol=symbol.lower())

        elif quantity == int(shares):
            db.execute("DELETE FROM :username WHERE stockname = :symbol",
                       username=session["username"], symbol=symbol.lower())

        # update cash
        db.execute("UPDATE users SET cash = :cash WHERE id = :user_id",
                   cash=session["cash"] + (int(shares) * price), user_id=session["user_id"])

        db.execute("INSERT INTO history (id, stockname, price, quantity, dt) VALUES (:id, :stockname, :price, :quantity, :dt)",
                   id=session["user_id"], stockname=symbol, price=price, quantity=int(shares) * -1, dt=datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S'))

        session["cash"] = session["cash"] + (int(shares) * price)

        session["status"] = "Sold!!"
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        raw = db.execute("SELECT stockname FROM :username", username=session['username'])
        items = [(i["stockname"]).upper() for i in raw]
        return render_template("sell.html", items=items)


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
