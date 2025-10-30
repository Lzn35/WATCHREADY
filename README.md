# WATCH System - Discipline Office Management System

A comprehensive web-based management system for school discipline offices to track cases, attendance, appointments, and administrative tasks.

## 📋 Table of Contents

- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Production Deployment](#production-deployment)
- [Default Credentials](#default-credentials)
- [User Roles](#user-roles)
- [Database](#database)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

## ✨ Features

### Core Functionality
- **User Authentication** - Secure login with role-based access control
- **Case Management** - Track major and minor disciplinary cases
- **Attendance Tracking** - Schedule management and attendance monitoring
- **Appointment Scheduling** - Online appointment booking with QR codes
- **Document Management** - OCR-powered document scanning and processing
- **Report Generation** - Comprehensive PDF reports for cases and attendance
- **Audit Logging** - Complete audit trail of all system activities

### Security Features
- ✅ CSRF Protection
- ✅ Auto-logout on browser close
- ✅ Security headers (CSP, X-Frame-Options, etc.)
- ✅ Rate limiting
- ✅ Password hashing
- ✅ Protected admin accounts
- ✅ Session management

## 🖥️ System Requirements

### Minimum Requirements
- **OS**: Windows 10/11, Linux, or macOS
- **Python**: 3.8 or higher
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 500MB minimum for application + space for database/uploads

### Optional
- **Tesseract OCR**: For document scanning features
- **MySQL**: For production deployments (SQLite included for development)

## 📥 Installation

### 1. Clone or Download the Repository

```bash
cd WATCH
```

### 2. Create Virtual Environment (Recommended)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
cd watch
pip install -r requirements.txt
```

### 4. Initialize the Database

```bash
python init_database.py
```

This will create the database and set up:
- Database tables
- Default roles (Admin, User)
- Default admin account
- System settings

## ⚙️ Configuration

### Environment Variables

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Generate a secure SECRET_KEY:**
   ```bash
   python generate_secret_key.py
   ```

3. **Edit `.env` file with your settings:**
   ```env
   SECRET_KEY=your-generated-secret-key-here
   APP_CONFIG=Config
   DEBUG=False
   ```

### Configuration Profiles

The system supports multiple configuration profiles:

- **Config** (Default) - Basic configuration for local use
- **DevelopmentConfig** - Development with debug enabled
- **NetworkConfig** - Local network deployment (HTTP)
- **ProductionConfig** - Production deployment (HTTPS)

Set the profile in `.env`:
```env
APP_CONFIG=NetworkConfig
```

## 🚀 Running the Application

### Development Mode

```bash
python run.py
```

Access at: `http://localhost:5000`

### Production Mode (Windows)

Using Waitress (recommended for Windows):

```bash
python -m waitress --host=0.0.0.0 --port=8000 --threads=4 wsgi:app
```

### Production Mode (Linux)

Using Gunicorn (recommended for Linux):

```bash
gunicorn -w 4 -b 0.0.0.0:8000 --timeout 120 wsgi:app
```

## 🌐 Production Deployment

### Pre-Deployment Checklist

- [ ] Generate and set a strong `SECRET_KEY`
- [ ] Set `DEBUG=False` in `.env`
- [ ] Configure database (MySQL recommended for production)
- [ ] Set appropriate `APP_CONFIG` (NetworkConfig or ProductionConfig)
- [ ] Configure firewall rules
- [ ] Set up SSL/TLS certificate (if using HTTPS)
- [ ] Configure email settings through web interface
- [ ] Change default admin password
- [ ] Test all functionality

### Local Network Deployment (HTTP)

For deployment on a local network without HTTPS:

1. **Configure `.env`:**
   ```env
   SECRET_KEY=your-generated-key
   APP_CONFIG=NetworkConfig
   DEBUG=False
   SESSION_COOKIE_SECURE=False
   ENABLE_HSTS=False
   ```

2. **Start the server:**
   ```bash
   python -m waitress --host=0.0.0.0 --port=8000 --threads=4 wsgi:app
   ```

3. **Access from network:**
   - Find server IP: `ipconfig` (Windows) or `ifconfig` (Linux)
   - Access at: `http://YOUR_IP:8000`

### Internet Deployment (HTTPS)

For deployment on the internet with HTTPS:

1. **Configure `.env`:**
   ```env
   SECRET_KEY=your-generated-key
   APP_CONFIG=ProductionConfig
   DEBUG=False
   SESSION_COOKIE_SECURE=True
   ENABLE_HSTS=True
   DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/watch_db
   ```

2. **Set up reverse proxy (Nginx/Apache)**
3. **Configure SSL/TLS certificate**
4. **Start the application server**

### Database Migration (SQLite to MySQL)

1. **Install MySQL and create database:**
   ```sql
   CREATE DATABASE watch_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'watch_user'@'localhost' IDENTIFIED BY 'your_password';
   GRANT ALL PRIVILEGES ON watch_db.* TO 'watch_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

2. **Update `.env`:**
   ```env
   DATABASE_URL=mysql+pymysql://watch_user:your_password@localhost:3306/watch_db
   ```

3. **Initialize the new database:**
   ```bash
   python init_database.py
   ```

4. **Migrate data** (manual export/import or use database tools)

## 🔐 Default Credentials

After initialization, use these credentials to log in:

- **Username:** `discipline_officer`
- **Password:** `admin123`

**⚠️ IMPORTANT:** Change this password immediately after first login!

## 👥 User Roles

### Admin (Discipline Officer)
- Full system access
- User management
- System settings
- Case management
- Attendance tracking
- Report generation
- All administrative functions

### User (Discipline Committee)
- Case management
- Attendance tracking
- View appointments
- Limited administrative access

## 🗄️ Database

### SQLite (Default)
- Location: `watch/instance/watch_db.sqlite`
- Suitable for: Small deployments, single server
- Automatic backups created

### MySQL (Recommended for Production)
- Better performance for multiple concurrent users
- Better backup and recovery options
- Recommended for production deployments

## 🔒 Security

### Best Practices

1. **Change Default Password** - Immediately after installation
2. **Use Strong SECRET_KEY** - Generate with `generate_secret_key.py`
3. **Enable HTTPS** - For internet-facing deployments
4. **Regular Backups** - Database is backed up automatically
5. **Update Dependencies** - Keep packages up to date
6. **Restrict Access** - Use firewall rules
7. **Monitor Logs** - Check `watch/logs/` regularly

### Security Features

- **CSRF Protection**: Enabled on all forms
- **Password Hashing**: Werkzeug secure password hashing
- **Auto-Logout**: Sessions expire when browser closes
- **Security Headers**: CSP, X-Frame-Options, etc.
- **Rate Limiting**: Prevents brute force attacks
- **Audit Logging**: All actions logged
- **Protected Accounts**: Admin account cannot be deleted

## 🔧 Troubleshooting

### Common Issues

**Issue: Application won't start**
- Check Python version: `python --version` (must be 3.8+)
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check database exists: `python init_database.py`

**Issue: Can't login**
- Verify database is initialized
- Check default credentials
- Review logs in `watch/logs/errors.log`

**Issue: Database errors**
- Ensure database file has write permissions
- Check disk space
- Review `watch/logs/db_operations.log`

**Issue: Can't access from network**
- Check firewall settings
- Verify server is binding to `0.0.0.0` not `127.0.0.1`
- Confirm correct IP address

**Issue: File uploads not working**
- Check `watch/instance/uploads` directory exists
- Verify write permissions
- Check `MAX_CONTENT_LENGTH` setting

### Logs

System logs are located in `watch/logs/`:
- `application.log` - General application logs
- `errors.log` - Error messages
- `security.log` - Security events
- `db_operations.log` - Database operations

### Getting Help

1. Check the logs first
2. Review the test cases documentation: `WATCH_SYSTEM_TEST_CASES.md`
3. Check auto-logout documentation: `AUTO_LOGOUT_IMPLEMENTATION.md`

## 📁 Project Structure

```
WATCH/
├── watch/                      # Main application directory
│   ├── app/                    # Flask application
│   │   ├── modules/            # Feature modules
│   │   ├── services/           # Business logic services
│   │   ├── static/             # Static files (CSS, JS, images)
│   │   ├── templates/          # HTML templates
│   │   ├── utils/              # Utility functions
│   │   ├── config.py           # Configuration
│   │   └── models.py           # Database models
│   ├── instance/               # Instance-specific files
│   │   ├── config.py           # Instance configuration
│   │   ├── uploads/            # Uploaded files
│   │   └── watch_db.sqlite     # Database (SQLite)
│   ├── logs/                   # Application logs
│   ├── requirements.txt        # Python dependencies
│   ├── init_database.py        # Database initialization
│   ├── generate_secret_key.py  # Secret key generator
│   └── wsgi.py                 # WSGI entry point
├── .env.example                # Environment configuration template
├── README.md                   # This file
└── run.py                      # Development server launcher
```

## 📝 License

This is a proprietary system for school discipline office management.

## 🙏 Support

For support or questions:
1. Review the documentation
2. Check the logs for error details
3. Consult the test cases documentation

---

**Version:** 1.0.0  
**Last Updated:** October 2024  
**Status:** Production Ready

