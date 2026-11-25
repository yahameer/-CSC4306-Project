import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from functools import wraps

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///clearance.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), nullable=False)
    matric = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(10), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="student", nullable=False)


class ClearanceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    session = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.String(500))
    status = db.Column(db.String(30), default="pending")
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class ClearanceStep(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("clearance_request.id"), nullable=False)
    office = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(30), default="pending")


class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


def get_user():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return None
    try:
        data = serializer.loads(token, max_age=86400)
        return db.session.get(User, data["user_id"])
    except (BadSignature, SignatureExpired, KeyError):
        return None


def login_required(role=None):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            user = get_user()
            if not user:
                return jsonify({"error": "Please log in"}), 401
            if role and user.role != role:
                return jsonify({"error": "Access denied"}), 403
            return function(user, *args, **kwargs)
        return wrapper
    return decorator


@app.route("/")
def home():
    return jsonify({"message": "Northwest University Student Clearance API is running"})


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    fullname = str(data.get("fullname", "")).strip()
    matric = str(data.get("matric", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    department = str(data.get("department", "")).strip()
    level = str(data.get("level", "")).strip()
    password = str(data.get("password", ""))

    if not all([fullname, matric, email, department, level, password]):
        return jsonify({"error": "All fields are required"}), 400

    if "@" not in email or len(password) < 8:
        return jsonify({"error": "Enter a valid email and a password of at least 8 characters"}), 400

    if User.query.filter_by(email=email).first() or User.query.filter_by(matric=matric).first():
        return jsonify({"error": "Email or matriculation number already registered"}), 409

    user = User(
        fullname=fullname,
        matric=matric,
        email=email,
        department=department,
        level=level,
        password=generate_password_hash(password),
        role="student"
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Registration successful"}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = serializer.dumps({"user_id": user.id})

    return jsonify({
        "message": "Login successful",
        "token": token,
        "role": user.role,
        "fullname": user.fullname
    })


@app.route("/api/profile", methods=["GET"])
@login_required()
def profile(user):
    return jsonify({
        "fullname": user.fullname,
        "matric": user.matric,
        "email": user.email,
        "department": user.department,
        "level": user.level,
        "role": user.role
    })


@app.route("/api/clearance", methods=["POST"])
@login_required()
def apply_clearance(user):
    data = request.get_json(silent=True) or {}
    session = str(data.get("session", "")).strip()
    reason = str(data.get("reason", "")).strip()

    if not session:
        return jsonify({"error": "Academic session is required"}), 400

    clearance = ClearanceRequest(
        user_id=user.id,
        session=session,
        reason=reason
    )

    db.session.add(clearance)
    db.session.flush()

    offices = ["Academic Department", "Library", "Bursary", "Student Affairs", "Faculty"]

    for office in offices:
        db.session.add(ClearanceStep(request_id=clearance.id, office=office))

    db.session.commit()

    return jsonify({
        "message": "Clearance application submitted",
        "application_id": clearance.id
    }), 201


@app.route("/api/dashboard", methods=["GET"])
@login_required()
def dashboard(user):
    applications = ClearanceRequest.query.filter_by(user_id=user.id).all()

    return jsonify({
        "student": user.fullname,
        "total": len(applications),
        "applications": [
            {
                "id": item.id,
                "session": item.session,
                "status": item.status
            }
            for item in applications
        ]
    })


@app.route("/api/admin/clearances", methods=["GET"])
@login_required(role="admin")
def admin_clearances(user):
    applications = ClearanceRequest.query.all()

    return jsonify([
        {
            "id": item.id,
            "student": item.user_id,
            "session": item.session,
            "status": item.status
        }
        for item in applications
    ])


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
