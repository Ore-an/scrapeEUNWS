import sys
import urllib2
import bs4 as BeautifulSoup
import multiprocessing
import subprocess
import io
import os.path
import argparse
from datetime import datetime, timedelta
from functools import partial

threads = 30
# TODO: check livingit.euronews?, follow links around?

parser = argparse.ArgumentParser(description='Scrape audio and article from euronews stories.')
parser.add_argument('lang', nargs='+', help="Language code or list of language codes.")
parser.add_argument('-a', '--archive', action='store_true', help="Scrape from archive. Requires start and end dates.")
parser.add_argument('-sd', '--start-date', help="Starting date (if end date is given)"
                                                " or single day for archive scraping (dd/mm/yy).")
parser.add_argument('-ed', '--end-date', help="End date for archive scraping (dd/mm/yy).")

top_domain = ".euronews.com"
useful_name_tags = {"program.url", "keywords", "news_keywords"}
useful_property_tags = {"og:title", "og:type", "article:published_time", "article:modified_time", "article:section"}
langdic = {'en':'www',
           'fr':'fr',
           'de':'de',
           'it':'it',
           'es':'es',
           'pt':'pt',
           'ru':'ru',
           'tr':'tr',
           'gr':'gr',
           'hu':'hu',
           'ar':'arabic',
           'fa':'fa'
           }



def ScrapeNews(newspage):
    lang = next(lang for lang, subdomain in langdic.items() if subdomain == newspage[0].split('.')[0][7:]) # reverse lookup of the subdomain
    domain_len = newspage[1]
    filename = newspage[0][domain_len:].replace('/','-')
    tfile = lang + '/' + filename + '.txt'
    afile = lang + '/' + filename + '.wav'
    sfile = lang + '/' + filename + '.htm'
    try:
        open_npage = urllib2.urlopen(newspage[0])
        parsed_page = BeautifulSoup.BeautifulSoup(open_npage, 'html.parser')
        video = parsed_page.find('meta', property='og:video').attrs['content']
        text = ["---Tags---\n"]
        text.extend(GetTags(parsed_page))
        text.extend(["\n---Text---\n"])
        text.extend([xpar.text for x in parsed_page.findAll('div', class_='js-article-content') for xpar in x.findAll('p', recursive=False) if not xpar.blockquote])
        html = [x.prettify() for x in parsed_page.findAll('div', class_='js-article-content')]
    except:
        e = sys.exc_info()[0]
        print "{} on {}".format(e,newspage[0])
        text = None
        video = None
        html = None
    if html and video and not os.path.isfile(tfile):
        with io.open(tfile, 'w', encoding='utf8') as f:
            if type(text) == type([]):
                f.write('\n'.join(text))
            else:
                f.write(text)
        if not os.path.isfile(sfile):
            with io.open(sfile, 'w', encoding='utf8') as f:
                if type(html) == type([]):
                    f.write('\n'.join(html))
                else:
                    f.write(html)
        if not os.path.isfile(afile):
            GetAudio(video, afile)
        # print "{} done.".format(filename)
        return 0
    else:
        return 1

def GetAudio(video, filename, yt=False):
    command = "ffmpeg -hide_banner -loglevel quiet -i {} -ar 16000 -vn {}".format(video,filename)
    subprocess.call(command, shell=True)

def GetTags(parsed_page):
    tags = []
    for tag in parsed_page.findAll('meta'):
        if tag.attrs.get('property') in useful_property_tags:
            tags.append(u"{} : {}".format(tag.attrs['property'], tag.attrs['content']))
        elif tag.attrs.get('name') in useful_name_tags:
            tags.append(u"{} : {}".format(tag.attrs['name'], tag.attrs['content']))
    return tags

def FindNews(homepage):
    links = []
    domain_len = len(home) + 1
    open_hpage = urllib2.urlopen(homepage)
    parsed_hpage = BeautifulSoup.BeautifulSoup(open_hpage, 'html.parser')
    for story in parsed_hpage.findAll('div', attrs={'class':'media__img '}):
        if story.figure and story.figure['data-video-duration'].strip():
            links.append(story.a['href'])
    npages = ['http:' + link if link[0:2] == '//' else home + link for link in links if link[0:6] != '/video'] #video links have no text
    return [(x, domain_len) for x in npages]

def FindArchivedNews(homepage, start_date, end_date):
    links = []
    domain_len = len(home) + 1
    start = datetime.strptime(start_date, "%d/%m/%y")
    end = datetime.strptime(end_date, "%d/%m/%y")
    dates = [start + timedelta(days=d) for d in xrange((end - start).days + 1)]
    pool = multiprocessing.Pool(threads)
    links.extend(pool.map(partial(FindArchivedNewsHelper, homepage), dates))
    pool.close()
    npages = ['http:' + link if link[0:2] == '//' else home + link for daylinks in links for link in daylinks if link[0:6] != '/video']
    return [(x, domain_len) for x in npages]

def FindArchivedNewsHelper(homepage, date):
    datelinks = []
    archpage = homepage + "/{y}/{m:02d}/{d:02d}".format(y=date.year, m=date.month, d=date.day)
    open_archpage = urllib2.urlopen(archpage)
    parsed_archpage = BeautifulSoup.BeautifulSoup(open_archpage, 'html.parser')
    for story in parsed_archpage.findAll('article', attrs={'class':'u--has-video'}):
        if story.figure and story.figure['data-video-duration'].strip():
            datelinks.append(story.a['href'])
    return datelinks

if __name__ == "__main__":
    args = parser.parse_args()
    if args.archive:
        if args.start_date is None:
            parser.error("The --archive option requires at least a start date.")
        elif args.end_date is None:
            args.end_date = args.start_date
    lang = args.lang
    newspages = []
    if len(lang) > 1:
        for l in lang:
            if langdic.get(l):
                if not os.path.exists(l):
                    os.makedirs(l)
                home = "http://" + langdic.get(l) + top_domain
                if args.archive:
                    newspages.extend(FindArchivedNews(home, args.start_date, args.end_date))
                else:
                    newspages.extend(FindNews(home))
    else:
        lang = lang[0]
        if langdic.get(lang):
            if not os.path.exists(lang):
                os.makedirs(lang)
            home = "http://" + langdic.get(lang) + top_domain
            if args.archive:
                newspages = FindArchivedNews(home, args.start_date, args.end_date)
            else:
                newspages = FindNews(home)
    if newspages:
        pool = multiprocessing.Pool(threads)
        pool.map(ScrapeNews, newspages)
        pool.close()
        pool.join()
        sys.exit(0)
    else:
        raise BaseException('Something went wrong, ensure that {} is in the languages list and dates are correct.'.format(lang))
