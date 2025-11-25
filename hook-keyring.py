"""
PyInstaller Runtime Hook for Keyring
=====================================

This hook forces keyring to use ONLY the macOS Keychain backend,
preventing multiple password prompts during app startup.

Place this file in the same directory as your HelloToolBelt.spec file.
"""

import sys

if sys.platform == 'darwin':
    try:
        import keyring
        from keyring.backends import macOS
        
        # Force keyring to use only the macOS Keychain backend
        keyring.set_keyring(macOS.Keyring())
        
        print("✓ Runtime hook: Keyring configured to use macOS backend only")
        
    except ImportError as e:
        print(f"⚠ Runtime hook: Could not import keyring - {e}")
    except Exception as e:
        print(f"⚠ Runtime hook: Error setting keyring backend - {e}")
else:
    print("ℹ Runtime hook: Not on macOS, skipping keyring configuration")