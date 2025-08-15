#!/usr/bin/env python3
"""
Safe removal of secrets from Git history

This script helps remove sensitive data from Git commits while preserving
the repository structure.
"""

import subprocess
import os
import sys

def run_command(command, check=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if check and result.returncode != 0:
            print(f"❌ Command failed: {command}")
            print(f"Error: {result.stderr}")
            return None
        return result
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return None

def main():
    print("🚨 REMOVING SECRETS FROM GIT HISTORY")
    print("=" * 50)
    
    # Check if we're in a git repository
    if not os.path.exists('.git'):
        print("❌ Not in a Git repository!")
        sys.exit(1)
    
    # Create backup branch
    print("📋 Creating backup branch...")
    run_command("git branch backup-before-secret-cleanup")
    
    # Define secrets to remove
    secrets_to_remove = {
        "i9Mu2wgiHvfG": "[EMAIL_PASSWORD_REDACTED]",
        "TL1pMOaRvnnSXEkTCcmd508MTg2GCVFoTR2NooVMtUqKl9qWnFl9duMHUgsF3i": "[TERMII_API_KEY_REDACTED]",
        "emailappsmtp.1219fc28d7f8a75": "[EMAIL_USER_REDACTED]"
    }
    
    # Use git-filter-repo if available, otherwise use filter-branch
    filter_repo_available = run_command("which git-filter-repo", check=False)
    
    if filter_repo_available and filter_repo_available.returncode == 0:
        print("✅ Using git-filter-repo (recommended method)")
        
        # Create replacements file
        with open('replacements.txt', 'w') as f:
            for secret, replacement in secrets_to_remove.items():
                f.write(f"{secret}==>{replacement}\n")
        
        # Run git-filter-repo
        result = run_command("git filter-repo --replace-text replacements.txt --force")
        
        # Clean up
        os.remove('replacements.txt')
        
        if result:
            print("✅ Secrets removed using git-filter-repo!")
        else:
            print("❌ git-filter-repo failed, falling back to filter-branch")
            use_filter_branch(secrets_to_remove)
    else:
        print("⚠️  git-filter-repo not available, using filter-branch")
        use_filter_branch(secrets_to_remove)
    
    print("\n✅ SECRET REMOVAL COMPLETE!")
    print("\n📋 CRITICAL NEXT STEPS:")
    print("1. ⚠️  FIRST: Rotate all exposed credentials immediately!")
    print("   - Change your email password in ZeptoMail")
    print("   - Rotate your TERMII API key")
    print("2. Verify cleanup: git log --oneline -5")
    print("3. Force push: git push --force-with-lease origin main")
    print("4. Clean up: git branch -D backup-before-secret-cleanup")
    print("\n🔒 Your repository will be secure after force pushing!")

def use_filter_branch(secrets_to_remove):
    """Fallback method using git filter-branch"""
    print("Using git filter-branch method...")
    
    for secret, replacement in secrets_to_remove.items():
        print(f"Removing: {secret[:10]}...")
        
        filter_command = f'''git filter-branch --force --tree-filter '
            find . -type f \\( -name "*.py" -o -name "*.md" -o -name "*.txt" \\) -exec sed -i "s/{secret}/{replacement}/g" {{}} \\; 2>/dev/null || true
        ' --all'''
        
        run_command(filter_command)
    
    # Clean up filter-branch remnants
    print("Cleaning up...")
    run_command("rm -rf .git/refs/original/")
    run_command("git reflog expire --expire=now --all")
    run_command("git gc --prune=now --aggressive")

if __name__ == "__main__":
    main()
