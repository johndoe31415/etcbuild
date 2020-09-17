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
import shutil
import subprocess
from WorkDir import WorkDir

class NoBuilderPresentException(Exception): pass

class GenericBuilder():
	def __init__(self, factory, pkg, flags):
		self._factory = factory
		self._pkg = pkg
		self._flags = flags
		self._builddir = "/tmp/etcbuild/%s" % (os.urandom(8).hex())
		os.makedirs(self._builddir)

	@property
	def flags(self):
		return self._flags

	@property
	def builddir(self):
		return self._builddir

	@property
	def extractdir(self):
		return self.builddir + "/" + self._pkg["pkgname"] + "-" + self._pkg["version"]

	def env(self, key):
		return self._factory.env[key]

	def unpack(self):
		source = self._pkg["local_filename"]
		if source.endswith(".tar.gz"):
			with WorkDir(self.builddir):
				self.execute([ "tar", "xzf", source ])
		else:
			raise NotImplementedError("Unpacking of file: %s" % (source))

	def build(self):
		raise NotImplementedError(__class__.__name__)

	def install(self, cwd = None):
		if cwd is None:
			cwd = self.extractdir
		with WorkDir(cwd):
			self.execute([ "make", "install" ])

	def execute(self, cmd):
		subprocess.check_call(cmd, env = self._factory.subprocess_env)

	def execute_make(self):
		self.execute([ "make", "-j%d" % (self._factory.concurrent_processes) ])

	def __enter__(self):
		return self

	def __exit__(self, *args):
		if self._factory.automatic_cleanup:
			shutil.rmtree(self._builddir)

class BuilderFactory():
	_REGISTRY = { }

	def __init__(self, environment, subprocess_environment, automatic_cleanup = True, concurrent_processes = 1):
		self._env = environment
		self._subprocess_env = subprocess_environment
		self._automatic_cleanup = automatic_cleanup
		self._concurrent_processes = concurrent_processes

	@property
	def env(self):
		return self._env

	@property
	def subprocess_env(self):
		return self._subprocess_env

	@property
	def automatic_cleanup(self):
		return self._automatic_cleanup

	@property
	def concurrent_processes(self):
		return self._concurrent_processes

	def get_builder(self, pkg, flags):
		if pkg["pkgname"] not in self._REGISTRY:
			raise NoBuilderPresentException("No builder present for package: %s" % (pkg["pkgname"]))
		builder_class = self._REGISTRY[pkg["pkgname"]]
		return builder_class(self, pkg, flags)

	@classmethod
	def register(cls, register_for):
		def decorator(builder_class):
			cls._REGISTRY[register_for] = builder_class
			return builder_class
		return decorator

@BuilderFactory.register("binutils")
class BinutilsBuilder(GenericBuilder):
	def build(self):
		with WorkDir(self.extractdir):
			configure_cmd = [ "./configure" ]
			configure_cmd += [ "--prefix=%s" % (self.env("prefix")) ]
			if self.env("target") in [ "7tdmi", "cortex-m0", "cortex-m1", "cortex-m3", "cortex-m4" ]:
				# ARM architectures
				configure_cmd += [ "--target=arm-none-eabi" ]
				if self.env("target") == "7tdmi":
					configure_cmd += [ "--enable-interwork", "--enable-multilib" ]
				else:
					configure_cmd += [ "--enable-thumb" ]
					configure_cmd += [ "--disable-interwork", "--disable-multilib" ]
			elif self.env("target") == "avr":
				configure_cmd += [ "--target=avr" ]
			elif self.env("target") == "blackfin":
				configure_cmd += [ "--target=bfin" ]
				configure_cmd += [ "--without-gnu-ld" ]
			else:
				configure_cmd += [ "--target=%s" % (self.env("target")) ]
			configure_cmd += [ "--disable-nls" ]
			configure_cmd += [ "--disable-libssp" ]
			self.execute(configure_cmd)
			self.execute_make()

@BuilderFactory.register("gcc")
class GCCBuilder(GenericBuilder):
	def build(self):
		with WorkDir(self.extractdir):
			os.mkdir("build")
			os.chdir("build")

			configure_cmd = [ "../configure" ]
			configure_cmd += [ "--prefix=%s" % (self.env("prefix")) ]
			if "prebuild" in self.flags:
				configure_cmd += [ "--without-headers" ]
			configure_cmd += [ "--with-gnu-ld", "--with-gnu-as" ]
			configure_cmd += [ "--with-dwarf2" ]
			configure_cmd += [ "--disable-werror" ]
			configure_cmd += [ "--disable-threads" ]
			configure_cmd += [ "--disable-nls" ]
			configure_cmd += [ "--disable-shared" ]
			configure_cmd += [ "--disable-libssp" ]
			configure_cmd += [ "--disable-libmudflap" ]
			configure_cmd += [ "--disable-libgomp" ]
			if self.env("target") in [ "7tdmi", "cortex-m0", "cortex-m1", "cortex-m3", "cortex-m4" ]:
				configure_cmd += [ "--target=arm-none-eabi" ]
				configure_cmd += [ "--with-newlib" ]
				if self.env("target") == "7tdmi":
					configure_cmd += [ "--enable-interwork", "--enable-multilib" ]
				if self.env("target") in [ "cortex-m0", "cortex-m3", "cortex-m4" ]:
					configure_cmd += [ "--with-cpu=" + self.env("target") ]
					configure_cmd += [ "--disable-interwork", "--disable-multilib" ]
				if self.env("target") in [ "cortex-m0", "cortex-m3" ]:
					configure_cmd += [ "--with-float=soft" ]
					configure_cmd += [ "--with-mode=thumb" ]
				elif self.env("target") in [ "cortex-m4" ]:
					configure_cmd += [ "--with-fpu=fpv4-sp-d16", "--with-float=hard" ]
					configure_cmd += [ "--with-mode=thumb" ]
			elif self.env("target") == "avr":
				configure_cmd += [ "--target=avr" ]

			if ("c++" in self.flags) and ("prebuild" not in self.flags):
				configure_cmd += [ "--enable-languages=c,c++" ]
			else:
				configure_cmd += [ "--enable-languages=c" ]
			configure_cmd += [ "--with-system-zlib" ]
			configure_cmd += [ "--enable-target-optspace" ]
			self.execute(configure_cmd)
			self.execute_make()

	def install(self):
		GenericBuilder.install(self, cwd = self.extractdir + "/build")
