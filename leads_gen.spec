# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import copy_metadata

datas = [('/Volumes/data/Work/Google_Leads/leads_gen/app.py', '.'), ('leads_gen', 'leads_gen')]
binaries = []
hiddenimports = ['importlib.metadata', 'io.BytesIO', 'leads_gen.config.settings.TESTING', 'leads_gen.config.settings.TRIAL', 'leads_gen.core.data_normalization.deduplicate_dataframe', 'leads_gen.core.data_normalization.process_scraped_data', 'leads_gen.core.demo_data.get_demo_leads', 'leads_gen.licensing.fingerprint.generate_machine_fingerprint', 'leads_gen.licensing.license_manager.LicenseManager', 'leads_gen.scraper.driver.DriverInitError', 'leads_gen.scraper.driver.start_driver', 'leads_gen.scraper.scrape.scrape_business_data', 'leads_gen.scraper.scroll.scroll_results', 'leads_gen.scraper.search.search_maps', 'leads_gen.utils.logging_utils.configure_file_logging', 'leads_gen.utils.paths.get_ui_output_dir', 'leads_gen.version.__app_name__', 'leads_gen.version.__version__', 'logging', 'os', 'pandas', 'pathlib.Path', 'streamlit', 'subprocess', 'sys', 'time', 'leads_gen', 'leads_gen.scraper', 'leads_gen.utils', 'leads_gen.config', 'leads_gen.core', 'leads_gen.licensing']
datas += copy_metadata('streamlit')
tmp_ret = collect_all('streamlit')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('streamlit')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('openpyxl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pandas')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('requests')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('selenium')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('webdriver_manager')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('xlsxwriter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['/var/folders/5m/8w7r470s0kb6xk0fzb5_vd1w0000gn/T/tmpk2ofqtbm.py'],
    pathex=['.', './'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
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
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
