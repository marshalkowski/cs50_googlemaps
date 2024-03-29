import os
import re
from flask import Flask, jsonify, render_template, request

from cs50 import SQL
from helpers import lookup

# Configure application
app = Flask(__name__)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///mashup.db")


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    """Render map"""
    if not os.environ.get("API_KEY"):
        raise RuntimeError("API_KEY not set")
    return render_template("index.html", key=os.environ.get("API_KEY"))


@app.route("/articles")
def articles():
    # Ensure paramaters are present
    if not request.args.get("geo"):
        raise RuntimeError("missing geo")

    #ensure parameter is zip code
    if not re.search("^-?\d\d\d\d\d$", request.args.get("geo")):
        raise RuntimeError("invalid geo")

    results = lookup(request.args.get("geo"))

    # TODO
    return jsonify(results)


@app.route("/search")
def search():
    if re.search("^-?\w*\s*\w*,\s?\w*\s*\w*?$", request.args.get("q")):
        r, s = request.args.get("q").split(",")
        r = r.strip() + "%"
        s = s.strip() + "%"
        locs = db.execute("SELECT * FROM places WHERE (place_name LIKE :r) AND (admin_name1 LIKE :s OR admin_code1 LIKE :s)", r=r, s=s)
        return jsonify(locs)
    elif re.search("^-?\w*\s*\w*,\s*\w*\s*\w*,\s*\w*$", request.args.get("q")):
        r, s, t = request.args.get("q").split(",")
        r = r.strip() + "%"
        s = s.strip() + "%"
        t = t.strip() + "%"
        locs = db.execute("SELECT * FROM places WHERE (place_name LIKE :r) AND (admin_name1 LIKE :s OR admin_code1 LIKE :s) AND (country_code LIKE :t)", r=r, s=s, t=t)
        return jsonify(locs)
    q = request.args.get("q") + "%"
    locs = db.execute("SELECT * FROM places WHERE postal_code LIKE :q OR place_name LIKE :q", q=q)
    return jsonify(locs)


@app.route("/update")
def update():
    """Find up to 10 places within view"""

    # Ensure parameters are present
    if not request.args.get("sw"):
        raise RuntimeError("missing sw")
    if not request.args.get("ne"):
        raise RuntimeError("missing ne")

    # Ensure parameters are in lat,lng format
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("sw")):
        raise RuntimeError("invalid sw")
    if not re.search("^-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?$", request.args.get("ne")):
        raise RuntimeError("invalid ne")

    # Explode southwest corner into two variables
    sw_lat, sw_lng = map(float, request.args.get("sw").split(","))

    # Explode northeast corner into two variables
    ne_lat, ne_lng = map(float, request.args.get("ne").split(","))

    # Find 10 cities within view, pseudorandomly chosen if more within view
    if sw_lng <= ne_lng:

        # Doesn't cross the antimeridian
        rows = db.execute("""SELECT * FROM places
                          WHERE :sw_lat <= latitude AND latitude <= :ne_lat AND (:sw_lng <= longitude AND longitude <= :ne_lng)
                          GROUP BY country_code, place_name, admin_code1
                          ORDER BY RANDOM()
                          LIMIT 10""",
                          sw_lat=sw_lat, ne_lat=ne_lat, sw_lng=sw_lng, ne_lng=ne_lng)

    else:

        # Crosses the antimeridian
        rows = db.execute("""SELECT * FROM places
                          WHERE :sw_lat <= latitude AND latitude <= :ne_lat AND (:sw_lng <= longitude OR longitude <= :ne_lng)
                          GROUP BY country_code, place_name, admin_code1
                          ORDER BY RANDOM()
                          LIMIT 10""",
                          sw_lat=sw_lat, ne_lat=ne_lat, sw_lng=sw_lng, ne_lng=ne_lng)

    # Output places as JSON
    return jsonify(rows)
