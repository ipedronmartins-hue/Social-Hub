module.exports = function (req, res) {
  var source = (req.query && req.query.source) || "all";

  var names = {
    reddit: "REDDIT",
    youtube: "YOUTUBE",
    news: "NOTÍCIAS",
    all: "SOCIAL HUB"
  };

  var title = names[source] || names.all;

  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");

  res.status(200).send(
    "<!doctype html>" +
    "<html lang='pt-PT'><head>" +
    "<meta charset='utf-8'>" +
    "<meta name='viewport' content='width=device-width, initial-scale=1'>" +
    "<title>Social Hub - " + title + "</title>" +
    "<link rel='stylesheet' href='/styles.css'>" +
    "</head><body><div class='page'>" +
    "<header class='header'><div class='brand'>SOCIAL HUB</div>" +
    "<div class='subtitle'>FEED · " + title + "</div></header>" +
    "<main><section class='hero'>" +
    "<div class='eyebrow'>" + title + "</div>" +
    "<h1>Ligação estabelecida.</h1>" +
    "<p>O Lumia conseguiu chamar uma Serverless Function da Vercel.</p>" +
    "</section>" +
    "<article class='card'>" +
    "<div class='card-source'>TESTE 01</div>" +
    "<h2>WP8.1 → Vercel → HTML</h2>" +
    "<p>Este conteúdo foi gerado no servidor. O telefone não precisou de JavaScript moderno.</p>" +
    "<div class='card-time'>OK</div>" +
    "</article>" +
    "</main><footer><a href='/' style='color:#fff'>← VOLTAR</a></footer>" +
    "</div></body></html>"
  );
};
