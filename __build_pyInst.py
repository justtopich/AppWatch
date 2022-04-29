from datetime import datetime
from time import sleep
import os


PACKAGE = "AppWatch"

def comile():
    try:
        with open(f'src/__init__.py', 'r') as file:
            for line in file.readlines():
                if line.startswith("__version__"):
                    version = line[line.find('"') + 1:-2].strip()
                    break
    except Exception as e:
        input("can't read src/_init__.py: %s" % e)
        return

    lines = []
    try:
        with open('version.txt', 'r') as file:
            for line in file.readlines():
                if "fileversion" in line.lower():
                    lines.append(f"{line[:line.find('build') + 5]}{version.split('.')[-1]}'),\n")
                elif "productversion" in line.lower():
                    lines.append(f"{line[:line.find(', u') + 4]}{version}')])\n")
                else:
                    lines.append(line)
    except Exception as e:
        input("can't read version.txt: %s" % e)
        return

    try:
        with open('version.txt', 'w') as file:
            file.writelines(lines)
    except Exception as e:
        input("can't write version.txt: %s" % e)
        return

    # сборка
    try:
        # pyinstaller 4 need add -F arg, pyinstaller 5 no need
        os.system(f"pyinstaller --clean --distpath bin {PACKAGE}.spec")
            # pkg_resources.py2_warn только при setuptools 45 и pyinstaller 3.6
            # os.system(
                 # f"pyinstaller -F "
                 # f"src/{PACKAGE}.py "
                 # f"--version-file=version.txt "
                 # f"--hidden-import=win32timezone "
                 # f"--hidden-import=pkg_resources.py2_warn "
                 # f"--clean "
                 # f"--distpath bin "
                 # f"--paths src "
                 # f"--name={PACKAGE} "
                 # f"--add-data=docs/README.md:docs "
                 # f"--add-data=docs/CHANGES.md:docs "
                 # f"--add-data=docs/Connectors.md:docs "
                 # f"--add-data=src/notifier/chat_ava.ico:notifier "
                 # f"--hidden-import=win32timezone "
                 # f"--hidden-import=pkg_resources.py2_warn "
                 # f"--hidden-import=plyer.platforms.win.notification "
                 # f"--exclude-module=dummy_thread "
                 # f"--exclude-module=setuptools "
                 # f"--exclude-module=cryptography "
                 # f"--exclude-module=lib2to3 "
                 # f"--exclude-module=_cffi_backend "
                 # f"--exclude-module=win32ui "
                 # f"--exclude-module=win32trace "
            # )
        
    except Exception as e:
        input("can't call pyinstaller: %s" % e)
        return


comile()
print('Done!')
sleep(2)
