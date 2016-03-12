from distutils.core import setup

setup(name='wpathr',
      version='0.2',
      description='Path optimization tool for Windows',
      author='Ville Vainio',
      author_email='vivainio@gmail.com',
      url='https://github.com/vivainio/wpathr',
      packages=['wpathr'],
      setup_requires=['pickleshare']
      entry_points = {
        'console_scripts': [
            'wpp = wpathr.wpathr:main'
        ]
      }
     )
