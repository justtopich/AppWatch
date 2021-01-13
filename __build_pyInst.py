from subprocess import call
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
        # pkg_resources.py2_warn только при setuptools 45 и pyinstaller 3.6
        #     call(f"pyinstaller -F --version-file=version.txt src/{PACKAGE}.py "
        #          f"--hidden-import=win32timezone "
        #          f"--hidden-import=pkg_resources.py2_warn "
        #          f"--clean "
        #          f"--distpath bin "
        #          f"--workpath src "
        #          f"--paths src"
        #     )
        os.system(f"pyinstaller -F --clean --workpath src --distpath bin {PACKAGE}.spec")
    except Exception as e:
        input("can't call pyinstaller: %s" % e)
        return


comile()
print('Done!')
sleep(2)
