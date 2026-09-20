var SOURCES = {
  reddit: {
    label: "REDDIT",
    url: "https://www.reddit.com/r/portugal/hot.json?limit=12"
  },
  news: {
    label: "RTP NOTÍCIAS",
    url: "https://www.rtp.pt/noticias/rss"
  },
  sport: {
    label: "RTP DESPORTO",
    url: "https://www.rtp.pt/noticias/rss/desporto"
  }
};

function esc(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function stripHtml(value) {
  return String(value || "")
    .replace(/<!\[CDATA\[/g, "")
    .replace(/\]\]>/g, "")
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function decodeEntities(value) {
  return String(value || "")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&#(\d+);/g, function(_, n) {
      return String.fromCharCode(Number(n));
    });
}

function rssItems(xml, limit) {
  var matches = xml.match(/<item[\s\S]*?<\/item>/gi) || [];
  return matches.slice(0, limit || 8).map(function(item) {
    var title = item.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
    var link = item.match(/<link[^>]*>([\s\S]*?)<\/link>/i);
    var date = item.match(/<(pubDate|dc:date)[^>]*>([\s\S]*?)<\/(pubDate|dc:date)>/i);
    return {
      title: decodeEntities(stripHtml(title ? title[1] : "Sem título")),
      link: decodeEntities(stripHtml(link ? link[1] : "")),
      date: date ? stripHtml(date[2]) : ""
    };
  }).filter(function(x) { return x.title; });
}

async function fetchReddit() {
  var response = await fetch(SOURCES.reddit.url, {
    headers: {
      "User-Agent": "SocialHub/1.0 (Windows Phone 8.1 compatibility service)"
    }
  });

  if (!response.ok) throw new Error("Reddit HTTP " + response.status);

  var data = await response.json();
  return (data.data && data.data.children ? data.data.children : []).slice(0, 10).map(function(row) {
    var p = row.data || {};
    return {
      title: p.title || "Sem título",
      link: p.url || ("https://www.reddit.com" + (p.permalink || "")),
      meta: (p.author ? "u/" + p.author : "Reddit") + " · " + (p.score || 0) + " pontos"
    };
  });
}

async function fetchRss(source) {
  var response = await fetch(SOURCES[source].url, {
    headers: {
      "User-Agent": "SocialHub/1.0 RSS reader"
    }
  });

  if (!response.ok) throw new Error(source + " HTTP " + response.status);

  var xml = await response.text();
  return rssItems(xml, 10).map(function(item) {
    return {
      title: item.title,
      link: item.link,
      meta: item.date || SOURCES[source].label
    };
  });
}

function renderPage(label, items, errors) {
  var cards = items.map(function(item) {
    return "<article class='card'>" +
      "<div class='card-source'>" + esc(label) + "</div>" +
      "<h2><a href='" + esc(item.link) + "'>" + esc(item.title) + "</a></h2>" +
      "<p>" + esc(item.meta || "Agora") + "</p>" +
      "</article>";
  }).join("");

  if (!cards) {
    cards = "<article class='card'><div class='card-source'>SOCIAL HUB</div>" +
      "<h2>Não foi possível obter conteúdos.</h2>" +
      "<p>Tenta novamente dentro de alguns segundos.</p></article>";
  }

  var errorBlock = errors.length
    ? "<article class='card'><div class='card-source'>AVISO</div><p>" + esc(errors.join(" · ")) + "</p></article>"
    : "";

  return "<!doctype html><html lang='pt-PT'><head>" +
    "<meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>" +
    "<title>Social Hub - " + esc(label) + "</title>" +
    "<link rel='stylesheet' href='/styles.css'></head><body><div class='page'>" +
    "<header class='header'><div class='brand'>SOCIAL HUB</div>" +
    "<div class='subtitle'>FEED · " + esc(label) + "</div></header>" +
    "<main><section class='hero'><div class='eyebrow'>ONLINE</div>" +
    "<h1>Conteúdo real.</h1><p>O servidor recolheu os feeds e converteu-os para HTML compatível com o Lumia.</p></section>" +
    "<section class='feed'><div class='section-title'>ÚLTIMAS</div>" +
    cards + errorBlock + "</section></main>" +
    "<footer><a href='/' style='color:#fff'>← VOLTAR</a> · SOCIAL HUB 2026</footer>" +
    "</div></body></html>";
}

module.exports = async function(req, res) {
  var source = (req.query && req.query.source) || "all";
  var items = [];
  var errors = [];

  try {
    if (source === "reddit") {
      items = await fetchReddit();
    } else if (source === "news") {
      items = await fetchRss("news");
    } else if (source === "sport") {
      items = await fetchRss("sport");
    } else if (source === "youtube") {
      items = [{
        title: "YouTube fica preparado para receber canais reais",
        link: "https://www.youtube.com/",
        meta: "Fonte configurável na próxima fase"
      }];
    } else {
      var results = await Promise.allSettled([
        fetchReddit(),
        fetchRss("news"),
        fetchRss("sport")
      ]);

      if (results[0].status === "fulfilled") {
        items = items.concat(results[0].value.map(function(x) {
          x.meta = "REDDIT · " + x.meta;
          return x;
        }));
      } else {
        errors.push("Reddit indisponível");
      }

      if (results[1].status === "fulfilled") {
        items = items.concat(results[1].value.map(function(x) {
          x.meta = "RTP · " + x.meta;
          return x;
        }));
      } else {
        errors.push("RTP indisponível");
      }

      if (results[2].status === "fulfilled") {
        items = items.concat(results[2].value.map(function(x) {
          x.meta = "DESPORTO · " + x.meta;
          return x;
        }));
      } else {
        errors.push("Desporto indisponível");
      }

      items = items.slice(0, 20);
    }
  } catch (error) {
    errors.push("Fonte temporariamente indisponível");
  }

  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "s-maxage=120, stale-while-revalidate=300");
  res.status(200).send(renderPage(
    source === "all" ? "TIMELINE" : (SOURCES[source] ? SOURCES[source].label : "SOCIAL HUB"),
    items,
    errors
  ));
};
