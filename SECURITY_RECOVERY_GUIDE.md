# 🚨 Security Recovery Guide

## IMMEDIATE ACTION REQUIRED!

Your SMTP credentials and API keys have been exposed in Git history. **Take immediate action to secure your application.**

## ⚠️ EXPOSED CREDENTIALS

The following sensitive data was found in your Git commits:

1. **Email Password**: `i9Mu2wgiHvfG`
2. **TERMII API Key**: `TL1pMOaRvnnSXEkTCcmd508MTg2GCVFoTR2NooVMtUqKl9qWnFl9duMHUgsF3i`  
3. **Email User**: `emailappsmtp.1219fc28d7f8a75`

## 🔧 IMMEDIATE STEPS TO TAKE

### Step 1: Rotate All Credentials (DO THIS FIRST!)

**Before cleaning Git history, you MUST rotate these credentials:**

1. **ZeptoMail/Email Provider**:
   - Log into your ZeptoMail dashboard
   - Generate a new SMTP password
   - Update your `.env` file with the new password

2. **Termii API**:
   - Log into your Termii dashboard
   - Regenerate your API key
   - Update your `.env` file with the new key

3. **Test the new credentials** to ensure they work

### Step 2: Clean Git History

**Option A: Using the Python script (Recommended)**
```bash
python remove_secrets.py
```

**Option B: Manual cleanup**
```bash
# Create backup
git branch backup-before-cleanup

# Remove secrets from history (this will rewrite history)
git filter-branch --force --tree-filter '
    find . -type f \( -name "*.py" -o -name "*.md" \) \
    -exec sed -i "s/i9Mu2wgiHvfG/[REDACTED]/g" {} \; 2>/dev/null || true
' --all

# Clean up
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### Step 3: Force Push Clean History

**⚠️ CRITICAL: Only do this AFTER rotating credentials!**

```bash
# Verify the cleanup worked
git log --oneline -5

# Force push the cleaned history
git push --force-with-lease origin main

# Clean up backup branch
git branch -D backup-before-cleanup
```

## 🔒 Prevention Measures Implemented

### Enhanced .gitignore
- Added comprehensive patterns for secrets
- Prevents future credential leaks

### Pre-commit Hooks
Install to prevent future issues:
```bash
pip install pre-commit
pre-commit install
```

### Environment Variable Best Practices
- Use `.env` files (already in `.gitignore`)
- Never commit actual secrets to version control
- Use placeholder values in `.env.example`

## 🚀 Production Deployment Security

### GitHub Secrets (For Actions)
If using GitHub Actions, store secrets securely:

1. Go to your repository → Settings → Secrets and variables → Actions
2. Add these secrets:
   - `EMAIL_HOST_PASSWORD` (your new email password)
   - `TERMII_API_KEY` (your new API key)
   - `SECRET_KEY` (Django secret key)

### Environment Variables
For deployment platforms:
```env
EMAIL_HOST_PASSWORD=your_new_secure_password
TERMII_API_KEY=your_new_api_key
SECRET_KEY=your_django_secret_key
```

## 📋 Security Checklist

- [ ] ✅ Rotated email SMTP password
- [ ] ✅ Rotated TERMII API key
- [ ] ✅ Updated local `.env` file
- [ ] ✅ Tested new credentials work
- [ ] ✅ Cleaned Git history using script
- [ ] ✅ Verified secrets removed from history
- [ ] ✅ Force pushed clean history to GitHub
- [ ] ✅ Updated production environment variables
- [ ] ✅ Installed pre-commit hooks
- [ ] ✅ Documented secure practices for team

## 🔍 Verification

After completing all steps, verify security:

```bash
# Check that secrets are no longer in history
git log --all -p | grep -E "(i9Mu2wgiHvfG|TL1pMOaRvnnSXEkTCcmd508MTg2GCVFoTR2NooVMtUqKl9qWnFl9duMHUgsF3i)"

# Should return no results
```

## 🚨 Future Security Practices

1. **Never commit secrets to version control**
2. **Always use environment variables for sensitive data**
3. **Use pre-commit hooks to scan for secrets**
4. **Regularly rotate API keys and passwords**
5. **Use tools like `detect-secrets` in CI/CD**
6. **Review commits before pushing**

## 🆘 If You Need Help

If you encounter issues during cleanup:

1. **Don't panic** - you have backup branches
2. **Don't push until secrets are rotated**
3. **Contact your team lead if needed**
4. **Consider using BFG Repo Cleaner for complex cases**

## 📞 Emergency Contacts

- **Security Team**: [Your team contact]
- **DevOps Team**: [Your DevOps contact]
- **Project Lead**: [Your lead contact]

---

**Remember**: The most important step is rotating the exposed credentials immediately. Git history cleanup is secondary to preventing active credential compromise.

## Recovery Status Tracking

- [ ] **CRITICAL**: Credentials rotated
- [ ] **HIGH**: Git history cleaned  
- [ ] **MEDIUM**: Force pushed to GitHub
- [ ] **LOW**: Prevention measures installed

**Status**: 🔴 CRITICAL - Immediate action required
