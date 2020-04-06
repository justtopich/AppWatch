# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['src\\AppWatch.py'],
             pathex=['./src'],
             binaries=[],
             datas=[('README.md', 'CHANGES.md')],
             hiddenimports=['win32timezone', 'pkg_resources.py2_warn'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['dummy_thread', 'setuptools', 'cryptography', 'lib2to3', '_cffi_backend', 'win32ui', 'win32trace'],
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
          name='AppWatch',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True , version='version.txt')
