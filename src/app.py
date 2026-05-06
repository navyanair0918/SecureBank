from flask import Flask, jsonify, request
from flask_cors import CORS
from database import BankDatabase
from config import (
    APP_PORT,
    JWT_SECRET,
    JWT_ALGORITHM,
    DEBUG,
    CORS_ORIGINS,
    SENDGRID_API_KEY,
    SENDGRID_FROM_EMAIL,
)
import jwt
from functools import wraps
from datetime import datetime, timedelta
import json
from urllib import request as urllib_request
from urllib import error as urllib_error

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": CORS_ORIGINS.split(",")}})
db = BankDatabase()


def send_email_via_sendgrid(to_email, subject, html_content):
    """Send email using SendGrid from server side."""
    if not SENDGRID_API_KEY or not SENDGRID_FROM_EMAIL:
        return False, "SendGrid is not configured on backend."

    payload = {
        "personalizations": [
            {
                "to": [{"email": to_email}],
                "subject": subject
            }
        ],
        "from": {"email": SENDGRID_FROM_EMAIL},
        "content": [
            {
                "type": "text/html",
                "value": html_content
            }
        ]
    }

    req = urllib_request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib_request.urlopen(req, timeout=20) as response:
            if response.status in (200, 202):
                return True, "Email sent"
            return False, f"Unexpected SendGrid status: {response.status}"
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        return False, f"SendGrid HTTP {exc.code}: {detail}"
    except Exception as exc:
        return False, f"Email send failed: {str(exc)}"


def build_transaction_email_html(data):
    transaction_type = "Received" if data.get("type") == "credit" else "Sent"
    color = "#27ae60" if data.get("type") == "credit" else "#e74c3c"
    amount = data.get("amount", 0)
    timestamp = data.get("timestamp")
    if isinstance(timestamp, (int, float)):
        timestamp = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
    elif not timestamp:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    description = data.get("description") or "Payment"
    counterparty_upi = data.get("counterpartyUpi") or "-"
    reference_id = data.get("referenceId") or "N/A"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <title>Transaction Alert</title>
    </head>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0; font-size: 24px;">SecureBank</h1>
            <p style="margin: 8px 0 0 0; opacity: 0.9;">Transaction Notification</p>
        </div>
        <div style="background: white; border: 1px solid #e1e8ed; border-radius: 0 0 10px 10px; padding: 24px;">
            <h2 style="color: #2c3e50; margin-top: 0;">Transaction Details</h2>
            <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; margin: 16px 0;">
                <p><strong>Type:</strong> <span style="color: {color}; font-weight: bold;">{transaction_type}</span></p>
                <p><strong>Amount:</strong> <span style="color: {color}; font-weight: bold;">₹{amount}</span></p>
                <p><strong>Date:</strong> {timestamp}</p>
                <p><strong>Description:</strong> {description}</p>
                <p><strong>From / To UPI:</strong> {counterparty_upi}</p>
                <p><strong>Reference:</strong> {reference_id}</p>
            </div>
            <p style="color: #7f8c8d; font-size: 12px;">This is an automated SecureBank message.</p>
        </div>
    </body>
    </html>
    """

# ========== JWT Authentication ==========

def create_token(user_id):
    """Create JWT token"""
    payload = {
        "user_id": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return True, payload.get("user_id")
    except jwt.ExpiredSignatureError:
        return False, "Token expired"
    except jwt.InvalidTokenError:
        return False, "Invalid token"

def token_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Missing authorization token"}), 401
        
        # Remove 'Bearer ' prefix
        if token.startswith("Bearer "):
            token = token[7:]
        
        is_valid, result = verify_token(token)
        if not is_valid:
            return jsonify({"error": result}), 401
        
        kwargs["user_id"] = result
        return f(*args, **kwargs)
    return decorated

# ========== Health Check ==========

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "🏦 Virtual Banking System API",
        "version": "1.0.0",
        "endpoints": {
            "auth": {
                "register": "POST /auth/register",
                "login": "POST /auth/login"
            },
            "account": {
                "profile": "GET /account/profile",
                "balance": "GET /account/balance",
                "passbook": "GET /account/passbook"
            },
            "transfer": {
                "send": "POST /transfer/send",
                "request": "POST /transfer/request"
            }
        }
    })

# ========== Authentication Endpoints ==========

@app.route("/auth/register", methods=["POST"])
def register():
    """Register a new user"""
    data = request.get_json() or {}
    
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()
    
    if not all([username, email, password, full_name]):
        return jsonify({"error": "Missing required fields"}), 400
    
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    
    success, result = db.register_user(username, email, password, full_name)
    if success:
        return jsonify({
            "message": "User registered successfully",
            "data": result,
            "token": create_token(result["user_id"])
        }), 201
    else:
        return jsonify({"error": result}), 400

@app.route("/auth/login", methods=["POST"])
def login():
    """Login user"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    
    success, user_id = db.authenticate_user(username, password)
    if success:
        token = create_token(user_id)
        account = db.get_user_account(user_id)
        return jsonify({
            "message": "Login successful",
            "token": token,
            "account": account
        }), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

# ========== Account Endpoints ==========

@app.route("/account/profile", methods=["GET"])
@token_required
def get_profile(user_id):
    """Get user account profile"""
    account = db.get_user_account(user_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    
    return jsonify({
        "account_id": account["account_id"],
        "upi_id": account["upi_id"],
        "balance": round(account["balance"], 2),
        "account_type": account["account_type"]
    }), 200

@app.route("/account/balance", methods=["GET"])
@token_required
def get_balance(user_id):
    """Get account balance"""
    account = db.get_user_account(user_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    
    return jsonify({
        "balance": round(account["balance"], 2),
        "currency": "INR"
    }), 200

@app.route("/account/passbook", methods=["GET"])
@token_required
def get_passbook(user_id):
    """Get transaction history (passbook)"""
    account = db.get_user_account(user_id)
    if not account:
        return jsonify({"error": "Account not found"}), 404
    
    limit = request.args.get("limit", 50, type=int)
    transactions = db.get_transactions(account["account_id"])[:limit]
    
    return jsonify({
        "account_id": account["account_id"],
        "upi_id": account["upi_id"],
        "transactions_count": len(transactions),
        "transactions": transactions
    }), 200

# ========== Transfer Endpoints ==========

@app.route("/transfer/send", methods=["POST"])
@token_required
def send_money(user_id):
    """Transfer money to another account"""
    data = request.get_json() or {}
    
    to_upi = data.get("to_upi", "").strip()
    amount = data.get("amount", 0)
    description = data.get("description", "Payment").strip()
    
    if not to_upi or amount <= 0:
        return jsonify({"error": "Invalid UPI or amount"}), 400
    
    # Get sender's account
    from_account = db.get_user_account(user_id)
    if not from_account:
        return jsonify({"error": "Sender account not found"}), 404
    
    # Get receiver's account
    to_account = db.get_account_by_upi(to_upi)
    if not to_account:
        return jsonify({"error": "Receiver account not found"}), 404
    
    if from_account["account_id"] == to_account["account_id"]:
        return jsonify({"error": "Cannot transfer to same account"}), 400
    
    # Process transfer
    success, result = db.create_transaction(
        from_account["account_id"],
        to_account["account_id"],
        amount,
        description
    )
    
    if success:
        return jsonify({
            "message": "Transfer successful",
            "transaction": result,
            "new_balance": round(from_account["balance"] - amount, 2)
        }), 200
    else:
        return jsonify({"error": result}), 400

@app.route("/search/upi", methods=["GET"])
@token_required
def search_upi(user_id):
    """Search for a UPI ID"""
    upi_id = request.args.get("upi", "").strip()
    
    if not upi_id:
        return jsonify({"error": "UPI ID required"}), 400
    
    account = db.get_account_by_upi(upi_id)
    if account:
        return jsonify({
            "found": True,
            "upi_id": account["upi_id"],
            "account_id": account["account_id"]
        }), 200
    else:
        return jsonify({"found": False, "error": "UPI not found"}), 404

# ========== Notification Endpoints ==========

@app.route("/notifications/transaction-email", methods=["POST"])
def send_transaction_email_notification():
    """Send transaction email notification via SendGrid (server-side)."""
    data = request.get_json() or {}
    to_email = data.get("toEmail", "").strip()
    transaction_data = data.get("transactionData") or {}

    if not to_email:
        return jsonify({"error": "toEmail is required"}), 400

    if "amount" not in transaction_data:
        return jsonify({"error": "transactionData.amount is required"}), 400

    subject = f"SecureBank Transaction Alert - ₹{transaction_data.get('amount')}"
    html_body = build_transaction_email_html(transaction_data)

    success, message = send_email_via_sendgrid(to_email, subject, html_body)
    if success:
        return jsonify({"success": True, "message": message}), 200
    return jsonify({"success": False, "error": message}), 500

# ========== Error Handlers ==========

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    print(f"Starting Banking API on http://localhost:{APP_PORT}")
    print(f"Using SQL Database: {db.use_sql}")
    app.run(host="0.0.0.0", port=APP_PORT, debug=DEBUG)
