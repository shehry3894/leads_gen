# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, copy_metadata
import os

block_cipher = None

# Collect metadata and data for key packages
datas = []
binaries = []
hiddenimports = []

# Add metadata
datas += copy_metadata('streamlit')
datas += copy_metadata('pandas')
datas += copy_metadata('openpyxl')

# Collect all for major dependencies
for pkg in ['streamlit', 'openpyxl', 'pandas', 'requests', 'selenium', 'webdriver_manager', 'xlsxwriter']:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

# Add project modules as data
datas += [('scraper', 'scraper'), ('utils', 'utils'), ('input', 'input')]
datas += [('version.py', '.'), ('data_types.py', '.')]

# Add critical hidden imports
hiddenimports += [
    'importlib.metadata',
    'io',
    'logging',
    'logging.handlers',
    'os',
    'sys',
    'types',
    'pathlib',
    'pandas',
    'openpyxl',
    'selenium',
    'selenium.webdriver',
    'selenium.webdriver.chrome',
    'selenium.webdriver.chrome.service',
    'selenium.webdriver.chrome.options',
    'selenium.webdriver.common.by',
    'selenium.webdriver.common.keys',
    'selenium.webdriver.support',
    'selenium.webdriver.support.ui',
    'selenium.webdriver.support.expected_conditions',
    'selenium.common.exceptions',
    'requests',
    'xlsxwriter',
    'webdriver_manager',
    'webdriver_manager.chrome',
    'scraper',
    'scraper.driver',
    'scraper.search',
    'scraper.scroll',
    'scraper.scrape',
    'scraper.zooming',
    'utils',
    'utils.paths',
    'utils.logging_utils',
    'utils.demo_data',
    'utils.email_utils',
    'utils.files_and_dir_utils',
    'utils.printing_and_logging',
    'utils.selenium_utils',
    'utils.webservices',
    'input',
    'input.config',
    'version',
    'data_types',
]

a = Analysis(
    ['app.py'],  # Main entry point
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='leads_gen',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
