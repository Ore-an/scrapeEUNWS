import urllib2
import bs4 as BeautifulSoup
import multiprocessing
import subprocess
import io
import os.path
import argparse
threads = 8

parser = argparse.ArgumentParser(description='Scrape one of the euronews homepages.')
parser.add_argument('home', help="Address of the page")


def ScrapeNews(newspage):
    openpage = urllib2.urlopen(newspage)
    parsed_page = BeautifulSoup.BeautifulSoup(openpage, 'html.parser')
    video = parsed_page.find('meta', property='og:video').attrs['content']
    text = [x.text for x in parsed_page.findAll('div', class_='js-article-content')]
    filename = newspage[domainlen:].replace('/','-')
    tfile = filename + '.txt'
    afile = filename + '.wav'
    if text and video and not os.path.isfile(tfile):
        with io.open(tfile, 'w', encoding='utf8') as f:
            if type(text) == type([]):
                f.write('\n'.join(text))
            else:
                f.write(text)
        GetAudio(video, afile)
        print "{} done.".format(filename)
        return 0
    else:
        return 1

def GetAudio(video, filename):
    command = "ffmpeg -hide_banner -loglevel quiet -i {} -ar 16000 -vn {}".format(video,filename)
    subprocess.call(command, shell=True)


args = parser.parse_args()
home = args.home
domainlen = len(home) + 1
page = urllib2.urlopen(home)
soup = BeautifulSoup.BeautifulSoup(page, 'html.parser')

pool = multiprocessing.Pool(threads)

links = []

for story in soup.findAll('div', attrs={'class':'media__img '}):
    if story.figure and story.figure['data-video-duration'].strip():
        links.append((story.figure['data-video-duration'].strip(), story.a['href']))

newspages = [home + link[1] for link in links]

pool.map(ScrapeNews, newspages)
