#	etcbuild - Embedded Toolchain build scripts
#	Copyright (C) 2020-2020 Johannes Bauer
#
#	This file is part of etcbuild.
#
#	etcbuild is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	etcbuild is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with etcbuild; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import os
import sys
import json
import hashlib
import requests
import contextlib

class PackageManagerException(Exception): pass
class PackageNameNotPresentException(PackageManagerException): pass
class PackageVersionNotPresentException(PackageManagerException): pass
class PackageDownloadFailedException(PackageManagerException): pass

class PackageManager():
	def __init__(self, package_definition_filename, package_directory):
		self._package_definition_filename = package_definition_filename
		with open(package_definition_filename) as f:
			self._pkgs = json.load(f)
		self._package_dir = os.path.realpath(os.path.expanduser(package_directory))
		with contextlib.suppress(FileExistsError):
			os.makedirs(self._package_dir)

	def get(self, pkgname, version = None):
		if pkgname not in self._pkgs:
			raise PackageNameNotPresentException("No such package name in %s: \"%s\"" % (self._package_definition_filename, pkgname))
		if version is not None:
			# Explicit version selected
			pkgs_by_version = { pkg["version"]: pkg for pkg in self._pkgs[pkgname] }
			if version not in pkgs_by_version:
				raise PackageVersionNotPresentException("No such version for \"%s\" in %s: %s" % (pkgname, self._package_definition_filename, version))
			pkg = pkgs_by_version[version]
		else:
			# Use latest version
			pkg = self._pkgs[pkgname][-1]

		pkg["uri"] = pkg["uri"].replace("{{version}}", pkg["version"])
		pkg.update({
			"pkgname":			pkgname,
			"local_filename":	self._package_dir + "/" + os.path.basename(pkg["uri"]),
		})
		return pkg

	@staticmethod
	def _get_hashval(filename):
		hashval = hashlib.sha384()
		with open(filename, "rb") as f:
			while True:
				chunk = f.read(1024 * 1024)
				if len(chunk) == 0:
					break
				hashval.update(chunk)
		return hashval.hexdigest()

	def is_present(self, pkg, delete_wrong_hash = True):
		if not os.path.exists(pkg["local_filename"]):
			return False

		# File exists, check hash value
		hashval = self._get_hashval(pkg["local_filename"])
		if hashval != pkg["sha384"]:
			# Hash value wrong. Erase file and return non-existent.
			if delete_wrong_hash:
				os.unlink(pkg["local_filename"])
			return False

		# Hash value correct.
		return True

	def download(self, pkg):
		with open(pkg["local_filename"], "wb") as f, requests.get(pkg["uri"], stream = True) as request:
			for chunk in request.iter_content(chunk_size = 1024 * 1024):
				f.write(chunk)

	def retrieve(self, pkg, verify = True):
		if self.is_present(pkg):
			return
		self.download(pkg)
		if not self.is_present(pkg, delete_wrong_hash = verify):
			if verify:
				raise PackageDownloadFailedException("Could not successfully verify download of package %s / version %s; maybe file has changed on the server?" % (pkg["pkgname"], pkg["version"]))
			else:
				print("Warning: Package %s / version %s could not be verified. Hash value: %s" % (pkg["pkgname"], pkg["version"], self._get_hashval(pkg["local_filename"])), file = sys.stderr)


if __name__ == "__main__":
	pkgman = PackageManager("packages.json", "packages/")
#	print(pkgman.present("foo", "1.2.3"))
#	print(pkgman.get("gcc", "1.2.3"))
#	print(pkgman.get("gcc"))
	print(pkgman.retrieve(pkgman.get("binutils"), verify = False))
