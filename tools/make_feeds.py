#!/usr/bin/env python3
"""Testa as fontes candidatas por tema e escreve feeds.json so com as que respondem.

Uso: python tools/make_feeds.py   (demora alguns minutos por causa do Reddit)
Para acrescentar uma fonte: acrescentar a linha em CANDIDATOS e voltar a correr.
"""
import io
import json
import os
import sys
import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import build_feed  # noqa: E402

GN = 'https://news.google.com/rss/search?q=%s&hl=%s&gl=%s&ceid=%s'


def gn(q, lang='pt-PT'):
    if lang == 'pt-PT':
        return GN % (urllib.parse.quote(q), 'pt-PT', 'PT', 'PT:pt-150')
    return GN % (urllib.parse.quote(q), 'en', 'GB', 'GB:en')


def site(domain, lang='pt-PT'):
    return gn('site:' + domain, lang)


def reddit(name):
    return ('r/' + name, 'https://www.reddit.com/r/%s/.rss' % name, 'reddit')


def mtag(tag):
    return ('Mastodon #' + tag, 'https://mastodon.social/tags/%s.rss' % tag)


def bsky(handle, name=None):
    return (name or ('Bluesky @' + handle), 'https://bsky.app/profile/%s/rss' % handle)


# id, titulo, cor, fontes: (nome, url[, tipo])
CANDIDATOS = [
    ('guerra', 'guerra', '#FFE51400', [
        ('Bellingcat', 'https://www.bellingcat.com/feed/'),
        ('War on the Rocks', 'https://warontherocks.com/feed/'),
        ('The War Zone', 'https://www.twz.com/feed'),
        ('Meduza', 'https://meduza.io/rss/en/all'),
        ('The Moscow Times', 'https://www.themoscowtimes.com/rss/news'),
        ('Ukrainska Pravda', 'https://www.pravda.com.ua/eng/rss/view_news/'),
        ('Euromaidan Press', 'https://euromaidanpress.com/feed/'),
        ('Oryx', 'https://www.oryxspioenkop.com/feeds/posts/default'),
        ('ISW', 'https://understandingwar.org/feed'),
        ('Defense One', 'https://www.defenseone.com/rss/all/'),
        ('Kyiv Independent', site('kyivindependent.com', 'en')),
        ('BBC · Ucrânia', 'https://feeds.bbci.co.uk/news/world/europe/rss.xml'),
        ('Guardian · Ucrânia', 'https://www.theguardian.com/world/ukraine/rss'),
        ('Google News · guerra da Ucrânia', gn('guerra Ucrânia')),
        ('Google News · Ukraine war', gn('Ukraine war frontline', 'en')),
        ('Google News · Médio Oriente', gn('Médio Oriente guerra')),
        mtag('ukraine'), mtag('russia'),
        bsky('kyivindependent.com', 'Kyiv Independent (Bluesky)'),
        bsky('bellingcat.com', 'Bellingcat (Bluesky)'),
    ]),
    ('politica', 'política', '#FF1BA1E2', [
        ('Politico', 'https://rss.politico.com/politics-news.xml'),
        ('Politico Europe', 'https://www.politico.eu/feed/'),
        ('NPR · Política', 'https://feeds.npr.org/1014/rss.xml'),
        ('NPR · Mundo', 'https://feeds.npr.org/1004/rss.xml'),
        ('Guardian · EUA', 'https://www.theguardian.com/us-news/rss'),
        ('Guardian · Reino Unido', 'https://www.theguardian.com/politics/rss'),
        ('BBC · Política', 'https://feeds.bbci.co.uk/news/politics/rss.xml'),
        ('BBC · Mundo', 'https://feeds.bbci.co.uk/news/world/rss.xml'),
        ('NYT · Política', 'https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml'),
        ('NYT · Mundo', 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml'),
        ('Washington Post', 'https://feeds.washingtonpost.com/rss/world'),
        ('Euronews', 'https://www.euronews.com/rss?level=theme&name=news'),
        ('DW', 'https://rss.dw.com/rdf/rss-en-all'),
        ('France 24', 'https://www.france24.com/en/rss'),
        ('Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'),
        ('Google News · política EUA', gn('US politics White House Congress', 'en')),
        ('Google News · União Europeia', gn('European Union Brussels', 'en')),
        ('Google News · Reino Unido', gn('UK politics Westminster', 'en')),
        mtag('politics'), mtag('geopolitics'),
        bsky('politico.com', 'Politico (Bluesky)'),
        bsky('apnews.com', 'AP (Bluesky)'),
        bsky('reuters.com', 'Reuters (Bluesky)'),
        bsky('theguardian.com', 'Guardian (Bluesky)'),
    ]),
    ('portugal', 'jornais', '#FF60A917', [
        ('Público', 'https://feeds.feedburner.com/PublicoRSS'),
        ('Observador', 'https://observador.pt/feed/'),
        ('RTP Notícias', 'https://www.rtp.pt/noticias/rss/'),
        ('Expresso', 'https://expresso.pt/rss'),
        ('Diário de Notícias', 'https://www.dn.pt/rss'),
        ('CNN Portugal', 'https://cnnportugal.iol.pt/rss'),
        ('Jornal Económico', 'https://jornaleconomico.pt/feed/'),
        ('SIC Notícias', site('sicnoticias.pt')),
        ('Jornal de Notícias', site('jn.pt')),
        ('Notícias ao Minuto', site('noticiasaominuto.com')),
        ('Google News · Portugal', 'https://news.google.com/rss?hl=pt-PT&gl=PT&ceid=PT:pt-150'),
    ]),
    ('futebol', 'futebol', '#FF0050EF', [
        ('Record', 'https://www.record.pt/rss'),
        ('Maisfutebol', 'https://maisfutebol.iol.pt/rss'),
        ('A Bola', site('abola.pt')),
        ('O Jogo', site('ojogo.pt')),
        ('zerozero', site('zerozero.pt')),
        ('Google News · FC Porto', gn('"FC Porto"')),
        ('Google News · Liga Portugal', gn('Liga Portugal futebol')),
        ('BBC Sport · Futebol', 'https://feeds.bbci.co.uk/sport/football/rss.xml'),
        ('Guardian · Futebol', 'https://www.theguardian.com/football/rss'),
        ('ESPN · Futebol', 'https://www.espn.com/espn/rss/soccer/news'),
        ('Sky Sports · Futebol', 'https://www.skysports.com/rss/12040'),
        mtag('football'),
    ]),
    ('formacao', 'formação', '#FF00ABA9', [
        ('Google News · futebol de formação', gn('"futebol de formação"')),
        ('Google News · escalões jovens', gn('futebol jovem juniores iniciados academia')),
        ('Google News · academias', gn('academia de futebol formação jovens talentos')),
        ('Google News · youth football', gn('youth football academy development', 'en')),
        ('Google News · FPF jovens', gn('FPF seleções jovens sub-21 sub-19 sub-17')),
        ('Google News · Dragon Force / Porto formação', gn('FC Porto Dragão formação sub-23 juniores')),
        ('Mastodon #youthfootball', 'https://mastodon.social/tags/youthfootball.rss'),
    ]),
    ('ciclismo', 'ciclismo', '#FFF0A30A', [
        ('Cyclingnews', 'https://www.cyclingnews.com/rss/'),
        ('Cycling Weekly', 'https://www.cyclingweekly.com/feeds.xml'),
        ('Velo', 'https://velo.outsideonline.com/feed/'),
        ('road.cc', 'https://road.cc/rss'),
        ('BikeRadar', 'https://www.bikeradar.com/feed/'),
        ('Rouleur', 'https://www.rouleur.cc/blogs/the-rouleur-journal.atom'),
        ('Google News · ciclismo', gn('ciclismo OR "Volta a Portugal"')),
        ('Google News · cycling', gn('professional cycling peloton Tour', 'en')),
        mtag('cycling'), mtag('ciclismo'),
    ]),
    ('tecnologia', 'tecnologia', '#FF8C00FF', [
        ('Ars Technica', 'https://feeds.arstechnica.com/arstechnica/index'),
        ('The Verge', 'https://www.theverge.com/rss/index.xml'),
        ('Hacker News', 'https://hnrss.org/frontpage'),
        ('Engadget', 'https://www.engadget.com/rss.xml'),
        ('TechCrunch', 'https://techcrunch.com/feed/'),
        ('Wired', 'https://www.wired.com/feed/rss'),
        ('Tom\'s Hardware', 'https://www.tomshardware.com/feeds/all'),
        ('The Register', 'https://www.theregister.com/headlines.atom'),
        ('Slashdot', 'http://rss.slashdot.org/Slashdot/slashdotMain'),
        ('Pplware', 'https://pplware.sapo.pt/feed/'),
        ('SAPO Tek', 'https://tek.sapo.pt/rss'),
        ('Windows Central', 'https://www.windowscentral.com/rss'),
        mtag('technology'),
    ]),
    ('legacy', 'legacy', '#FFD80073', [
        ('MSPoweruser', 'https://mspoweruser.com/feed/'),
        ('Nokiamob', 'https://nokiamob.net/feed/'),
        ('Nokia Power User', 'https://nokiapoweruser.com/feed/'),
        ('CrackBerry', 'https://crackberry.com/feed'),
        ('BlackBerry Empire', 'https://www.blackberryempire.com/feed/'),
        ('GSMArena', 'https://www.gsmarena.com/rss-news-reviews.php3'),
        ('Hackaday', 'https://hackaday.com/blog/feed/'),
        ('Google News · Windows Phone', gn('"Windows Phone" OR "Windows 10 Mobile" OR Lumia', 'en')),
        ('Google News · Symbian', gn('Symbian Nokia S60', 'en')),
        ('Google News · BlackBerry OS', gn('BlackBerry OS BB10 BlackBerry 10', 'en')),
        ('Google News · iOS legacy', gn('"iOS 6" OR "iOS 7" OR "legacy iOS" OR "old iPhone" jailbreak', 'en')),
        ('Google News · telemóveis antigos', gn('telemóveis antigos retro Nokia clássicos')),
        mtag('windowsphone'), mtag('symbian'), mtag('blackberry'), mtag('retrophones'), mtag('legacyios'),
    ]),
    ('reddit', 'reddit', '#FFFF4500', [
        reddit('windowsphone'), reddit('Windows10Mobile'), reddit('symbian'), reddit('nokia'),
        reddit('blackberry'), reddit('BlackBerry10'), reddit('LegacyJailbreak'), reddit('legacyiOS'),
        reddit('ubuntuphone'), reddit('UbuntuTouch'), reddit('dumbphones'), reddit('retrophones'),
        reddit('webOS'), reddit('UkrainianConflict'), reddit('CredibleDefense'),
        reddit('portugal'), reddit('cycling'), reddit('soccer'), reddit('hacking'),
    ]),
    ('musica', 'música', '#FFD80073', [
        ('Pitchfork', 'https://pitchfork.com/feed/feed-news/rss'),
        ('Stereogum', 'https://www.stereogum.com/feed/'),
        ('NME', 'https://www.nme.com/feed'),
        ('Rolling Stone · Música', 'https://www.rollingstone.com/music/feed/'),
    ]),
    ('hacking', 'hacking', '#FF00AB00', [
        ('BleepingComputer', 'https://www.bleepingcomputer.com/feed/'),
        ('The Hacker News', 'https://feeds.feedburner.com/TheHackersNews'),
        ('Krebs on Security', 'https://krebsonsecurity.com/feed/'),
        ('Schneier', 'https://www.schneier.com/feed/atom/'),
    ]),
    ('famosos', 'famosos', '#FFE51400', [
        ('TMZ', 'https://www.tmz.com/rss.xml'),
        ('People', site('people.com', 'en')),
        ('The Hollywood Reporter', 'https://www.hollywoodreporter.com/feed/'),
        ('Google News · celebridades PT', gn('celebridades portuguesas')),
    ]),
]


def norm(s):
    if len(s) == 2:
        return {'name': s[0], 'url': s[1]}
    return {'name': s[0], 'url': s[1], 'kind': s[2]}


def main():
    sources = {}
    groups = {}
    for sid, title, accent, srcs in CANDIDATOS:
        for s in srcs:
            d = norm(s)
            sources[d['url']] = d
            groups.setdefault(urllib.parse.urlparse(d['url']).netloc, []).append(d)

    failures, ok = [], {}
    lock = threading.Lock()

    def log(m):
        with lock:
            print(m, flush=True)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(build_feed.run_group, h, s, 12, failures, log) for h, s in groups.items()]
        for f in futs:
            for s, items in f.result():
                if items:
                    ok[s['url']] = len(items)

    sections = []
    for sid, title, accent, srcs in CANDIDATOS:
        good = [norm(s) for s in srcs if norm(s)['url'] in ok]
        if good:
            sections.append({'id': sid, 'title': title, 'accent': accent, 'sources': good})
    cfg = {'itemsPerSource': 10, 'itemsPerSection': 50, 'sections': sections}
    with io.open(os.path.join(ROOT, 'feeds.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('\nSECCOES:')
    for s in sections:
        print('  %-10s %2d fontes' % (s['id'], len(s['sources'])))
    print('FALHARAM (%d):' % len(failures))
    for x in failures:
        print('  - %s | %s' % (x['fonte'], x['erro'][:70]))


if __name__ == '__main__':
    main()
