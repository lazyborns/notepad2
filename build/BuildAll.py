import os.path
import time
import shutil
import subprocess

buildFolder = os.getcwd()
buildEnv = {}

notepad2_config_h = os.path.abspath('../src/config.h')
metapath_config_h = os.path.abspath('../metapath/src/config.h')
projectDir = os.path.abspath('VS2017')
localeDir = os.path.abspath('../locale')
notepad2_rc = os.path.abspath('../src/Notepad2.rc')
metapath_rc = os.path.abspath('../metapath/src/metapath.rc')

activeLocaleList = ['i18n', 'en', 'it', 'ja', 'ko', 'zh-Hans', 'zh-Hant']
defaultConfig = {
	'NP2_ENABLE_CUSTOMIZE_TOOLBAR_LABELS': 0,
	'NP2_ENABLE_HIDPI_IMAGE_RESOURCE': 1,

	'NP2_ENABLE_DOT_LOG_FEATURE': 0,

	'NP2_ENABLE_APP_LOCALIZATION_DLL': 1,
	'NP2_ENABLE_TEST_LOCALIZATION_LAYOUT': 0,
	'NP2_ENABLE_LOCALIZE_LEXER_NAME': 1,
	'NP2_ENABLE_LOCALIZE_STYLE_NAME': 1,
}

def get_locale_override_config(locale, hd):
	override = {}
	if not hd:
		override['NP2_ENABLE_HIDPI_IMAGE_RESOURCE'] = 0
	if locale != 'i18n':
		override['NP2_ENABLE_APP_LOCALIZATION_DLL'] = 0
	if locale == 'en':
		override['NP2_ENABLE_LOCALIZE_LEXER_NAME'] = 0
		override['NP2_ENABLE_LOCALIZE_STYLE_NAME'] = 0
	return override

def update_raw_file(path, content):
	with open(path, 'rb') as fd:
		origin = fd.read()
		if origin == content:
			return
	print('update:', path)
	with open(path, 'wb') as fd:
		fd.write(content)

def update_config_file(override):
	config = defaultConfig.copy()
	config.update(override)
	output = ['#pragma once']
	output.append('')
	for key, value in config.items():
		output.append(f'#define {key}\t\t{value}')
	output.append('')
	content = '\n'.join(output).encode('utf-8')
	update_raw_file(notepad2_config_h, content)
	update_raw_file(metapath_config_h, content)


def format_duration(duration):
	second = int(duration)
	duration = round((duration - second)*1000)
	hour, second = divmod(second, 60*60)
	minute, second = divmod(second, 60)
	return f'{hour}:{minute:02d}:{second:02d}.{duration:03d}'

def run_command_in_folder(command, folder):
	print(f'run: {command} @ {folder}')
	os.chdir(folder)
	os.system(command)

def find_7z_path():
	path = shutil.which('7z.exe')
	if path:
		return path

	import winreg
	for program in ['7-Zip', '7-Zip-Zstandard']:
		try:
			key = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\{program}", access=winreg.KEY_READ)
			path, rtype = winreg.QueryValueEx(key, 'Path')
			if rtype == winreg.REG_SZ and os.path.isdir(path):
				path = os.path.join(path, '7z.exe')
				if os.path.isfile(path):
					return path
		except OSError:
			pass
	return '7z.exe'

def zip_folder_inner(folder, output):
	if os.path.exists(output):
		os.remove(output)
	os.chdir(folder)
	program = buildEnv['7z_path']
	with subprocess.Popen([program, 'a', '-tzip', '-mx=9', output], stdout=subprocess.DEVNULL) as proc:
		retcode = proc.poll()
		if retcode:
			print('make zip fail:', retcode, os.path.basename(output))

def get_app_version():
	major, minor, build, reversion = ['']*4
	path = os.path.join(buildFolder, '../src/Version.h')
	with open(path, encoding='utf-8') as fd:
		for line in fd.read().splitlines():
			if line.startswith('#define VERSION_MAJOR'):
				major = line.split()[2]
				break

	path = os.path.join(buildFolder, '../src/VersionRev.h')
	with open(path, encoding='utf-8') as fd:
		for line in fd.read().splitlines():
			items = line.split()
			if len(items) > 2:
				key = items[1]
				value = items[2]
				if key == 'VERSION_MINOR':
					minor = value
				elif key == 'VERSION_BUILD':
					build = value
				elif key == 'VERSION_REV':
					reversion = value
	return f'v{major}.{minor}.{build}r{reversion}'

def prepare_build_environment():
	app_version = get_app_version()
	buildEnv['app_version'] = app_version
	print('app version:', app_version)

	path = find_7z_path()
	print('7z path:', path)
	buildEnv['7z_path'] = path

	# copy common zip files once
	zipDir = os.path.join(buildFolder, 'temp_zip_dir')
	buildEnv['temp_zip_dir'] = zipDir
	if not os.path.exists(zipDir):
		os.makedirs(zipDir)
	for path in ['../License.txt',
		'../doc/Notepad2.ini',
		'../doc/Notepad2 DarkTheme.ini',
		'../metapath/doc/metapath.ini']:
		target = os.path.join(zipDir, os.path.basename(path))
		if not os.path.exists(target):
			src = os.path.join(buildFolder, path)
			shutil.copyfile(src, target)

	# backup resource files once
	backupDir = os.path.join(localeDir, 'en')
	if not os.path.exists(backupDir):
		os.makedirs(backupDir)
		shutil.copyfile(metapath_rc, os.path.join(backupDir, 'metapath.rc'))
		shutil.copyfile(notepad2_rc, os.path.join(backupDir, 'Notepad2.rc'))

def clean_build_temporary():
	backupDir = os.path.join(localeDir, 'en')
	if os.path.exists(backupDir):
		try:
			shutil.rmtree(backupDir)
		except PermissionError:
			pass
	zipDir = buildEnv['temp_zip_dir']
	if os.path.exists(zipDir):
		try:
			shutil.rmtree(zipDir)
		except PermissionError:
			pass

# copy from locale/Locale.py
def restore_resource_include_path(path, metapath):
	with open(path, encoding='utf-8', newline='\n') as fd:
		doc = fd.read()
	if metapath:
		# include path
		doc = doc.replace('../../metapath/src/', '')
		# resource path
		doc = doc.replace(r'..\\metapath\\', '')
	else:
		# include path
		doc = doc.replace('../../src/', '')
		# resource path
		doc = doc.replace(r'..\\..\\res', r'..\\res')

	with open(path, 'w', encoding='utf-8', newline='\n') as fd:
		fd.write(doc)

def copy_back_localized_resources(language):
	print(f'Locale: copy back localized resources for {language}.')
	folder = os.path.join(localeDir, language)
	shutil.copyfile(os.path.join(folder, 'metapath.rc'), metapath_rc)
	shutil.copyfile(os.path.join(folder, 'Notepad2.rc'), notepad2_rc)
	restore_resource_include_path(metapath_rc, True)
	restore_resource_include_path(notepad2_rc, False)

def build_main_project(arch):
	command = f'call build.bat Build {arch} Release'
	run_command_in_folder(command, projectDir)

def build_locale_project(arch):
	command = f'call build.bat Build {arch} Release'
	run_command_in_folder(command, localeDir)

def make_release_artifact(locale, suffix=''):
	app_version = buildEnv['app_version']
	zipDir = buildEnv['temp_zip_dir']
	outDir = os.path.join(buildFolder, 'bin', 'Release')
	for arch in ['ARM', 'ARM64', 'AVX2', 'Win32', 'x64']:
		if arch == 'ARM' and locale not in ('i18n', 'en'):
			# 32-bit ARM is only built for i18n and en
			continue
		folder = os.path.join(outDir, arch)
		notepad2_exe = os.path.join(folder, 'Notepad2.exe')
		metapath_exe = os.path.join(folder, 'metapath.exe')
		if os.path.isfile(notepad2_exe) and os.path.isfile(metapath_exe):
			shutil.copyfile(notepad2_exe, os.path.join(zipDir, 'Notepad2.exe'))
			shutil.copyfile(metapath_exe, os.path.join(zipDir, 'metapath.exe'))
			target = os.path.join(zipDir, 'locale')
			if os.path.exists(target):
				shutil.rmtree(target)
			if locale == 'i18n':
				path = os.path.join(folder, 'locale')
				if os.path.isdir(path):
					shutil.copytree(path, target, copy_function=shutil.copyfile)
			name = f'Notepad2_{suffix + locale}_{arch}_{app_version}.zip'
			print('make:', name)
			path = os.path.join(buildFolder, name)
			zip_folder_inner(zipDir, path)
		else:
			print(f'{locale} {arch} build failure')

def build_release_artifact(hd, suffix=''):
	for locale in activeLocaleList:
		print('build:', hd, locale)
		override = get_locale_override_config(locale, hd)
		update_config_file(override)
		if locale in ('i18n', 'en'):
			build_main_project('all')
			if locale == 'i18n':
				build_locale_project('all')
		else:
			copy_back_localized_resources(locale)
			# 32-bit ARM is only built for i18n and en
			build_main_project('NoARM')
		make_release_artifact(locale, suffix)
	copy_back_localized_resources('en')

def build_all_release_artifact():
	print('project folder:', projectDir)
	print('build folder:', buildFolder)
	print('locale folder:', localeDir)
	startTime = time.perf_counter()
	prepare_build_environment()
	build_release_artifact(True, 'HD_')
	build_release_artifact(False)
	clean_build_temporary()
	endTime = time.perf_counter()
	print('total build time:', format_duration(endTime - startTime))

# https://cli.github.com/
# gh auth login
# gh release list -L 2
# gh release upload <tag> <files>
def upload_all_release_artifact(tag):
	files = []
	with os.scandir(buildFolder) as it:
		for entry in it:
			name = entry.name
			if entry.is_file() and name.endswith('.zip'):
				files.append(name)

	print('total artifact:', len(files))
	files = ' '.join(files)
	command = f'gh release upload {tag} {files}'
	startTime = time.perf_counter()
	run_command_in_folder(command, buildFolder)
	endTime = time.perf_counter()
	print('total upload time:', format_duration(endTime - startTime))

build_all_release_artifact()
#upload_all_release_artifact('')
