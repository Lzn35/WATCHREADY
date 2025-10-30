#!/usr/bin/env python3
"""
Secret Key Generator for WATCH System
Generates a cryptographically secure random secret key for production use.
"""

import secrets
import sys

def generate_secret_key(length=32):
    """
    Generate a cryptographically secure random secret key.
    
    Args:
        length (int): Length of the key in bytes (default: 32 bytes = 256 bits)
    
    Returns:
        str: Hex-encoded secret key
    """
    return secrets.token_hex(length)

def main():
    print("=" * 70)
    print("  WATCH System - Secret Key Generator")
    print("=" * 70)
    print()
    print("Generating a cryptographically secure secret key...")
    print()
    
    secret_key = generate_secret_key()
    
    print("Your new SECRET_KEY:")
    print("-" * 70)
    print(secret_key)
    print("-" * 70)
    print()
    print("IMPORTANT: Copy this key and add it to your .env file:")
    print(f"SECRET_KEY={secret_key}")
    print()
    print("Security Notes:")
    print("  ✓ This key is cryptographically secure (256-bit entropy)")
    print("  ✓ Never share this key or commit it to version control")
    print("  ✓ Keep this key secret and secure")
    print("  ✓ Generate a new key for each environment (dev, staging, prod)")
    print()
    print("To use this key:")
    print("  1. Copy the SECRET_KEY line above")
    print("  2. Open your .env file (create one from .env.example if needed)")
    print("  3. Replace the SECRET_KEY line with the new one")
    print("  4. Restart your application")
    print()
    print("=" * 70)

if __name__ == "__main__":
    main()

