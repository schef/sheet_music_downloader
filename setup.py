import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sheet_music_downloader",
    version="1.0.0",
    author="schef",
    author_email="",
    description="Sheet music downloader",
    long_description=long_description,
    url="https://github.com/schef/sheet_music_downloader",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'sheet-music-downloader = sheet_music_downloader.main:run',
        ],
    },
    install_requires=[
        'selenium',
        'yt_dlp',
        'PyMuPDF',
    ],
)
