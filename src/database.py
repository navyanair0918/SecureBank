import os
import pyodbc
import bcrypt
from datetime import datetime
from config import SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD, USE_SQL

class BankDatabase:
    def __init__(self):
        self.connection = None
        self.use_sql = USE_SQL
        
        # In-memory fallback
        self._users = {}
        self._accounts = {}
        self._transactions = []
        self._next_account_id = 1001
        
        if self.use_sql:
            self._connect_sql()
            self._init_database()
        else:
            # Initialize with demo accounts
            self._init_demo_data()

    def _connect_sql(self):
        """Connect to Azure SQL Database"""
        if SQL_SERVER and SQL_DATABASE and SQL_USER and SQL_PASSWORD:
            conn_string = (
                f"Driver={{ODBC Driver 17 for SQL Server}};"
                f"Server={SQL_SERVER};"
                f"Database={SQL_DATABASE};"
                f"UID={SQL_USER};PWD={SQL_PASSWORD};"
                f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
            )
            try:
                self.connection = pyodbc.connect(conn_string, timeout=10)
                print("✓ Connected to SQL Database")
            except Exception as e:
                print(f"✗ SQL connection failed: {e}")
                self.connection = None

    def _init_database(self):
        """Create tables if they don't exist"""
        if not self.connection:
            return
        
        cursor = self.connection.cursor()
        try:
            # Create Users table
            cursor.execute('''
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Users' AND xtype='U')
                CREATE TABLE Users (
                    user_id INT PRIMARY KEY IDENTITY(1,1),
                    username NVARCHAR(50) UNIQUE NOT NULL,
                    email NVARCHAR(100) UNIQUE NOT NULL,
                    password_hash NVARCHAR(255) NOT NULL,
                    full_name NVARCHAR(100) NOT NULL,
                    created_at DATETIME DEFAULT GETUTCDATE()
                )
            ''')
            
            # Create Accounts table
            cursor.execute('''
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Accounts' AND xtype='U')
                CREATE TABLE Accounts (
                    account_id INT PRIMARY KEY IDENTITY(1001,1),
                    user_id INT NOT NULL FOREIGN KEY REFERENCES Users(user_id),
                    upi_id NVARCHAR(50) UNIQUE NOT NULL,
                    balance FLOAT DEFAULT 0,
                    account_type NVARCHAR(20) DEFAULT 'savings',
                    created_at DATETIME DEFAULT GETUTCDATE()
                )
            ''')
            
            # Create Transactions table
            cursor.execute('''
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Transactions' AND xtype='U')
                CREATE TABLE Transactions (
                    transaction_id INT PRIMARY KEY IDENTITY(1,1),
                    from_account INT NOT NULL FOREIGN KEY REFERENCES Accounts(account_id),
                    to_account INT NOT NULL FOREIGN KEY REFERENCES Accounts(account_id),
                    amount FLOAT NOT NULL,
                    transaction_type NVARCHAR(20),
                    status NVARCHAR(20) DEFAULT 'completed',
                    timestamp DATETIME DEFAULT GETUTCDATE(),
                    description NVARCHAR(255)
                )
            ''')
            
            self.connection.commit()
            print("✓ Database schema initialized")
        except Exception as e:
            print(f"✗ Error initializing database: {e}")

    def _init_demo_data(self):
        """Initialize demo accounts for testing"""
        self._users = {
            1: {"username": "alice", "email": "alice@bank.com", "password_hash": bcrypt.hashpw(b"alice123", bcrypt.gensalt()), "full_name": "Alice Johnson"},
            2: {"username": "bob", "email": "bob@bank.com", "password_hash": bcrypt.hashpw(b"bob123", bcrypt.gensalt()), "full_name": "Bob Smith"},
        }
        self._accounts = {
            1001: {"user_id": 1, "upi_id": "alice@bank", "balance": 5000.0, "account_type": "savings"},
            1002: {"user_id": 2, "upi_id": "bob@bank", "balance": 3000.0, "account_type": "savings"},
        }

    # ========== Authentication Methods ==========
    
    def register_user(self, username, email, password, full_name):
        """Register a new user"""
        try:
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            
            if self.use_sql and self.connection:
                cursor = self.connection.cursor()
                cursor.execute('''
                    INSERT INTO Users (username, email, password_hash, full_name)
                    VALUES (?, ?, ?, ?)
                ''', username, email, password_hash, full_name)
                self.connection.commit()
                
                # Get the user ID and create account
                cursor.execute('SELECT user_id FROM Users WHERE username = ?', username)
                user_id = cursor.fetchone()[0]
                
                # Create UPI ID
                upi_id = f"{username}@bank"
                cursor.execute('''
                    INSERT INTO Accounts (user_id, upi_id, balance, account_type)
                    VALUES (?, ?, 0, 'savings')
                ''', user_id, upi_id)
                self.connection.commit()
                return True, {"user_id": user_id, "username": username, "upi_id": upi_id}
            else:
                # Fallback: in-memory
                user_id = max(self._users.keys()) + 1 if self._users else 1
                self._users[user_id] = {
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                    "full_name": full_name
                }
                
                upi_id = f"{username}@bank"
                account_id = self._next_account_id
                self._next_account_id += 1
                self._accounts[account_id] = {
                    "user_id": user_id,
                    "upi_id": upi_id,
                    "balance": 0,
                    "account_type": "savings"
                }
                return True, {"user_id": user_id, "username": username, "upi_id": upi_id}
        except Exception as e:
            return False, str(e)

    def authenticate_user(self, username, password):
        """Authenticate user and return user_id"""
        try:
            if self.use_sql and self.connection:
                cursor = self.connection.cursor()
                cursor.execute('SELECT user_id, password_hash FROM Users WHERE username = ?', username)
                result = cursor.fetchone()
                if result:
                    user_id, password_hash = result
                    if bcrypt.checkpw(password.encode(), password_hash.encode()):
                        return True, user_id
            else:
                for user_id, user_data in self._users.items():
                    if user_data["username"] == username:
                        if bcrypt.checkpw(password.encode(), user_data["password_hash"]):
                            return True, user_id
            return False, "Invalid credentials"
        except Exception as e:
            return False, str(e)

    # ========== Account Methods ==========
    
    def get_account_by_upi(self, upi_id):
        """Get account by UPI ID"""
        if self.use_sql and self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT account_id, user_id, upi_id, balance FROM Accounts WHERE upi_id = ?', upi_id)
            result = cursor.fetchone()
            if result:
                return {"account_id": result[0], "user_id": result[1], "upi_id": result[2], "balance": result[3]}
        else:
            for account_id, account in self._accounts.items():
                if account["upi_id"] == upi_id:
                    return {"account_id": account_id, **account}
        return None

    def get_account(self, account_id):
        """Get account details"""
        if self.use_sql and self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT account_id, user_id, upi_id, balance FROM Accounts WHERE account_id = ?', account_id)
            result = cursor.fetchone()
            if result:
                return {"account_id": result[0], "user_id": result[1], "upi_id": result[2], "balance": result[3]}
        else:
            if account_id in self._accounts:
                return {"account_id": account_id, **self._accounts[account_id]}
        return None

    def get_user_account(self, user_id):
        """Get account for a specific user"""
        if self.use_sql and self.connection:
            cursor = self.connection.cursor()
            cursor.execute('SELECT account_id, user_id, upi_id, balance FROM Accounts WHERE user_id = ?', user_id)
            result = cursor.fetchone()
            if result:
                return {"account_id": result[0], "user_id": result[1], "upi_id": result[2], "balance": result[3]}
        else:
            for account_id, account in self._accounts.items():
                if account["user_id"] == user_id:
                    return {"account_id": account_id, **account}
        return None

    # ========== Transaction Methods ==========
    
    def create_transaction(self, from_account_id, to_account_id, amount, description=""):
        """Transfer funds between accounts"""
        try:
            # Validate accounts and balance
            from_acc = self.get_account(from_account_id)
            to_acc = self.get_account(to_account_id)
            
            if not from_acc or not to_acc:
                return False, "Account not found"
            if amount <= 0:
                return False, "Amount must be positive"
            if from_acc["balance"] < amount:
                return False, "Insufficient funds"
            
            if self.use_sql and self.connection:
                cursor = self.connection.cursor()
                try:
                    # Deduct from sender
                    cursor.execute('''
                        UPDATE Accounts SET balance = balance - ? WHERE account_id = ?
                    ''', amount, from_account_id)
                    
                    # Add to receiver
                    cursor.execute('''
                        UPDATE Accounts SET balance = balance + ? WHERE account_id = ?
                    ''', amount, to_account_id)
                    
                    # Record transaction
                    cursor.execute('''
                        INSERT INTO Transactions (from_account, to_account, amount, transaction_type, status, description)
                        VALUES (?, ?, ?, 'transfer', 'completed', ?)
                    ''', from_account_id, to_account_id, amount, description)
                    
                    self.connection.commit()
                    
                    # Get transaction ID
                    cursor.execute('SELECT @@IDENTITY')
                    txn_id = cursor.fetchone()[0]
                    return True, {
                        "transaction_id": txn_id,
                        "from": from_account_id,
                        "to": to_account_id,
                        "amount": amount,
                        "timestamp": datetime.now().isoformat(),
                        "status": "completed"
                    }
                except Exception as e:
                    self.connection.rollback()
                    raise e
            else:
                # In-memory transaction
                from_acc["balance"] -= amount
                to_acc["balance"] += amount
                
                txn = {
                    "transaction_id": len(self._transactions) + 1,
                    "from": from_account_id,
                    "to": to_account_id,
                    "amount": amount,
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed"
                }
                self._transactions.append(txn)
                return True, txn
        except Exception as e:
            return False, str(e)

    def get_transactions(self, account_id):
        """Get transaction history for an account (passbook)"""
        transactions = []
        try:
            if self.use_sql and self.connection:
                cursor = self.connection.cursor()
                cursor.execute('''
                    SELECT transaction_id, from_account, to_account, amount, timestamp, description
                    FROM Transactions
                    WHERE from_account = ? OR to_account = ?
                    ORDER BY timestamp DESC
                ''', account_id, account_id)
                
                for row in cursor.fetchall():
                    txn = {
                        "transaction_id": row[0],
                        "from_account": row[1],
                        "to_account": row[2],
                        "amount": row[3],
                        "timestamp": str(row[4]),
                        "description": row[5],
                        "type": "debit" if row[1] == account_id else "credit"
                    }
                    transactions.append(txn)
            else:
                # In-memory
                for txn in self._transactions:
                    if txn["from"] == account_id or txn["to"] == account_id:
                        transactions.append({
                            **txn,
                            "type": "debit" if txn["from"] == account_id else "credit"
                        })
        except Exception as e:
            print(f"Error fetching transactions: {e}")
        
        return transactions
