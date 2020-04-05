import setuptools
setuptools.setup(
    name="suggests",
    version="0.1.1",
    author='Ronald E. Robertson',
    author_email='rer@ronalderobertson.com',
    description="Algorithm auditing tools for search engine autocomplete",
    keywords="suggestions autocomplete google bing",
    url='http://github.com/gitronald/suggests',
    classifiers=['Programming Language :: Python :: 3',
                 'License :: OSI Approved :: MIT License'],
    packages=setuptools.find_packages(),
    install_requires=['requests', 'pandas', 'numpy', 'bs4'],
    python_requires='~=3.6',
    package_data={'': ['*.txt', '*.md']},
    license='MIT'
)
