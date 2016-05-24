from setuptools import setup, find_packages

setup(name = 'pytknvim',
     version='0.1.2',
     description = 'tkinter text widget using neovim',
     url = 'https://github.com/timeyyy/pytknvim',
     author='timeyyy',
     author_email='tim_eichler@hotmail.com',
     license='BSD3',
     classifiers=[
         'Development Status :: 4 - Beta',
         'Intended Audience :: Developers',
         'License :: OSI Approved :: BSD License',
         'Programming Language :: Python :: 3',],
     keywords = 'tkinter text neovim vim edit',
     packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
     install_requires=['neovim>=0.1.3'],
     entry_points = {
         'console_scripts': [
             'pytknvim=pytknvim.tk_ui:main',],},)
