# Security Setup Guide

## ⚠️ IMPORTANT: Credentials Security

This project uses environment variables to store sensitive credentials. **NEVER commit your `.env` file to version control.**

## Quick Setup

### Step 1: Create your `.env` file

Copy the example file:
```bash
cp .env.example .env
```

### Step 2: Update `.env` with your credentials

Edit `.env` and replace the placeholder values with your actual credentials:

```bash
# MongoDB Connection (REQUIRED)
MONGODB_URI=mongodb+srv://your_username:your_password@cluster0.lixbqmp.mongodb.net/
MONGODB_DB=Project2
```

**Important:** After rotating your MongoDB password (see below), update the `MONGODB_URI` in your `.env` file.

### Step 3: Verify `.env` is ignored

The `.gitignore` file should already include `.env`. Verify with:
```bash
cat .gitignore | grep .env
```

You should see `.env` listed.

## MongoDB Credential Rotation (CRITICAL)

If your credentials were exposed:

1. **Go to MongoDB Atlas** → Your Project → Database Access
2. **Delete the exposed user** OR **Change its password**
3. **Create a new database user** with a strong password
4. **Update your `.env` file** with the new connection string

## What's Protected

The following sensitive data is now stored in environment variables:
- ✅ MongoDB connection URI (username + password)
- ✅ ClickHouse credentials (if using authentication)
- ✅ Redis credentials (if using authentication)
- ✅ API keys (if added in future)

## Default Values

If environment variables are not set, the code uses safe defaults:
- MongoDB: `mongodb://localhost:27017/` (local development)
- ClickHouse: `localhost:9000` (local development)
- Redis: `localhost:6379` (local development)

## Testing Your Setup

After creating `.env`, test the connection:
```bash
python3 -c "from config import MONGODB_URI; print('Config loaded successfully')"
```

## Troubleshooting

**Error: "MONGODB_URI not found"**
- Make sure `.env` file exists in the project root
- Check that `.env` contains `MONGODB_URI=...`
- Verify no extra spaces around the `=` sign

**Error: "ModuleNotFoundError: No module named 'dotenv'"**
- Install dependencies: `pip install -r requirements.txt`

## Best Practices

1. ✅ Use `.env` for local development
2. ✅ Use `.env.example` as a template (safe to commit)
3. ✅ Never commit `.env` to version control
4. ✅ Rotate credentials immediately if exposed
5. ✅ Use strong, unique passwords
6. ✅ Review `.gitignore` before committing
