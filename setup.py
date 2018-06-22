#!/usr/bin/env python
# -*- coding: utf-8 -*-

# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
from shutil import which, copyfile
from subprocess import check_output, CalledProcessError

ARCH = 'x64'
VERSION = 3.6
PACKAGES = ['conda', 'pip', 'wheel', 'setuptools', 'pandas']
PYTHONNET = 'https://github.com/QuantConnect/pythonnet'
README = 'https://github.com/QuantConnect/Lean#installation-instructions'
MACOS = sys.platform == "darwin"
WIN32 = sys.platform == "win32"
LINK = 'https://www.microsoft.com/en-us/download/details.aspx?id=44266'
if MACOS: LINK = 'http://macappstore.org/pkg-config/'

class PythonSupport:

    def __init__(self):
        self.print_header()
        self.check_requirements()
        self.is_shared = self.macOS_settings()
        self.target = self.get_target_path()

    def print_header(self):
        extra = ''''''
        if WIN32:
            extra = f'''
        - Visual C++ for Python: {LINK}'''
        if MACOS:
            extra = f'''
        - pkg-config: {LINK}'''

        print(f'''
    Python support in Lean with pythonnet
    =====================================

    Prerequisites:
        - LEAN: {README}
        - Python {VERSION} {ARCH}{extra}
        - git
        - pip

    It will update {', '.join(PACKAGES)} packages.
    ''')

    def check_requirements(self):
        version = sys.version_info.major + sys.version_info.minor / 10
        arch = "x64" if sys.maxsize > 2**32 else "x86"
        if version != VERSION or arch != ARCH :
            exit(f'Python {VERSION} {ARCH} is required: version {version} {arch} found.')

        if which('git') is None:
            exit('Git is required and not found in the path. Link to install: https://git-scm.com/downloads')

        if which('pip') is None:
            exit('pip is required and not found in the path.')
            
    def macOS_settings(self):
        
        if not MACOS:
            return True
    
        if which('pkg-config') is None:
            exit(f'pkg-config is required and not found in path. Link to install: {LINK}')

        lib = '/Library/Frameworks/Mono.framework/Versions/Current/lib'
        
        # Create a symlink of framework lib/mono to python lib/mono
        dst = os.path.join(os.path.dirname(sys.executable)[:-3] + 'lib', 'mono')
        if os.path.exists(dst): os.remove(dst)
        os.symlink(os.path.join(lib, 'mono'), dst)

        paths = [path for path, dirs, files in os.walk(lib) if 'mono-2.pc' in files]
        os.environ['PKG_CONFIG_PATH'] = ':'.join(paths)
        
        if len(paths) == 0:
           exit(f'Could not find "mono-2.pc" in "{lib}" tree.')

        from sysconfig import get_config_var
        return get_config_var('Py_ENABLE_SHARED')

    def get_target_path(self):

        for path, dirs, files in os.walk('packages'):
            if 'Python.Runtime.dll' in files:
                path = os.path.join(os.getcwd(), path, 'Python.Runtime.dll')
                ori = path[0:-4] + '.ori'

                # Save the original file
                if not os.path.exists(ori):
                    os.rename(path, ori)
                    copyfile(ori, path)

                return path

        exit(f'Python.Runtime.dll not found in packages tree.{os.linesep}Please restore Nuget packages ({README})')

    def update_package_dll(self):
        
        try:
            if self.is_shared:
                import clr
                path = os.path.dirname(clr.__file__)
                file = os.path.join(path, 'Python.Runtime.dll')
            else:
                path = os.path.dirname(os.path.dirname(self.target))
                file = os.path.join(path, 'build', 'Python.Runtime.mac')
            
            copyfile(file, self.target)

            exit('Please REBUILD Lean solution to complete pythonnet setup.')
            
        except Exception as e:
            exit(f'Python.Runtime.dll not found in site-packages directories. Reason: {e}')

    def install_packages(self):
        
        print('''
    Install/updates required packages
    ---------------------------------
    ''')
        conda = which('conda')
        if conda is not None:
            pkgs = self.get_pkgs([conda])
            for pkg in PACKAGES:
                cmd = 'update' if pkg in pkgs else 'install'
                self._check_output([conda, cmd, '-y', pkg])
            print(f'[conda] Successfully installed/updated: {", ".join(self.get_pkgs([conda]))}')
        else:
            cmd = [sys.executable, '-m', 'pip', 'install', '-U'] + PACKAGES[1:]
            self._check_output(cmd)
            print(f'[ pip ] Successfully installed/updated: {", ".join(self.get_pkgs(cmd[0:3]))}')
        
    def get_pkgs(self, cmd):
        cmd.append('list')
        pkgs = self._check_output(cmd)[-1]
        pkgs = [pkg[:pkg.find(' ')].strip() for pkg in pkgs.splitlines()]
        return set(PACKAGES) & set(pkgs)
     
    def pythonnet_install(self):

        print('''
    Install/updates pythonnet
    -------------------------
    ''')
        cmd = [sys.executable, '-m', 'pip', 'install', '-U', 'git+' + PYTHONNET]
        return self._check_output(cmd)

    def _check_output(self, cmd):
        try:
            cmd.append(check_output(cmd).decode('UTF-8'))
        except CalledProcessError as e:
            exit(os.linesep.join([str(x)[2:-1] for x in e.output.splitlines()]))
        return cmd

if __name__ == "__main__":

    pythonSupport = PythonSupport()

    # Installs/updates packages required for pythonnet and Lean
    pythonSupport.install_packages()
    
    # Installs/updates pythonnet
    result = pythonSupport.pythonnet_install()

    # If pythonnet is installed, copy the file to Lean packages folder
    if result is not None:
        pythonSupport.update_package_dll()
    elif WIN32:
        exit(f'Failed to install pythonnet. Please install Visual C++ for Python: {LINK}')
