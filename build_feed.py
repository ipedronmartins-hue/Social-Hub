#!/usr/bin/env python3
"""Recolhe os feeds de feeds.json e escreve out/hub.json + out/img/*.jpg.

Corre no GitHub (tarefa agendada) ou no PC. So usa fontes publicas, sem contas nem cookies.
Uma fonte que falha nunca estraga as outras: fica registada em "falhas".
"""
import hashlib
import html
import io
import json
import os
import re
import sys
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

import requests
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'out')
IMG = os.path.join(OUT, 'img')
UA = 'Mozilla/5.0 (compatible; PessoalHub/1.0; leitor pessoal de feeds publicos)'
TIMEOUT = 20
MAX_FEED_BYTES = 6 * 1024 * 1024
MAX_IMG_BYTES = 3 * 1024 * 1024
THUMB_W = 560
HOST_DELAY = {'www.reddit.com': 10.0}
DEFAULT_DELAY = 1.0

_img_lock = threading.Lock()
_wanted_imgs = set()


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.img = None

    def handle_starttag(self, tag, attrs):
        if tag == 'img' and not self.img:
            a = dict(attrs)
            src = a.get('src') or a.get('data-src')
            if src and src.startswith(('http://', 'https://')):
                self.img = src
        if tag in ('p', 'br', 'li', 'div'):
            self.parts.append(' ')

    def handle_data(self, data):
        self.parts.append(data)


def plain(markup):
    p = _Text()
    try:
        p.feed(markup or '')
    except Exception:
        return html.unescape(re.sub(r'<[^>]+>', ' ', markup or '')).strip(), None
    text = re.sub(r'\s+', ' ', ''.join(p.parts)).strip()
    return text, p.img


def local(tag):
    return tag.rsplit('}', 1)[-1] if '}' in tag else tag


def child_text(el, *names):
    for c in el:
        if local(c.tag) in names and (c.text or '').strip():
            return c.text.strip()
    return None


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        d = None
    if d is None:
        try:
            d = datetime.fromisoformat(s.replace('Z', '+00:00'))
        except Exception:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def entry_link(e):
    for c in e:
        if local(c.tag) == 'link':
            href = c.get('href')
            if href and c.get('rel') in (None, 'alternate'):
                return href
            if c.text and c.text.strip():
                return c.text.strip()
    return None


def entry_image(e, body_img):
    for c in e.iter():
        t = local(c.tag)
        if t in ('thumbnail', 'content') and c.get('url') and (t == 'thumbnail' or (c.get('medium') == 'image' or 'image' in (c.get('type') or ''))):
            return c.get('url')
        if t == 'enclosure' and 'image' in (c.get('type') or '') and c.get('url'):
            return c.get('url')
    return body_img


def parse_feed(data, source):
    root = ET.fromstring(data)
    items = []
    entries = [e for e in root.iter() if local(e.tag) in ('item', 'entry')]
    for e in entries:
        title = child_text(e, 'title')
        if not title:
            continue
        title = plain(title)[0]
        real_source = child_text(e, 'source')
        if real_source:
            suffix = ' - ' + real_source
            if title.endswith(suffix):
                title = title[:-len(suffix)]
        body = child_text(e, 'encoded', 'content', 'description', 'summary') or ''
        text, body_img = plain(body)
        if real_source:
            text = ''
        link = entry_link(e)
        if not link:
            continue
        when = parse_date(child_text(e, 'pubDate', 'published', 'updated', 'date'))
        items.append({
            'title': title[:220],
            'summary': text[:260],
            'source': real_source or source['name'],
            'url': link,
            'when': when,
            'image': entry_image(e, body_img),
        })
    return items


def fetch(url, limit):
    r = None
    for attempt in range(3):
        r = requests.get(url, headers={'User-Agent': UA, 'Accept': '*/*'}, timeout=TIMEOUT, stream=True)
        if r.status_code not in (429, 503) or attempt == 2:
            break
        wait = 20
        try:
            wait = min(60, max(5, int(r.headers.get('Retry-After', '20'))))
        except ValueError:
            pass
        r.close()
        time.sleep(wait)
    r.raise_for_status()
    buf = io.BytesIO()
    for chunk in r.iter_content(65536):
        buf.write(chunk)
        if buf.tell() > limit:
            raise ValueError('resposta demasiado grande')
    return buf.getvalue(), r.headers.get('content-type', '')


def make_thumb(url):
    """Descarrega e reduz a imagem; devolve o nome do ficheiro ou None."""
    name = hashlib.sha1(url.encode('utf-8')).hexdigest()[:16] + '.jpg'
    path = os.path.join(IMG, name)
    with _img_lock:
        _wanted_imgs.add(name)
    if os.path.exists(path):
        return name
    try:
        data, ctype = fetch(url, MAX_IMG_BYTES)
        im = Image.open(io.BytesIO(data))
        im.load()
        if im.width < 80 or im.height < 60:
            return None
        im = im.convert('RGB')
        im.thumbnail((THUMB_W, THUMB_W * 2))
        im.save(path, "JPEG", quality=72, optimize=True)
        return name
    except Exception:
        with _img_lock:
            _wanted_imgs.discard(name)
        return None


def run_group(host, sources, per_source, failures, log):
    delay = HOST_DELAY.get(host, DEFAULT_DELAY)
    out = []
    for i, s in enumerate(sources):
        if i:
            time.sleep(delay)
        try:
            data, _ = fetch(s['url'], MAX_FEED_BYTES)
            items = parse_feed(data, s)
            items.sort(key=lambda x: x['when'] or datetime(1970, 1, 1, tzinfo=timezone.utc), reverse=True)
            out.append((s, items[:per_source]))
            log('ok     %-34s %2d itens' % (s['name'], min(len(items), per_source)))
        except Exception as ex:
            failures.append({'fonte': s['name'], 'erro': '%s: %s' % (type(ex).__name__, str(ex)[:120])})
            log('FALHOU %-34s %s: %s' % (s['name'], type(ex).__name__, str(ex)[:100]))
    return out



# ---------- cartoes (tempo e jogos) ----------
HOME = {'name': 'Rio Tinto', 'lat': 41.18, 'lon': -8.56}
LEAGUES = [('por.1', 'Liga Portugal'), ('uefa.champions', 'Liga dos Campeões'), ('uefa.europa', 'Liga Europa')]
WMO = [((0,), 'limpo'), ((1,), 'pouco nublado'), ((2,), 'parcialmente nublado'), ((3,), 'nublado'),
       ((45, 48), 'nevoeiro'), ((51, 53, 55, 56, 57), 'chuvisco'), ((61, 63, 65, 66, 67), 'chuva'),
       ((71, 73, 75, 77, 85, 86), 'neve'), ((80, 81, 82), 'aguaceiros'), ((95, 96, 99), 'trovoada')]
DIAS = ['seg', 'ter', 'qua', 'qui', 'sex', 'sáb', 'dom']


def lisbon(dt):
    try:
        from zoneinfo import ZoneInfo
        return dt.astimezone(ZoneInfo('Europe/Lisbon'))
    except Exception:
        return dt


def weather_card():
    url = ('https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s&current=temperature_2m,weather_code,is_day'
           '&daily=precipitation_probability_max,temperature_2m_max,temperature_2m_min&timezone=Europe%%2FLisbon&forecast_days=3'
           % (HOME['lat'], HOME['lon']))
    data, _ = fetch(url, 200 * 1024)
    j = json.loads(data.decode('utf-8'))
    code = j['current']['weather_code']
    text = next((n for codes, n in WMO if code in codes), 'tempo variável')
    d = j['daily']
    days = []
    for i in range(len(d['time'])):
        dd = datetime.fromisoformat(d['time'][i])
        days.append({'d': 'hoje' if i == 0 else DIAS[dd.weekday()], 'hi': round(d['temperature_2m_max'][i]),
                     'lo': round(d['temperature_2m_min'][i]), 'rain': d['precipitation_probability_max'][i]})
    return {'type': 'weather', 'title': HOME['name'], 'temp': round(j['current']['temperature_2m']), 'text': text,
            'night': not j['current'].get('is_day', 1), 'rain': days[0]['rain'], 'hi': days[0]['hi'], 'lo': days[0]['lo'], 'days': days}


def score_cards():
    out = []
    now = datetime.now(timezone.utc)
    for code, label in LEAGUES:
        try:
            data, _ = fetch('https://site.api.espn.com/apis/site/v2/sports/soccer/%s/scoreboard' % code, 3 * 1024 * 1024)
            ev = json.loads(data.decode('utf-8')).get('events', [])
        except Exception:
            continue
        for e in ev:
            try:
                c = e['competitions'][0]
                a, b = c['competitors'][0], c['competitors'][1]
                if a.get('homeAway') == 'away':
                    a, b = b, a
                when = datetime.fromisoformat(e['date'].replace('Z', '+00:00'))
                hours = (when - now).total_seconds() / 3600.0
                state = e['status']['type']['state']
                if state == 'pre' and hours > 60:
                    continue
                if state == 'post' and hours < -40:
                    continue
                if state == 'pre':
                    lw = lisbon(when)
                    status = '%s %02d:%02d' % (DIAS[lw.weekday()], lw.hour, lw.minute)
                elif state == 'in':
                    status = e['status'].get('displayClock') or 'em jogo'
                else:
                    status = 'fim'
                porto = 'porto' in (a['team']['displayName'] + b['team']['displayName']).lower()
                out.append({'type': 'score', 'league': label, 'home': a['team'].get('shortDisplayName') or a['team']['displayName'],
                            'away': b['team'].get('shortDisplayName') or b['team']['displayName'],
                            'hs': a.get('score') if state != 'pre' else None, 'as': b.get('score') if state != 'pre' else None,
                            'status': status, 'live': state == 'in', 'ts': int(when.timestamp()), '_k': (0 if porto else 1, 0 if state == 'in' else 1, abs(hours))})
            except Exception:
                continue
    out.sort(key=lambda x: x['_k'])
    for x in out:
        x.pop('_k', None)
    return out[:6]


def build_cards(log):
    cards = []
    try:
        cards.append(weather_card())
        log('ok     cartao do tempo')
    except Exception as ex:
        log('FALHOU cartao do tempo %s: %s' % (type(ex).__name__, str(ex)[:80]))
    try:
        sc = score_cards()
        cards.extend(sc)
        log('ok     cartoes de jogos: %d' % len(sc))
    except Exception as ex:
        log('FALHOU cartoes de jogos %s: %s' % (type(ex).__name__, str(ex)[:80]))
    return cards


# ---------- "para ti": o melhor de cada tema, misturado ----------
PARATI = ['futebol', 'guerra', 'portugal', 'politica', 'tecnologia', 'ciclismo', 'formacao', 'legacy']


def build_parati(sections):
    by = {s['id']: s for s in sections}
    picked = []
    for sid in PARATI:
        s = by.get(sid)
        if not s:
            continue
        for it in sorted(s['items'], key=lambda x: x['ts'], reverse=True)[:4]:
            c = dict(it)
            c['sec'] = sid
            picked.append(c)
    picked.sort(key=lambda x: x['ts'], reverse=True)
    out, seen, last = [], set(), None
    for it in picked:
        key = it['title'][:40].lower()
        if key in seen:
            continue
        if it['sec'] == last and len(out) % 3 == 2:
            continue   # evita tres seguidos do mesmo tema
        seen.add(key)
        out.append(it)
        last = it['sec']
    # a primeira noticia com imagem passa a destaque
    for i, it in enumerate(out):
        if it.get('thumb'):
            out.insert(0, out.pop(i))
            break
    return {'id': 'parati', 'title': 'para ti', 'accent': '#FF1BA1E2', 'items': out[:50]}


def main():
    cfg = json.load(open(os.path.join(ROOT, 'feeds.json'), encoding='utf-8'))
    os.makedirs(IMG, exist_ok=True)
    per_source = cfg.get('itemsPerSource', 12)
    per_section = cfg.get('itemsPerSection', 40)
    failures = []
    lock = threading.Lock()

    def log(msg):
        with lock:
            print(msg, flush=True)

    groups = {}
    for sec in cfg['sections']:
        for s in sec['sources']:
            host = urllib.parse.urlparse(s['url']).netloc
            groups.setdefault(host, []).append(s)

    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(run_group, h, srcs, per_source, failures, log) for h, srcs in groups.items()]
        for f in futs:
            for s, items in f.result():
                results[s['url']] = items

    sections = []
    now = datetime.now(timezone.utc)
    img_jobs = []
    for sec in cfg['sections']:
        merged = []
        for s in sec['sources']:
            merged.extend(results.get(s['url'], []))
        merged.sort(key=lambda x: x['when'] or datetime(1970, 1, 1, tzinfo=timezone.utc), reverse=True)
        # no maximo 3 itens seguidos da mesma fonte ficam juntos: evita que uma fonte barulhenta tape as outras
        merged = merged[:per_section * 2]
        seen_urls, uniq = set(), []
        for it in merged:
            if it['url'] in seen_urls:
                continue
            seen_urls.add(it['url'])
            uniq.append(it)
        uniq = uniq[:per_section]
        for it in uniq:
            img_jobs.append(it)
        sections.append({'id': sec['id'], 'title': sec['title'], 'accent': sec.get('accent'), 'items': uniq})

    with ThreadPoolExecutor(max_workers=6) as pool:
        thumbs = list(pool.map(lambda it: make_thumb(it['image']) if it['image'] else None, img_jobs))
    for it, th in zip(img_jobs, thumbs):
        it['thumb'] = th

    # limpa miniaturas que ja nao estao em uso
    for f in os.listdir(IMG):
        if f not in _wanted_imgs:
            try:
                os.remove(os.path.join(IMG, f))
            except OSError:
                pass

    for sec in sections:
        for it in sec['items']:
            w = it.pop('when')
            it['ts'] = int(w.timestamp()) if w else 0
            it.pop('image', None)
            it['id'] = hashlib.sha1(it['url'].encode('utf-8')).hexdigest()[:12]
            it['sec'] = sec['id']

    cards = build_cards(log)
    sections.insert(0, build_parati(sections))
    doc = {
        'generated': int(now.timestamp()),
        'cards': cards,
        'sections': sections,
        'failures': failures,
    }
    with open(os.path.join(OUT, 'hub.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(doc, f, ensure_ascii=False, separators=(',', ':'))

    parati = next((s for s in sections if s['id'] == 'parati'), None)
    heads = [{'s': it['source'], 't': it['title']} for it in (parati['items'] if parati else [])[:6]]
    with open(os.path.join(OUT, 'tile.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'generated': doc['generated'], 'items': heads}, f, ensure_ascii=False, separators=(',', ':'))
    total = sum(len(s['items']) for s in sections if s['id'] != 'parati')
    log('feito: %d itens em %d seccoes, %d falhas, %d miniaturas' % (total, len(sections), len(failures), len(_wanted_imgs)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
