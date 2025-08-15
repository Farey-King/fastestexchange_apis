#!/bin/bash

# Script to remove sensitive data from Git history
# WARNING: This will rewrite Git history and require force pushing

echo "🚨 CLEANING SENSITIVE DATA FROM GIT HISTORY 🚨"
echo "================================================"

# Create backup branch first
git branch backup-before-cleanup

# Remove specific sensitive strings from all history
echo "Removing EMAIL_HOST_PASSWORD..."
git filter-branch --force --tree-filter '
    if [ -f "SIGNUP_FIXES_SUMMARY.md" ]; then
        sed -i "s/i9Mu2wgiHvfG/\[REDACTED\]/g" SIGNUP_FIXES_SUMMARY.md 2>/dev/null || true
    fi
    find . -type f -name "*.md" -exec sed -i "s/i9Mu2wgiHvfG/\[REDACTED\]/g" {} \; 2>/dev/null || true
' --all

echo "Removing TERMII_API_KEY..."
git filter-branch --force --tree-filter '
    if [ -f "fastest_exchange/utils.py" ]; then
        sed -i "s/TL1pMOaRvnnSXEkTCcmd508MTg2GCVFoTR2NooVMtUqKl9qWnFl9duMHUgsF3i/\[REDACTED\]/g" fastest_exchange/utils.py 2>/dev/null || true
    fi
    find . -type f \( -name "*.py" -o -name "*.md" \) -exec sed -i "s/TL1pMOaRvnnSXEkTCcmd508MTg2GCVFoTR2NooVMtUqKl9qWnFl9duMHUgsF3i/\[REDACTED\]/g" {} \; 2>/dev/null || true
' --all

echo "Removing email user..."
git filter-branch --force --tree-filter '
    find . -type f -name "*.md" -exec sed -i "s/emailappsmtp\.1219fc28d7f8a75/\[REDACTED\]/g" {} \; 2>/dev/null || true
' --all

# Clean up the filter-branch refs
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo "✅ Git history cleaned!"
echo "📋 Next steps:"
echo "1. Verify the cleanup worked: git log --oneline | head -10"
echo "2. Force push to GitHub: git push --force-with-lease origin main"
echo "3. Delete the backup branch: git branch -D backup-before-cleanup"
echo ""
echo "⚠️  WARNING: You MUST have already rotated your credentials before pushing!"
