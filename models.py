from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # store a hashed password, never plain text

    expenses = db.relationship("Expense", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.email}>"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    expenses = db.relationship("Expense", backref="category", lazy=True)

    def __repr__(self):
        return f"<Category {self.name}>"


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow)
    note = db.Column(db.String(255), nullable=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    def __repr__(self):
        return f"<Expense {self.amount} on {self.date}>"

    def to_dict(self):
        """Convert an Expense object into a JSON-friendly dictionary for API responses."""
        return {
            "id": self.id,
            "amount": self.amount,
            "date": self.date.strftime("%Y-%m-%d") if self.date else None,
            "note": self.note,
            "category": self.category.name if self.category else None,
            "user_id": self.user_id,
        }
