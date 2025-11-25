# -*- mode: python ; coding: utf-8 -*-
# HelloToolBelt PyInstaller Spec File
# Fixed to prevent multiple macOS keychain password prompts
block_cipher = None
# Exclude problematic keyring backends that cause multiple password prompts
excluded_modules = [
    'keyring.backends.Windows',
    'keyring.backends.kwallet',
    'keyring.backends.SecretService',
    'keyring.backends.chainer',
]
a = Analysis(
    ['HelloToolbelt.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('auth_integration.py', '.'),  # Auth integration
        ('user_managment.py', '.'),  # User management tab
        ('user_audit.py', '.'),  # User audit logs tab
        ('eligibility_tool.py', '.'),
        ('configurator_tool.py', '.'),
        ('multisearch_tool.py', '.'),
        ('Cron_tool.py', '.'),
        ('Base64_Tool.py', '.'),
        ('DLQ_Tool.py', '.'),
        ('bill_hunter.py', '.'),
        ('shipping_map.py', '.'),
        ('hedis.py', '.'),
        ('icon.icns', '.'),  # Lowercase to match code
        # Also include with original name in case that's what you have
        # ('Icon.icns', '.'),
    ],
    hiddenimports=[
        'auth_integration',  # Auth integration
        'user_managment',  # User management tab
        'user_audit',  # User audit logs tab
        'eligibility_tool',
        'configurator_tool', 
        'multisearch_tool',
        'Cron_tool',
        'Base64_Tool',
        'DLQ_Tool',
        'bill_hunter',
        'shipping_map',
        'hedis',
        'pandas',
        'openpyxl',
        'dateutil',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        '_tkinter',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'keyring.backends.macOS',
    ],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=['hook-keyring.py'],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HelloToolbelt',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
app = BUNDLE(
    exe,
    name='HelloToolbelt.app',
    icon='icon.icns',  # Lowercase to match
    bundle_identifier='com.helloheart.hellotoolbelt',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
        'CFBundleDisplayName': 'HelloToolbelt',
        'CFBundleName': 'HelloToolbelt',
    },
)
