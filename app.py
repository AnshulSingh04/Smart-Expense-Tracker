from flask import Flask
from models import db

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


if __name__ == "__main__":
    app.run(debug=True)
