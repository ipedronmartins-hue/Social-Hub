function esc(v) {
  return String(v || "").replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}

function decode(v) {
  return String(v || "")
    .replace(/&nbsp;/gi," ")
    .replace(/&amp;/g,"&")
    .replace(/&quot;/g,'"')
    .replace(/&#39;/g,"'")
    .replace(/&apos;/g,"'")
    .replace(/&lt;/g,"<")
    .replace(/&gt;/g,">")
    .replace(/&#(\d+);/g,function(_,n){ return String.fromCharCode(Number(n)); });
}

function clean(v) {
  return decode(String(v || "")
    .replace(/<script[\s\S]*?<\/script>/gi," ")
    .replace(/<style[\s\S]*?<\/style>/gi," ")
    .replace(/<noscript[\s\S]*?<\/noscript>/gi," ")
    .replace(/<svg[\s\S]*?<\/svg>/gi," ")
    .replace(/<[^>]*>/g," ")
    .replace(/\s+/g," ").trim());
}

function allowed(host) {
  host=host.toLowerCase().replace(/^www\./,"");
  return [
    "reddit.com","thehackernews.com","bleepingcomputer.com","krebsonsecurity.com",
    "theguardian.com","rtp.pt","cyclingnews.com","news.ycombinator.com"
  ].some(function(d){ return host===d || host.slice(-(d.length+1))==="."+d; });
}

function extract(html, fallback) {
  var title=html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  var blocks=[];
  var article=html.match(/<article[^>]*>([\s\S]*?)<\/article>/i);
  var main=html.match(/<main[^>]*>([\s\S]*?)<\/main>/i);
  var body=article ? article[1] : (main ? main[1] : html);

  var matches=body.match(/<(p|h2|h3|blockquote)[^>]*>[\s\S]*?<\/\1>/gi) || [];
  matches.forEach(function(x){
    var text=clean(x);
    if(text.length>=40 && text.length<=1200) blocks.push(text);
  });

  var unique=[], seen={};
  blocks.forEach(function(x){
    var k=x.slice(0,180);
    if(!seen[k]) { seen[k]=true; unique.push(x); }
  });

  return {
    title: clean(title ? title[1] : fallback) || fallback || "Artigo",
    paragraphs: unique.slice(0,60)
  };
}

module.exports=async function(req,res) {
  var raw=req.query && req.query.url;
  var target;

  try {
    target=new URL(raw);
  } catch(e) {
    res.status(400).send("URL inválido");
    return;
  }

  if(target.protocol!=="https:" || !allowed(target.hostname)) {
    res.status(403).send("Fonte não suportada pelo modo de leitura.");
    return;
  }

  try {
    var upstream=await fetch(target.toString(),{
      headers:{
        "User-Agent":"Mozilla/5.0 SocialHubReader/1.0",
        "Accept":"text/html,application/xhtml+xml"
      },
      redirect:"follow"
    });

    if(!upstream.ok) throw new Error("HTTP "+upstream.status);

    var html=await upstream.text();
    var data=extract(html,target.hostname);

    var content=data.paragraphs.map(function(p){
      return "<p>"+esc(p)+"</p>";
    }).join("");

    if(!content) {
      content="<p>Este site não disponibilizou o texto completo ao modo de leitura.</p>";
    }

    res.setHeader("Content-Type","text/html; charset=utf-8");
    res.setHeader("Cache-Control","s-maxage=300, stale-while-revalidate=900");
    res.status(200).send(
      "<!doctype html><html lang='pt-PT'><head><meta charset='utf-8'>"+
      "<meta name='viewport' content='width=device-width, initial-scale=1'>"+
      "<title>Leitura · "+esc(data.title)+"</title><link rel='stylesheet' href='/styles.css'></head>"+
      "<body><div class='page reader'><header class='header'>"+
      "<div class='brand'>SOCIAL HUB</div><div class='subtitle'>MODO DE LEITURA</div></header>"+
      "<main><div class='eyebrow'>ARTIGO</div><h1>"+esc(data.title)+"</h1>"+
      "<div class='reader-body'>"+content+"</div>"+
      "<p class='reader-note'>Conteúdo preparado na cloud para leitura no Lumia 830.</p>"+
      "</main><footer><a href='javascript:history.back()'>← VOLTAR</a></footer>"+
      "</div></body></html>"
    );
  } catch(e) {
    res.setHeader("Content-Type","text/html; charset=utf-8");
    res.status(200).send(
      "<!doctype html><html lang='pt-PT'><head><meta charset='utf-8'>"+
      "<meta name='viewport' content='width=device-width, initial-scale=1'>"+
      "<title>Social Hub · Leitura</title><link rel='stylesheet' href='/styles.css'></head>"+
      "<body><div class='page'><header class='header'><div class='brand'>SOCIAL HUB</div>"+
      "<div class='subtitle'>MODO DE LEITURA</div></header><main>"+
      "<div class='eyebrow'>AVISO</div><h1>Não foi possível preparar o artigo.</h1>"+
      "<p>A fonte recusou o acesso ou não disponibilizou o conteúdo numa estrutura compatível.</p>"+
      "</main><footer><a href='javascript:history.back()'>← VOLTAR</a></footer></div></body></html>"
    );
  }
};