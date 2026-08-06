from flask import Flask, request, jsonify
from models import db, Expense, Category, User
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///expenses.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    print("Database and tables created successfully!")


@app.route("/")
def home():
    return {"message": "Smart Expense Tracker API is running"}


# ---------------- USER ROUTES (basic, for testing — real auth comes in Phase 4) ----------------

@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()

    if not data or not all(k in data for k in ["name", "email", "password"]):
        return jsonify({"error": "name, email, and password are required"}), 400

    existing = User.query.filter_by(email=data["email"]).first()
    if existing:
        return jsonify({"error": "Email already registered"}), 400

    hashed_password = generate_password_hash(data["password"])
    user = User(name=data["name"], email=data["email"], password=hashed_password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"id": user.id, "name": user.name, "email": user.email}), 201


@app.route("/users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify([{"id": u.id, "name": u.name, "email": u.email} for u in users]), 200


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "email and password are required"}), 400

    user = User.query.filter_by(email=data["email"]).first()

    if not user or not check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify({
        "message": "Login successful",
        "user": {"id": user.id, "name": user.name, "email": user.email}
    }), 200


# ---------------- CATEGORY ROUTES ----------------

@app.route("/categories", methods=["POST"])
def create_category():
    data = request.get_json()

    if not data or not data.get("name"):
        return jsonify({"error": "Category name is required"}), 400

    existing = Category.query.filter_by(name=data["name"]).first()
    if existing:
        return jsonify({"error": "Category already exists"}), 400

    category = Category(name=data["name"])
    db.session.add(category)
    db.session.commit()

    return jsonify({"id": category.id, "name": category.name}), 201


@app.route("/categories", methods=["GET"])
def get_categories():
    categories = Category.query.all()
    return jsonify([{"id": c.id, "name": c.name} for c in categories]), 200


# ---------------- EXPENSE ROUTES ----------------

@app.route("/expenses", methods=["POST"])
def create_expense():
    data = request.get_json()

    required_fields = ["amount", "user_id", "category_id"]
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "amount, user_id, and category_id are required"}), 400

    user = User.query.get(data["user_id"])
    category = Category.query.get(data["category_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404
    if not category:
        return jsonify({"error": "Category not found"}), 404

    expense_date = datetime.utcnow().date()
    if data.get("date"):
        expense_date = datetime.strptime(data["date"], "%Y-%m-%d").date()

    expense = Expense(
        amount=data["amount"],
        date=expense_date,
        note=data.get("note", ""),
        user_id=data["user_id"],
        category_id=data["category_id"],
    )

    db.session.add(expense)
    db.session.commit()

    return jsonify(expense.to_dict()), 201


@app.route("/expenses", methods=["GET"])
def get_expenses():
    query = Expense.query

    category_id = request.args.get("category_id")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if category_id:
        query = query.filter_by(category_id=category_id)
    if start_date:
        query = query.filter(Expense.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(Expense.date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    expenses = query.order_by(Expense.date.desc()).all()
    return jsonify([e.to_dict() for e in expenses]), 200


@app.route("/expenses/<int:expense_id>", methods=["GET"])
def get_expense(expense_id):
    expense = Expense.query.get(expense_id)
    if not expense:
        return jsonify({"error": "Expense not found"}), 404
    return jsonify(expense.to_dict()), 200


@app.route("/expenses/<int:expense_id>", methods=["PUT"])
def update_expense(expense_id):
    expense = Expense.query.get(expense_id)
    if not expense:
        return jsonify({"error": "Expense not found"}), 404

    data = request.get_json()

    if "amount" in data:
        expense.amount = data["amount"]
    if "note" in data:
        expense.note = data["note"]
    if "category_id" in data:
        category = Category.query.get(data["category_id"])
        if not category:
            return jsonify({"error": "Category not found"}), 404
        expense.category_id = data["category_id"]
    if "date" in data:
        expense.date = datetime.strptime(data["date"], "%Y-%m-%d").date()

    db.session.commit()
    return jsonify(expense.to_dict()), 200


@app.route("/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    expense = Expense.query.get(expense_id)
    if not expense:
        return jsonify({"error": "Expense not found"}), 404

    db.session.delete(expense)
    db.session.commit()
    return jsonify({"message": "Expense deleted successfully"}), 200


# ---------------- ANALYTICS / SUMMARY ROUTES ----------------

@app.route("/summary/<int:user_id>", methods=["GET"])
def get_summary(user_id):
    """
    Returns spending analytics for a user using Pandas:
    - total spend
    - category-wise breakdown
    - month-wise breakdown
    Optional query params: start_date, end_date (format YYYY-MM-DD)
    """
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    query = Expense.query.filter_by(user_id=user_id)

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if start_date:
        query = query.filter(Expense.date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(Expense.date <= datetime.strptime(end_date, "%Y-%m-%d").date())

    expenses = query.all()

    if not expenses:
        return jsonify({
            "total_spent": 0,
            "category_breakdown": {},
            "monthly_breakdown": {},
            "message": "No expenses found for this user in the given range"
        }), 200

    # Convert to a Pandas DataFrame for analysis
    data = [{
        "amount": e.amount,
        "date": e.date,
        "category": e.category.name if e.category else "Uncategorized"
    } for e in expenses]

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%Y-%m")

    total_spent = round(df["amount"].sum(), 2)

    category_breakdown = df.groupby("category")["amount"].sum().round(2).to_dict()

    monthly_breakdown = df.groupby("month")["amount"].sum().round(2).to_dict()

    top_category = df.groupby("category")["amount"].sum().idxmax()

    return jsonify({
        "total_spent": total_spent,
        "category_breakdown": category_breakdown,
        "monthly_breakdown": monthly_breakdown,
        "top_spending_category": top_category,
        "number_of_expenses": len(expenses)
    }), 200


if __name__ == "__main__":
    app.run(debug=True)