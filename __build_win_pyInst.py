from subprocess import call
from datetime import datetime
from time import sleep


PACKAGE = "AppWatch"

def comile():
    curdate = datetime.now().strftime("%Y, %m, %d, ")
    fileVersion = "        StringStruct(u'FileVersion', u'build%s" % curdate.replace(', ', '') + "'),\n"
    prodVersion = "        StringStruct(u'ProductVersion', u'%s" % curdate + "attempt" + "')])\n"

    build=None
    lines=[]

    # чтение\разбор
    try:
        with open('version.txt','r') as file:
            for line in file.readlines():
                if "fileversion" in line.lower():
                    lines.append(fileVersion)
                elif "productversion" in line.lower():
                    if build == None:
                        buildStr = '# build=' + curdate.replace(', ', '') + ' ; 0\n'
                        prodVersion = prodVersion.replace('attempt', '0')
                    lines.append(prodVersion)
                    
                elif "# build" in line:
                    build=line.split('=')[1].split(' ; ')
                    build[1]=str(int(build[1])+1)
                    buildStr='# build='+build[0] +" ; " + build[1] +'\n' #build, attempt
                    prodVersion=prodVersion.replace('attempt',build[1])
                else:
                    lines.append(line)
    except Exception as e:
        input("can't read version.txt: %s" %e)
        return


    lines1 = []
    try:
        with open(f'src/__init__.py', 'r') as file:
            for line in file.readlines():
                if line.startswith("__version__"):
                    lines1.append('__version__ = "'+curdate.replace(', ','.')+build[1]+'"\n')
                else:
                    lines1.append(line)
    except Exception as e:
        input("can't read __init__.py: %s" % e)
        return

    # запись
    try:
        with open('version.txt','w') as file:
            file.write(buildStr)
            file.writelines(lines)

    except Exception as e:
        input("can't write version.txt: %s" %e)
        return

    try:
        with open(f'src/__init__.py','w') as file:
            file.writelines(lines1)

    except Exception as e:
        input(f"can't write src/__init__.py: %s" %e)
        return

    # сборка
    try:
    # pkg_resources.py2_warn только при setuptools 45 и pyinstaller 3.6
    #     call(f"pyinstaller -F --version-file=version.txt src/{PACKAGE}.py "
    #          f"--hidden-import=win32timezone "
    #          f"--hidden-import=pkg_resources.py2_warn "
    #          f"--clean "
    #          f"--distpath ./bin "
    #          f"--workpath ./src "
    #          f"--paths ./src"
    #     )
        call(f"pyinstaller -F --clean --workpath ./src --distpath ./bin {PACKAGE}.spec")
    except Exception as e:
        input("can't call pyinstaller: %s" %e)
        return

comile()
print('Done!')
sleep(2)