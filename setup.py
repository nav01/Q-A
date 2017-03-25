from setuptools import setup

requires = [
    'pyramid',
    'pyramid_chameleon',
]

setup(name='qa',
    install_requires=requires,
    entry_points="""\
    [paste.app_factory]
    main = qa:main
    """,
)
