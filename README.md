# 🏦 Cloud-Based Virtual Banking System on Azure

A secure, UPI-type virtual banking system built with Python Flask and Azure cloud services. Features fund transfers, transaction history (passbook), and proper authentication.

## 🏗️ Architecture

**3 Azure Services Used:**
1. **Azure SQL Database** - Stores user accounts, authentication data, and transaction records
2. **Azure Key Vault** - Securely manages secrets, connection strings, and JWT keys
3. **Azure App Service** - Hosts the Python Flask backend API (or use locally)

## ✨ Features

✅ **User Authentication** - Register & login with JWT tokens  
✅ **Account Management** - View balance, account details, UPI ID  
✅ **Fund Transfers** - UPI-style money transfer to other users  
✅ **Passbook** - Complete transaction history (debit/credit)  
✅ **Security** - Password hashing with bcrypt, JWT authentication  
✅ **Responsive UI** - Beautiful gradient interface for all devices  
✅ **Demo Mode** - Works without database for testing  

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- Azure CLI (for cloud deployment)
- Git

### 1. Clone & Setup

```powershell
git clone <repo-url>
cd Cloud-Based_Banking_System

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r src/requirements.txt
```

### 2. Run Locally (In-Memory Demo)

```powershell
# In the project root, run:
cd src
python app.py
```

The API will start at `http://localhost:5000`

### 3. Open Frontend

Open `index.html` in your browser or use:
```powershell
# Using Python's built-in server
python -m http.server 8000
# Then visit http://localhost:8000
```

### Demo Credentials

**Test these without a database:**
| User | Password | UPI ID |
|------|----------|--------|
| alice | alice123 | alice@bank |
| bob | bob123 | bob@bank |

**Try:** Login as `alice`, transfer ₹500 to `bob@bank` ✓

## 🔧 API Endpoints

### Authentication
```
POST /auth/register     - Create new account
POST /auth/login        - Login and get JWT token
```

### Account
```
GET  /account/profile       - Get account details
GET  /account/balance       - Get current balance
GET  /account/passbook      - Get transaction history
```

### Transfers
```
POST /transfer/send         - Transfer money to UPI
GET  /search/upi            - Search recipient UPI
```

**Example Request:**
```bash
# Login
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"alice123"}'

# Transfer Money
curl -X POST http://localhost:5000/transfer/send \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"to_upi":"bob@bank","amount":500,"description":"Payment"}'
```

## ☁️ Deploy to Azure

### 1. Create Azure Resources

```powershell
# Login to Azure
az login --use-device-code

# Create resource group
az group create --name BankRG --location eastus

# Deploy infrastructure
az deployment group create `
  --resource-group BankRG `
  --template-file infrastructure/main.bicep `
  --parameters sqlAdminPassword='YourSecurePassword123!'
```

### 2. Configure & Deploy App

```powershell
# Get SQL connection string from Azure Portal
# Update src/.env with:
# USE_SQL=true
# SQL_SERVER=<your-server>.database.windows.net
# SQL_USER=sqladmin
# SQL_PASSWORD=YourSecurePassword123!
# JWT_SECRET=<generate-secure-random-key>

# Package app
$compress = @{
  Path = "src/*", "requirements.txt"
  DestinationPath = "banking-app.zip"
}
Compress-Archive @compress

# Deploy to App Service
az webapp deployment source config-zip `
  --resource-group BankRG `
  --name <your-app-service-name> `
  --src banking-app.zip
```

### 3. Update Frontend

In `index.html`, change:
```javascript
const API_URL = "https://<your-app-service>.azurewebsites.net";
```

## 📊 Database Schema

### Users Table
```sql
- user_id (PK)
- username (unique)
- email (unique)
- password_hash
- full_name
- created_at
```

### Accounts Table
```sql
- account_id (PK, auto-increment from 1001)
- user_id (FK)
- upi_id (unique)
- balance
- account_type
- created_at
```

### Transactions Table
```sql
- transaction_id (PK)
- from_account (FK)
- to_account (FK)
- amount
- transaction_type
- status
- timestamp
- description
```

## 🔐 Security Features

- ✅ Passwords hashed with bcrypt
- ✅ JWT token authentication
- ✅ Secrets stored in Azure Key Vault
- ✅ CORS protection
- ✅ SQL injection prevention (parameterized queries)
- ✅ HTTPS enforced in production
- ✅ Minimum TLS 1.2

## 📁 Project Structure

```
├── index.html                 # Frontend UI
├── deploy.ps1               # Azure deployment script
├── README.md                # This file
├── infrastructure/
│   └── main.bicep          # Azure infrastructure (App Service, SQL, Key Vault)
├── src/
│   ├── app.py              # Flask API server
│   ├── database.py         # Database operations & schema
│   ├── config.py           # Configuration management
│   ├── requirements.txt     # Python dependencies
│   └── __init__.py
```

## 💰 Azure Cost Estimates (Student Account)

| Service | SKU | Monthly Cost* |
|---------|-----|---------------|
| SQL Database | Basic | ~$5-15 |
| App Service | B1 | ~$10 |
| Key Vault | Standard | ~$0.6 |
| **Total** | | **~$15-25** |

*Azure Student credits should cover this easily. Check your free credit at portal.azure.com

## 🐛 Troubleshooting

### Port 5000 already in use?
```powershell
# Change in .env:
APP_PORT=5001
```

### SQL Connection fails?
```powershell
# Check firewall rules in Azure Portal
# Ensure "Allow Azure Services" is enabled
# Add your IP to firewall rules
```

### CORS errors?
```powershell
# Update CORS_ORIGINS in .env:
CORS_ORIGINS=http://localhost:5000,https://your-domain.com
```

## 📚 Learning Resources

- [Azure SQL Database Docs](https://docs.microsoft.com/azure/azure-sql/)
- [Azure Key Vault Docs](https://docs.microsoft.com/azure/key-vault/)
- [Azure App Service Docs](https://docs.microsoft.com/azure/app-service/)
- [Bicep Language Reference](https://docs.microsoft.com/azure/azure-resource-manager/bicep/)

## 📝 License

MIT License - feel free to use and modify!

## 🤝 Contributing

Found a bug? Want to add features? Submit a pull request!

---

**Built with ❤️ for learning Azure cloud architecture**

For support, open an issue on GitHub or check the docs folder.
