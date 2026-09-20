var SOURCES = {
  cyber: [
    { label: "THE HACKER NEWS", url: "https://thehackernews.com/feeds/posts/default" },
    { label: "BLEEPINGCOMPUTER", url: "https://www.bleepingcomputer.com/feed/" },
    { label: "KREBS ON SECURITY", url: "https://krebsonsecurity.com/feed/" }
  ],
  legacy: [
    { label: "BLEEPINGCOMPUTER", url: "https://www.bleepingcomputer.com/feed/" },
    { label: "HACKER NEWS", url: "https://news.ycombinator.com/rss" }
  ],
  world: [
    { label: "GUARDIAN · RUSSIA", url: "https://www.theguardian.com/world/russia/rss" }
  ],
  football: [
    { label: "GUARDIAN · FOOTBALL", url: "https://www.theguardian.com/football/rss" },
    { label: "RTP · DESPORTO", url: "https://www.rtp.pt/noticias/rss/desporto" }
  ],
  cycling: [
    { label: "CYCLINGNEWS", url: "https://feeds2.feedburner.com/cyclingnews/news" }
  ],
  cardputer: [
    { label: "HACKER NEWS · CARDPUTER", url: "https://hnrss.org/newest?q=cardputer" },
    { label: "HACKER NEWS · M5STACK", url: "https://hnrss.org/newest?q=m5stack" }
  ],
  news: [
    { label: "RTP NOTÍCIAS", url: "https://www.rtp.pt/noticias/rss" }
  ]
};

function esc(v) {
  return String(v || "").replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}

function strip(v) {
  return String(v || "").replace(/<!\[CDATA\[/g,"").replace(/\]\]>/g,"")
    .replace(/<[^>]*>/g," ").replace(/&nbsp;/gi," ").replace(/\s+/g," ").trim();
}

function decode(v) {
  return strip(v).replace(/&amp;/g,"&").replace(/&quot;/g,'"')
    .replace(/&#39;/g,"'").replace(/&apos;/g,"'").replace(/&lt;/g,"<")
    .replace(/&gt;/g,">").replace(/&#(\d+);/g,function(_,n){
      return String.fromCharCode(Number(n));
    });
}

function rssItems(xml, source, limit) {
  var matches = xml.match(/<item[\s\S]*?<\/item>/gi) || [];
  return matches.slice(0,limit || 8).map(function(item) {
    var t=item.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
    var l=item.match(/<link[^>]*>([\s\S]*?)<\/link>/i);
    var d=item.match(/<(pubDate|dc:date|published|updated)[^>]*>([\s\S]*?)<\/(pubDate|dc:date|published|updated)>/i);
    return {
      title: decode(t ? t[1] : "Sem título"),
      link: decode(l ? l[1] : ""),
      meta: source + (d ? " · " + strip(d[2]) : "")
    };
  }).filter(function(x){ return x.title && x.link; });
}

async function fetchSource(source) {
  var r=await fetch(source.url,{headers:{"User-Agent":"SocialHub/1.0 RSS reader"}});
  if(!r.ok) throw new Error(source.label+" HTTP "+r.status);
  return rssItems(await r.text(),source.label,8);
}

async function getSources(list) {
  var results=await Promise.allSettled(list.map(fetchSource));
  var items=[], errors=[];
  results.forEach(function(r,i){
    if(r.status==="fulfilled") items=items.concat(r.value);
    else errors.push(list[i].label+" indisponível");
  });
  return {items:items.slice(0,24),errors:errors};
}

async function fetchReddit() {
  var r=await fetch("https://www.reddit.com/r/portugal/hot.json?limit=12",{
    headers:{"User-Agent":"SocialHub/1.0 Windows Phone feed"}
  });
  if(!r.ok) throw new Error("Reddit HTTP "+r.status);
  var d=await r.json();
  return (d.data && d.data.children ? d.data.children : []).slice(0,12).map(function(row){
    var p=row.data || {};
    return {
      title:p.title || "Sem título",
      link:p.url || ("https://www.reddit.com"+(p.permalink||"")),
      meta:"REDDIT · "+(p.author ? "u/"+p.author : "post")+" · "+(p.score||0)+" pontos"
    };
  });
}

function render(label,items,errors) {
  var cards=items.map(function(x){
    return "<article class='card'><div class='card-source'>"+esc(x.meta.split(" · ")[0])+"</div>"+
      "<h2><a href='"+esc(x.link)+"'>"+esc(x.title)+"</a></h2>"+
      "<p>"+esc(x.meta)+"</p></article>";
  }).join("");

  if(!cards) cards="<article class='card'><div class='card-source'>SOCIAL HUB</div>"+
    "<h2>Sem conteúdos neste momento.</h2><p>A fonte pode estar temporariamente indisponível.</p></article>";

  if(errors.length) cards += "<article class='card'><div class='card-source'>AVISO</div><p>"+
    esc(errors.join(" · "))+"</p></article>";

  return "<!doctype html><html lang='pt-PT'><head><meta charset='utf-8'>"+
    "<meta name='viewport' content='width=device-width, initial-scale=1'>"+
    "<title>Social Hub - "+esc(label)+"</title><link rel='stylesheet' href='/styles.css'></head>"+
    "<body><div class='page'><header class='header'><div class='brand'>SOCIAL HUB</div>"+
    "<div class='subtitle'>FEED · "+esc(label)+"</div></header><main>"+
    "<section class='hero'><div class='eyebrow'>ONLINE</div><h1>"+esc(label)+"</h1>"+
    "<p>Conteúdo recolhido na cloud e convertido para HTML compatível com o Lumia.</p></section>"+
    "<section class='feed'><div class='section-title'>ÚLTIMAS</div>"+cards+"</section></main>"+
    "<footer><a href='/' style='color:#fff'>← VOLTAR</a> · SOCIAL HUB 2026</footer>"+
    "</div></body></html>";
}

module.exports=async function(req,res) {
  var source=(req.query&&req.query.source)||"all";
  var items=[],errors=[],label="TIMELINE";

  if(source==="reddit") {
    try { items=await fetchReddit(); label="REDDIT"; }
    catch(e) { errors.push("Reddit indisponível"); }
  } else if(source==="all") {
    var groups=["cyber","world","football","cycling","cardputer"];
    var allResults=await Promise.allSettled(groups.map(function(g){return getSources(SOURCES[g]);}));
    allResults.forEach(function(r){
      if(r.status==="fulfilled") { items=items.concat(r.value.items); errors=errors.concat(r.value.errors); }
    });
    items=items.slice(0,30);
  } else if(SOURCES[source]) {
    var result=await getSources(SOURCES[source]);
    items=result.items; errors=result.errors;
    label=source.toUpperCase();
  } else {
    errors.push("Fonte desconhecida");
  }

  res.setHeader("Content-Type","text/html; charset=utf-8");
  res.setHeader("Cache-Control","s-maxage=120, stale-while-revalidate=300");
  res.status(200).send(render(label,items,errors));
};