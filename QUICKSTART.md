# 🚀 Quick Start Guide - Banking System

## Test It Right Now (5 minutes!)

### 1. Start the Backend

```powershell
cd Cloud-Based_Banking_System
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r src/requirements.txt
cd src
python app.py
```

You should see:
```
🚀 Starting Banking API on http://localhost:5000
📊 Using SQL Database: False
```

### 2. Open the Frontend

- **Option A (Browser):** Open `index.html` directly
- **Option B (HTTP Server):**
```powershell
python -m http.server 8000
# Visit http://localhost:8000
```

### 3. Login with Demo Account

```
Username: alice
Password: alice123
```

### 4. Try These Actions

✅ **View Balance** - See your ₹5000 balance  
✅ **Transfer Money** - Send ₹500 to `bob@bank`  
✅ **Check Passbook** - View your transaction history

---

## API Testing

### Register New User
```bash
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username":"john",
    "email":"john@bank.com",
    "password":"john123456",
    "full_name":"John Doe"
  }'
```

### Login
```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"alice123"}'
```

Response:
```json
{
  "message": "Login successful",
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "account": {
    "account_id": 1001,
    "upi_id": "alice@bank",
    "balance": 5000.0
  }
}
```

### Transfer Money
```bash
curl -X POST http://localhost:5000/transfer/send \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "to_upi":"bob@bank",
    "amount":500,
    "description":"Payment for dinner"
  }'
```

### View Passbook
```bash
curl -X GET http://localhost:5000/account/passbook \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Deploy to Azure (Step by Step)

### Step 1: Create Azure Resources
```powershell
.\deploy.ps1 -ResourceGroupName BankRG -Location eastus
```

When prompted, enter a secure SQL password (min 8 chars):
```
Example: MyP@ssw0rd123
```

**Wait 3-5 minutes** for resources to create...

### Step 2: Deploy Backend App
```powershell
# Get app service name from output
az webapp deployment source config-zip `
  --resource-group BankRG `
  --name banking-app-xxxxx `
  --src banking-app.zip
```

### Step 3: Update Frontend
Open `index.html` and update:
```javascript
// Line 1 (change this):
const API_URL = "https://banking-app-xxxxx.azurewebsites.net";
```

### Step 4: Access Online
Open `https://banking-app-xxxxx.azurewebsites.net` in your browser

---

## Troubleshooting

### Backend won't start?
```powershell
# Check Python version
python --version  # Need 3.10+

# Check dependencies
pip list | grep -E "flask|pyodbc|jwt|bcrypt"

# Reinstall
pip install --upgrade -r src/requirements.txt
```

### Port 5000 already in use?
```powershell
# Method 1: Change port in .env
APP_PORT=5001

# Method 2: Kill process using port 5000
Get-Process | Where-Object {$_.Name -eq "python"} | Stop-Process
```

### Frontend can't reach backend?
1. Check if backend is running: `http://localhost:5000`
2. Check CORS_ORIGINS in .env matches your frontend URL
3. Browser dev tools (F12) → Network tab for error details

### SQL Connection Error?
```powershell
# Check if using SQL
# If not needed for demo, keep USE_SQL=false

# For Azure SQL, verify:
# 1. Firewall rules configured
# 2. Connection string is correct
# 3. Username/password are correct
```

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│         Frontend (HTML/CSS/JS)          │
│        - Login/Register UI              │
│        - Transfer Money Form            │
│        - Passbook Display               │
└────────────┬────────────────────────────┘
             │ HTTP/HTTPS
             ▼
┌─────────────────────────────────────────┐
│      Backend (Flask Python API)         │
│  ┌─────────────────────────────────┐   │
│  │ Authentication (JWT)            │   │
│  │ - Register, Login               │   │
│  │ - Token validation              │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │ Account Management              │   │
│  │ - Balance query                 │   │
│  │ - Profile info                  │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │ Transactions                    │   │
│  │ - Money transfer                │   │
│  │ - Passbook query                │   │
│  └─────────────────────────────────┘   │
└────────────┬────────────────────────────┘
             │ ODBC/SQL
             ▼
┌─────────────────────────────────────────┐
│       Azure SQL Database                │
│  ┌─────────────────────────────────┐   │
│  │ Users Table (Auth)              │   │
│  ├─────────────────────────────────┤   │
│  │ Accounts Table (Balances)       │   │
│  ├─────────────────────────────────┤   │
│  │ Transactions Table (History)    │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

---

## Key Features Explained

### 🔐 Security
- Passwords hashed with bcrypt
- JWT tokens for authentication
- Secrets in Azure Key Vault
- Parameterized SQL queries (no injection)

### 💰 Transactions
- Real-time balance updates
- Transaction history with timestamps
- Debit/Credit classification
- Transaction descriptions

### 📱 UPI-Style
- Send money by UPI ID (e.g., alice@bank)
- Search for recipient
- Quick money transfer

### 📊 Passbook
- See all transactions
- Filter by date
- Transaction status

---

## Learning Goals Met

✅ **Azure Services**
- App Service (compute)
- SQL Database (data)
- Key Vault (security)

✅ **Backend Development**
- Flask REST API
- Authentication (JWT)
- Database operations

✅ **Frontend**
- Responsive UI
- API integration
- Real-time updates

✅ **DevOps**
- Infrastructure as Code (Bicep)
- Azure deployment
- Configuration management

---

## Next Steps

1. Add email notifications
2. Implement transaction approval flow
3. Add multi-currency support
4. Create admin dashboard
5. Add spending analytics
6. Implement mobile app (Flutter/React Native)

---

Happy Banking! 🏦
