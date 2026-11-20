#!/bin/bash
# Проверка кошелька на всех платных страницах + тревога в Telegram, если разошлось.
#
# Зачем: адрес в ~/.env меняется редко, и именно поэтому о нём забывают. Этот
# скрипт превращает «помни про verify» в «узнаешь сам»: cron раз в сутки, при
# расхождении — сообщение владельцу, а не молчание.
#
#   bash scripts/verify_wallet.sh          # показать результат
#   bash scripts/verify_wallet.sh --quiet  # только при проблеме (для cron)

set -uo pipefail
ROOT="/media/Sruti/iamthat/work/sales/nidhipati"
ENV_FILE="/home/iamthat/.env"
QUIET="${1:-}"

out=$(cd "$ROOT" && /usr/bin/python3 scripts/usdc_block.py --verify 2>&1)
code=$?

if [ "$code" -eq 0 ]; then
  [ "$QUIET" = "--quiet" ] || echo "$out"
  exit 0
fi

echo "$out"

# Тревога в Telegram: тот же бот, что у отчётов агента.
token=$(grep -E '^TG_TOKEN=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"')
if [ -z "$token" ]; then
  echo "TG_TOKEN не задан — тревога только в stdout" >&2
  exit "$code"
fi

text="⚠️ Nidhipati: адрес USDC на страницах не совпадает с ~/.env. Проверить и запустить: cd $ROOT && python3 scripts/usdc_block.py --sync"
curl -s --max-time 20 --socks5-hostname 127.0.0.1:9050 \
  --data-urlencode "chat_id=330822359" \
  --data-urlencode "text=$text" \
  "https://api.telegram.org/bot${token}/sendMessage" >/dev/null || true

exit "$code"
