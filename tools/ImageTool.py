import os.path
import re

from Bitmap import *

def save_bitmap(bmp, path, colorDepth=None):
	ext = os.path.splitext(path)[1].lower()
	if ext == '.bmp':
		bmp.save(path, colorDepth)
	else:
		img = bmp.toImage(colorDepth)
		img.save(path)

def dump_bitmap(path):
	print('dump bitmap:', path)
	bmp = Bitmap.fromFile(path)
	print(bmp.fileHeader)
	print(bmp.infoHeader)
	print('colorCount:', bmp.colorUsed)

	data_path = path + '.data'
	print('write:', data_path, len(bmp.data))
	with open(data_path, 'wb') as fd:
		fd.write(bmp.data)

	dump_path = os.path.splitext(path)[0] + '-dump.bmp'
	print('write:', dump_path)
	bmp.save(dump_path)

def quantize_external(path, out_path, colorCount, method):
	temp = f'{out_path}-{method.name}{colorCount}.png'
	if method == QuantizeMethod.PngQuant:
		# https://pngquant.org/
		command = f'pngquant --force --verbose {colorCount} --output "{temp}" "{path}"'
	elif method == QuantizeMethod.ImageMagick:
		# https://imagemagick.org/script/command-line-options.php#colors
		command = f'magick "{path}" -verbose -colors {colorCount} "{temp}"'
	print('Run:', command)
	os.system(command)
	bmp = Bitmap.fromFileEx(temp)
	#os.remove(temp);
	return bmp

def convert_image(path, out_path=None, colorDepth=None, quantize=True, method=None):
	if not out_path:
		name, ext = os.path.splitext(path)
		if ext.lower() == '.bmp':
			out_path = name + '-converted.bmp'
		else:
			out_path = name + '.bmp'

	print(f'convert image: {path} => {out_path}')
	bmp = Bitmap.fromFileEx(path)
	#bmp.resolution = (96, 96)
	if quantize and colorDepth in (1, 4, 8):
		colorCount = 1 << colorDepth
		current = bmp.colorUsed
		if current > colorCount:
			if method and method > QuantizeMethod.Naive:
				bmp = quantize_external(path, out_path, colorCount, method)
			else:
				bmp = bmp.quantize(colorCount, method, False)
			name = method.name if method != None else 'Default'
			count = bmp.colorUsed
			print(f'quantize image {name}: {current} => {count}')
	save_bitmap(bmp, out_path, colorDepth)


def concat_images(horizontal, paths, out_path, colorDepth=None):
	if horizontal:
		print('concat horizontal:', ', '.join(paths), '=>', out_path)
	else:
		print('concat vertical:', ', '.join(paths), '=>', out_path)

	bmps = []
	for path in paths:
		bmp = Bitmap.fromFileEx(path)
		bmps.append(bmp)

	if horizontal:
		bmp = Bitmap.concatHorizontal(bmps)
	else:
		bmp = Bitmap.concatVertical(bmps)
	save_bitmap(bmp, out_path, colorDepth)

def concat_horizontal(paths, out_path, colorDepth=None):
	concat_images(True, paths, out_path, colorDepth)

def concat_vertical(paths, out_path, colorDepth=None):
	concat_images(False, paths, out_path, colorDepth)


def save_bitmap_list(bmps, out_path, ext):
	if not os.path.exists(out_path):
		os.makedirs(out_path)
	for index, bmp in enumerate(bmps):
		path = os.path.join(out_path, f'{index}{ext}')
		save_bitmap(bmp, path)

def _parse_split_dims(item):
	items = item.split()
	dims = []
	for item in items:
		m = re.match(r'(\d+)(x(\d+))?', item)
		if m:
			g = m.groups()
			size = int(g[0])
			count = g[2]
			if count:
				dims.extend([size] * int(count))
			else:
				dims.append(size)
		else:
			break
	return dims

def split_image(horizontal, path, dims=None, out_path=None, ext=None):
	name, old_ext = os.path.splitext(path)
	if not out_path:
		out_path = name + '-split'
	if not ext:
		ext = old_ext

	if isinstance(dims, str):
		dims = _parse_split_dims(dims)
	if horizontal:
		print('split horizontal:', path, dims, '=>', out_path)
	else:
		print('split vertical:', path, dims, '=>', out_path)

	bmp = Bitmap.fromFileEx(path)
	if horizontal:
		bmps = bmp.splitHorizontal(dims)
	else:
		bmps = bmp.splitVertical(dims)
	save_bitmap_list(bmps, out_path, ext)

def split_horizontal(path, dims=None, out_path=None, ext=None):
	split_image(True, path, dims, out_path, ext)

def split_vertical(path, dims=None, out_path=None, ext=None):
	split_image(False, path, dims, out_path, ext)


def flip_image(horizontal, path, out_path=None):
	if not out_path:
		name, ext = os.path.splitext(path)
		out_path = name + '-flip' + ext
	if horizontal:
		print('flip horizontal:', path, '=>', out_path)
	else:
		print('flip vertical:', path, '=>', out_path)

	bmp = Bitmap.fromFileEx(path)
	if horizontal:
		bmp = bmp.flipHorizontal()
	else:
		bmp = bmp.flipVertical()
	save_bitmap(bmp, out_path)

def flip_horizontal(path, out_path=None):
	flip_image(True, path, out_path)

def flip_vertical(path, out_path=None):
	flip_image(False, path, out_path)


def resize_toolbar_bitmap_whole(path, percent, method=ResizeMethod.Bicubic, out_path=None):
	bmp = Bitmap.fromFileEx(path)

	width, height = bmp.size
	width = round(width * percent/100)
	height = round(height * percent/100)
	size = (width, height)

	print(f'resize toolbar bitmap {percent} {method.name}: {bmp.size} => {size}')

	bmp = bmp.resize(size, method=method)
	if not out_path:
		name, ext = os.path.splitext(path)
		out_path = f"{name}_{height}_{percent}_{method.name}{ext}"
	save_bitmap(bmp, out_path)

def resize_toolbar_bitmap_each(path, percent, method=ResizeMethod.Bicubic, out_path=None):
	bmp = Bitmap.fromFileEx(path)
	bmps = bmp.splitHorizontal()

	width, height = bmps[0].size
	width = round(width * percent/100)
	height = round(height * percent/100)
	size = (width, height)

	print(f'resize toolbar bitmap {percent} {method.name}: {bmps[0].size} => {size}')

	resized = []
	for bmp in bmps:
		bmp = bmp.resize(size, method=method)
		resized.append(bmp)

	bmp = Bitmap.concatHorizontal(resized)
	if not out_path:
		name, ext = os.path.splitext(path)
		out_path = f"{name}_{height}_{percent}_{method.name}{ext}"
	save_bitmap(bmp, out_path)

resize_toolbar_bitmap = resize_toolbar_bitmap_whole

def make_metapath_toolbar_bitmap(size):
	images = f'images/metapath/{size}x{size}'
	common = f'images/{size}x{size}'
	concat_horizontal([
		f'{images}/Back.png',			# IDT_HISTORY_BACK
		f'{images}/Forward.png',		# IDT_HISTORY_FORWARD
		f'{images}/UpperDirectory.png',	# IDT_UP_DIR
		f'{images}/RootDirectory.png',	# IDT_ROOT_DIR
		f'{common}/OpenFav.png',		# IDT_VIEW_FAVORITES
		f'{images}/PreviousFile.png',	# IDT_FILE_PREV
		f'{images}/NextFile.png',		# IDT_FILE_NEXT
		f'{common}/Launch.png',			# IDT_FILE_RUN
		f'{images}/Quickview.png',		# IDT_FILE_QUICKVIEW
		f'{common}/SaveAs.png',			# IDT_FILE_SAVEAS
		f'{common}/Copy.png',			# IDT_FILE_COPYMOVE
		f'{images}/DeleteRecycleBin.png',# IDT_FILE_DELETE_RECYCLE
		f'{common}/Delete.png',			# IDT_FILE_DELETE_PERM
		f'{images}/DeleteFilter.png',	# IDT_VIEW_FILTER TB_DEL_FILTER_BMP
		f'{images}/Filter.png',			# IDT_VIEW_FILTER TB_ADD_FILTER_BMP
	], f'Toolbar{size}.bmp')

def make_all_metapath_toolbar_bitmap():
	for size in (16, 24, 32, 40, 48):
		make_metapath_toolbar_bitmap(size)

def make_notepad2_toolbar_bitmap(size):
	images = f'images/{size}x{size}'
	concat_horizontal([
		f'{images}/New.png',			# IDT_FILE_NEW
		f'{images}/Open.png',			# IDT_FILE_OPEN
		f'{images}/Browse.png',			# IDT_FILE_BROWSE
		f'{images}/Save.png',			# IDT_FILE_SAVE
		f'{images}/Undo.png',			# IDT_EDIT_UNDO
		f'{images}/Redo.png',			# IDT_EDIT_REDO
		f'{images}/Cut.png',			# IDT_EDIT_CUT
		f'{images}/Copy.png',			# IDT_EDIT_COPY
		f'{images}/Paste.png',			# IDT_EDIT_PASTE
		f'{images}/Find.png',			# IDT_EDIT_FIND
		f'{images}/Replace.png',		# IDT_EDIT_REPLACE
		f'{images}/WordWrap.png',		# IDT_VIEW_WORDWRAP
		f'{images}/ZoomIn.png',			# IDT_VIEW_ZOOMIN
		f'{images}/ZoomOut.png',		# IDT_VIEW_ZOOMOUT
		f'{images}/Scheme.png',			# IDT_VIEW_SCHEME
		f'{images}/SchemeConfig.png',	# IDT_VIEW_SCHEMECONFIG
		f'{images}/Exit.png',			# IDT_FILE_EXIT
		f'{images}/SaveAs.png',			# IDT_FILE_SAVEAS
		f'{images}/SaveCopy.png',		# IDT_FILE_SAVECOPY
		f'{images}/Delete.png',			# IDT_EDIT_DELETE
		f'{images}/Print.png',			# IDT_FILE_PRINT
		f'{images}/OpenFav.png',		# IDT_FILE_OPENFAV
		f'{images}/AddToFav.png',		# IDT_FILE_ADDTOFAV
		f'{images}/ToggleFolds.png',	# IDT_VIEW_TOGGLEFOLDS
		f'{images}/Launch.png',			# IDT_FILE_LAUNCH
		f'{images}/AlwaysOnTop.png',	# IDT_VIEW_ALWAYSONTOP
	], f'Toolbar{size}.bmp')

def make_all_notepad2_toolbar_bitmap():
	for size in (16, 24, 32, 40, 48):
		make_notepad2_toolbar_bitmap(size)

def make_other_bitmap():
	for size in (16, 24, 32, 40, 48):
		colorDepth = 24 if size == 16 else 8
		convert_image(f'images/{size}x{size}/Open.png', f'OpenFolder{size}.bmp', colorDepth)

	for size in (16, 24, 32, 40, 48):
		images = f'images/{size}x{size}'
		convert_image(f'{images}/Next.png', f'Next{size}.bmp', 4, False)
		convert_image(f'{images}/Prev.png', f'Prev{size}.bmp', 4, False)

	for size in (16, 24, 32, 40, 48):
		colorDepth = 24 if size == 16 else 8
		images = f'images/{size}x{size}'
		concat_horizontal([f'{images}/Encoding.png', f'{images}/EncodingGray.png'], f'Encoding{size}.bmp', colorDepth)

#make_all_metapath_toolbar_bitmap()
#make_all_notepad2_toolbar_bitmap()
#make_other_bitmap()

#convert_image('images/16x16/Open.png', 'OpenFolder16.bmp', 4, QuantizeMethod.PngQuant)

#concat_horizontal(['../res/Toolbar.bmp', 'images/16x16/AlwaysOnTop.png'], 'Toolbar.bmp')
#split_horizontal('Toolbar.bmp', '16x40')

#resize_toolbar_bitmap('../res/Toolbar.bmp', 200, ResizeMethod.Nearest)
#resize_toolbar_bitmap('../res/Toolbar.bmp', 200, ResizeMethod.Bilinear)
#resize_toolbar_bitmap('../res/Toolbar.bmp', 200, ResizeMethod.Bicubic)
#resize_toolbar_bitmap('../res/Toolbar.bmp', 200, ResizeMethod.Lanczos)
