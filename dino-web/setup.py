import os

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

root = os.path.join(os.path.dirname(__file__), 'dinoweb')

def walk_dir(root, dir):
    for (dir, dirnames, filenames) in os.walk(os.path.join(root, dir)):
        for f in filenames:
            fp = os.path.join(dir, f)
            yield fp[len('dinoweb') + 1:]


setup(
    name='dino-web',
    version='0.9',
    description='',
    author='',
    author_email='',
    url='',
    install_requires=[
        "Pylons>=0.9.7",
    ],
    setup_requires=["PasteScript>=1.6.3"],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    test_suite='nose.collector',
    package_data={'dinoweb': list(walk_dir(root, 'probe-tools')) },
    zip_safe=False,
    paster_plugins=['PasteScript', 'Pylons'],
    entry_points="""
    [paste.app_factory]
    main = dinoweb.config.middleware:make_app

    [paste.app_install]
    main = pylons.util:PylonsInstaller
    """,
)
