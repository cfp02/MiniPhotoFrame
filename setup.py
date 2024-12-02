from setuptools import setup, find_packages

setup(
    name="mini_photo_frame",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'google-auth',
        'google-auth-oauthlib',
        'google-auth-httplib2',
        'google-api-python-client',
        'pillow',
        'screeninfo',
        'opencv-python',
        'pyinstaller',
    ],
    entry_points={
        'console_scripts': [
            'photo_frame=mini_photo_frame.main:main',
        ],
    },
) 