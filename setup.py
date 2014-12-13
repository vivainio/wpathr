from distutils.core import setup

setup(name='wpathr',
      version='0.1.5',
      description='Path optimization tool for Windows',
      author='Ville Vainio',
      author_email='vivainio@gmail.com',
      url='https://github.com/vivainio/wpathr',
      packages=['wpathr'],
      entry_points = {
        'console_scripts': [
            'wpathr = wpathr.wpathr:main',
        ]
      }
     )
