#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
. ./.article.env

OWNER_ID=-242598887
ARTICLE_ID=373183
TITLE=$(sed -n 's/^# //p' docs/article.md | head -n 1)

# articles.save нет в документации VK: тело статьи он берёт только из параметра markdown, остальные молча игнорирует
answer=$(curl -s https://api.vk.com/method/articles.save \
  --data-urlencode "access_token=$VK_ARTICLE_TOKEN" -d v=5.199 \
  -d owner_id="$OWNER_ID" -d article_id="$ARTICLE_ID" \
  --data-urlencode "title=$TITLE" --data-urlencode "markdown@docs/article.md")
echo "$answer"
case "$answer" in *'"error"'*) exit 1 ;; esac
