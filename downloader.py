import pathlib
import threading
import urllib.request
import json
import os
from threading import Thread
import time
import math

#Считываем параметры скачивания
with open('loadParams.json') as json_file:
    loadParams = json.load(json_file)

#Формат пути, по которому лежат тайлы на сервере
tileUrlsOSM = [
	'https://tile.openstreetmap.org/{2}/{0}/{1}.png',
	'https://a.tile.openstreetmap.org/{2}/{0}/{1}.png',
	'https://b.tile.openstreetmap.org/{2}/{0}/{1}.png',
	'https://c.tile.openstreetmap.org/{2}/{0}/{1}.png'
]
tileUrlsWikimapia = [
	'https://maps.wikimedia.org/osm-intl/{2}/{0}/{1}.png?lang=ru'
]
tileUrlsSputnik = [
	'https://a.tilessputnik.ru/tiles/kmt2/{2}/{0}/{1}.png',
	'https://b.tilessputnik.ru/tiles/kmt2/{2}/{0}/{1}.png',
	'https://c.tilessputnik.ru/tiles/kmt2/{2}/{0}/{1}.png'
]
tileUrlsHere = [
	'https://1.base.maps.api.here.com/maptile/2.1/maptile/0e31a46a5a/normal.day/' + 
	'{2}/{0}/{1}}/256/png8?app_id=VgTVFr1a0ft1qGcLCVJ6&app_code=LJXqQ8ErW71UsRUK3R33Ow&lg=rus&ppi=72&pview=DEF'
]
tileUrlsYandex = [
	'https://vec01.maps.yandex.net/tiles?l=map&v=4.40&x={0}&y={1}&z={2}&lang=ru',
	'https://vec02.maps.yandex.net/tiles?l=map&v=4.40&x={0}&y={1}&z={2}&lang=ru',
	'https://vec03.maps.yandex.net/tiles?l=map&v=4.40&x={0}&y={1}&z={2}&lang=ru',
	'https://vec04.maps.yandex.net/tiles?l=map&v=4.40&x={0}&y={1}&z={2}&lang=ru'
]

tileUrls = tileUrlsYandex

def nextTileUrl():
	nextTileUrl.lastIndex = 0
	ret = tileUrls[nextTileUrl.lastIndex]
	nextTileUrl.lastIndex += 1
	if nextTileUrl.lastIndex == len(tileUrls):
		nextTileUrl.lastIndex = 0
	return ret

class TileParam:
	def __init__(self, x, y, zoom):
		self.zoom = zoom
		self.x = x
		self.y = y

class LoaderThread(Thread):
	
	def __init__(self, x, y, zoom):
		Thread.__init__(self)
		self.zoom = zoom
		self.x = x
		self.y = y
		self.url = nextTileUrl()
    
	def run(self):
		directory = f'tiles/{self.zoom}/{self.x}/'
		if not os.path.exists(directory):
			os.makedirs(directory)
		
		fpath = f'tiles/{self.zoom}/{self.x}/{self.y}.png'
		
		r = urllib.request.Request(self.url.format(self.x, self.y, self.zoom))
		r.add_header('Referer', 'https://mc.bbbike.org/')
		r.add_header('Accept-Language',' ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3')
		r.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0')
		r.add_header('Accept', '*/*')

		done = False
		while not done:
			print(f'Try to load tile [{self.x} ; {self.y}]')
			try:
				resp = urllib.request.urlopen(r)
				open(fpath, 'wb').write(resp.read())
				done = True
			except:
				print(f'Error while downloading tile [{self.x};{self.y};{self.zoom}]')
				self.url = nextTileUrl()
				r.full_url = self.url.format(self.x, self.y, self.zoom)
				time.sleep(1)

class LoaderThreadPool:
	def __init__(self, threadsCount):
		self.threadsCount = threadsCount
		self.poolParams = []
		self.working = []
		self.operations = threading.Thread(target = self.WorkMethod)

	def Start(self):
		self.operations.start()
	
	def Add(self, tileParam):
		self.poolParams.append(tileParam)

	def CheckAlive(self):
		for thread in self.working:
			if not thread.is_alive():
				self.working.remove(thread)
		while len(self.working) < self.threadsCount:
			self.RunNextThread()
	
	def RunNextThread(self):
		if len(self.poolParams) == 0:
			return
		tileParam = self.poolParams.pop(0)
		#if tileUrls != tileUrlsYandex:
		nextThread = LoaderThread(tileParam.x, tileParam.y, tileParam.zoom)
		#else:
		#	x = tileParam.x
		#	y = tileParam.y
		#	nextThread = LoaderThread(x, y, tileParam.zoom)
		nextThread.run()
		self.working.append(nextThread)
		print(f'New tile load task [{tileParam.x} ; {tileParam.y}] ({len(self.poolParams)} remaining)')
	
	def WorkMethod(self):
		while len(self.poolParams) > 0:
			self.CheckAlive()
			time.sleep(.1)
		print('Done')

threadPool = LoaderThreadPool(3)

def deg2num(lat_deg, lon_deg, zoom):
	lat_rad = math.radians(lat_deg)
	n = 2.0 ** zoom
	xtile = (lon_deg + 180.0) / 360.0 * n
	ytile = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
	xtile = int(xtile)
	ytile = int(ytile)
	return (xtile, ytile)

def yandexdeg2num(lat, lng, zoom):
    rlat, rlon = math.radians(lat), math.radians(lng)
    a = 6378137
    k = 0.0818191908426
    z = math.tan(math.pi / 4 + rlat / 2) / math.tan(math.pi / 4 + math.asin(k * math.sin(rlat)) / 2) ** k
    z1 = 2 ** (23 - zoom)
    x = int(((20037508.342789 + a * rlon) * 53.5865938 / z1) / 256)
    y = int(((20037508.342789 - a * math.log(z)) * 53.5865938 / z1) / 256)
    return (x, y)

for paramData in loadParams:
	print(f'Loading {paramData["name"]}')
	lat_lt = paramData["lt"][0]
	lng_lt = paramData["lt"][1]
	lat_rb = paramData["rb"][0]
	lng_rb = paramData["rb"][1]
	for zoom in range(paramData["zooms"][0], paramData["zooms"][1] + 1):
		if tileUrls == tileUrlsYandex:
			ltxy = yandexdeg2num(lat_lt, lng_lt, zoom)
			rbxy = yandexdeg2num(lat_rb, lng_rb, zoom)
		else:
			ltxy = deg2num(lat_lt, lng_lt, zoom)
			rbxy = deg2num(lat_rb, lng_rb, zoom)

		print(f'   with zoom {zoom} (from {ltxy} to {rbxy})')
		for x in range( ltxy[0], rbxy[0]+1 ):
			for y in range( ltxy[1], rbxy[1]+1 ):
				fpath = f'tiles/{zoom}/{x}/{y}.png'
				if not os.path.exists(fpath):
					threadPool.Add( TileParam(x, y, zoom) )

threadPool.Start()