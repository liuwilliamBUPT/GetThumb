# -*- coding:utf-8 -*-

from setuptools import setup, find_packages

VERSION = '0.2.3'

setup(name='GetThumbnails',
      version=VERSION,
      description="A FFmpeg based thumbnails tool written by Python.",
      long_description='Find more in https://github.com/liuwilliamBUPT/GetThumb',
      classifiers=[],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='python FFmpeg thumbnails',
      author='William Liu',
      author_email='liuwilliam.zh@gmail.com',
      url='https://github.com/liuwilliamBUPT/GetThumb',
      license='GPL v3.0',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=True,
      install_requires=[],
      entry_points={
        'console_scripts': [
            'GetThumbnails = thumbnails.main:main'
        ]
      },
)