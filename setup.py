from setuptools import setup

requires = [
    'deform',
    'passlib',
    'psycopg2',
    'pymongo',
    'pyramid',
    'pyramid_chameleon',
    'sqlalchemy',
]

setup(name='qa',
    install_requires=requires,
    entry_points="""\
    [paste.app_factory]
    main = qa:main
    """,
)
