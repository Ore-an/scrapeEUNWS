import sys
import urllib2
import bs4 as BeautifulSoup
import multiprocessing
import subprocess
import io
import os.path
import argparse
threads = 8
# TODO: check livingit.euronews?, follow links around? (archive: www.euronews.com/2017).

parser = argparse.ArgumentParser(description='Scrape one of the euronews homepages.')
parser.add_argument('lang', nargs='+', help="Language code or list of language codes.")

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
    try:
        open_npage = urllib2.urlopen(newspage[0])
        parsed_page = BeautifulSoup.BeautifulSoup(open_npage, 'html.parser')
        video = parsed_page.find('meta', property='og:video').attrs['content']
        text = GetTags(parsed_page)
        text.extend([x.text for x in parsed_page.findAll('div', class_='js-article-content')])
    except:
        e = sys.exc_info()[0]
        print "{} on {}".format(e,newspage[0])
        text = None
        video = None
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
    soup = BeautifulSoup.BeautifulSoup(open_hpage, 'html.parser')
    for story in soup.findAll('div', attrs={'class':'media__img '}):
        if story.figure and story.figure['data-video-duration'].strip():
            links.append((story.figure['data-video-duration'].strip(), story.a['href']))
    npages = ['http:' + link[1] if link[1][0:2] == '//' else home + link[1] for link in links if link[1][0:6] != '/video'] #video links have no text
    return [(x, domain_len) for x in npages]

def FindArchivedNews(archive):
    pass
    # go to link of every date
    # check every link for that date

if __name__ == "__main__":
    args = parser.parse_args()
    lang = args.lang
    newspages = []
    if len(lang) > 1:
        for l in lang:
            if not os.path.exists(l):
                    os.makedirs(l)
            if langdic.get(l):
                home = "http://" + langdic.get(l) + top_domain
                newspages.extend(FindNews(home))
    else:
        lang = lang[0]
        if not os.path.exists(lang):
            os.makedirs(lang)
        if langdic.get(lang):
            home = "http://" + langdic.get(lang) + top_domain
            newspages = FindNews(home)
    if newspages:
        pool = multiprocessing.Pool(threads)
        pool.map(ScrapeNews, newspages)
        pool.close()
        pool.join()
    else:
        raise BaseException('Something went wrong, ensure that {} is in the languages list.'.format(lang))