# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

add_datas = [
    ('/home/charles/Eluvk-project/top-dw-agent/agent', 'agent'),
    ('/home/charles/Eluvk-project/top-dw-agent/common', 'common')
]

a = Analysis(['main.py'],
             pathex=['/home/charles/Eluvk-project/top-dw-agent'],
             binaries=[],
             datas=add_datas,
             hiddenimports=["setproctitle"],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='topargus-agent',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )