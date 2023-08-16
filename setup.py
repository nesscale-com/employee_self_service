from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in employee_self_service/__init__.py
from employee_self_service import __version__ as version

setup(
	name="employee_self_service",
	version=version,
	description="Employee Self Service",
	author="Nesscale Solutions Private Limited",
	author_email="info@nesscale.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
