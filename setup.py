from distutils.core import setup

setup(name='wpathr',
      version='0.4.0',
      description='Path optimization tool and command runner for Windows',
      author='Ville Vainio',
      author_email='vivainio@gmail.com',
      url='https://github.com/vivainio/wpathr',
      packages=['wpathr'],
      install_requires=['pickleshare', 'argp'],
      entry_points = {
        'console_scripts': [
            'wpp = wpathr.wpathr:main'
        ]
      }
     )
