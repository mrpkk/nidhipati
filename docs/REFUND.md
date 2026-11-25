# Возврат в кассе nidhipati: карта и USDC

Порядок для владельца. Клиенту — письмо; здесь — что нажать, что записать и чем доказать.
Правило сроков — общее для всей экосистемы: `onchain-ai-agent/docs/REFUND-RUNBOOK.md`.

## 1. Сначала — основание

Пишем одной строкой: **что** не доставлено и **какой срок** нарушен. Без этого возврат не
закрывается, даже если деньги ушли: через месяц никто не вспомнит, почему.

Проверить заказ: `GET /pay/order/<order_id>` — статус, письмо, срок ключа/доступ.

## 2. Установить статус `refunded`

Ручка закрыта токеном владельца (`NIDHIPATI_ADMIN_TOKEN` в
`/home/iamthat/.config/nidhipati/payment.env`), без токена — `403`.

```bash
# USDC: доказательство — хеш перевода
curl -s -X POST https://nidhipati.ailegal.legal/pay/refund \
  -H "X-Nidhipati-Admin: $NIDHIPATI_ADMIN_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"order_id":"ORD-1","reason":"отчёт не доставлен за 5 рабочих дней","tx_hash":"0x…"}'

# Карта: доказательство — ссылка/номер возврата у провайдера
curl -s -X POST https://nidhipati.ailegal.legal/pay/refund \
  -H "X-Nidhipati-Admin: $NIDHIPATI_ADMIN_TOKEN" \
  -H 'content-type: application/json' \
  -d '{"order_id":"ORD-1","reason":"возврат по карте, запрос клиента","refund_ref":"paygate-rf-…"}'
```

Ответ: `{"ok": true, "order": {…, "status": "refunded", "meta": {"refund_tx_hash": …}}}`.
Повторный вызов не дублирует: `{"duplicate": true}`.

## 3. Сами деньги

| Рельс | Как возвращаем | Где доказательство |
|---|---|---|
| **USDC (Base)** | перевод с адреса выплат на **тот же адрес**, с которого платили | `tx_hash` в Basescan |
| **Карта (PayGate)** | возврат в панели провайдера по `order_id` | `refund_ref` / номер операции |

Сумма — ровно оплаченная, без удержаний. На другой адрес не возвращаем: только откуда платили.

## 3.5 Покупатель узнаёт из письма, а не из выписки

`POST /pay/refund` сам отправляет письмо на `customer_email` из заказа: сумма, **доказательство**
(`tx_hash`/`refund_ref`), причина и фраза «ничего присылать не нужно». Ответ ручки показывает, ушло ли
письмо: `"refund_email": "sent"` или причина ошибки (тогда пишем вручную).

Реестр возвратов для сверки с деньгами: `GET /pay/refunds` (только с `X-Nidhipati-Admin`) —
заказ, сумма, провайдер, причина, доказательство, время; и общая сумма.

## 4. Записать и сообщить

1. `PROGRESS.md` проекта: дата, заказ, основание, доказательство.
2. `python3 /media/Sruti/iamthat/work/autonomy/progress.py add "nidhipati: возврат <order>, <причина>, <tx/ref>"`.
3. Письмо клиенту — с доказательством:

```
Subject: nidhipati: refund sent — <order_id>

We did not deliver <what> within <N> business days, so $<amount> is back.
Refund: <tx_hash | provider reference>
Funds go to the address/card you paid from.
Nothing is required from you; if it does not appear in an hour, reply here.
```

## Что мы не делаем

- Не удерживаем «комиссию за возврат».
- Не просим заявление и сканы.
- Не возвращаем дважды: статус `refunded` — терминальный, повтор даёт `duplicate`.
- Не подменяем возврат «продлением доступа» без согласия клиента.

## Проверено

21.11.2026: `POST /pay/refund` — 403 без токена и при незаданном токене, 400 без доказательства,
404 на неизвестный заказ, 200 с `status: refunded` и сохранённым хешем/ссылкой, повтор — `duplicate`;
`GET /pay/order/<id>` показывает `refunded`. Тесты: `tests/test_refund_status.py`.

## 5. Сколько осталось (26.11.2026)

Реестр возвратов показывает только возвращённое. Чтобы не считать «на глаз», касса отдаёт сверку:

```
curl -s -H "X-Nidhipati-Admin: $NIDHIPATI_ADMIN_TOKEN" \
  https://nidhipati.ailegal.legal/pay/refunds | python3 -m json.tool | grep -A3 totals
```

`totals.paid_usd` — оплачено, `totals.refunded_usd` — возвращено, **`totals.kept_usd` — осталось**
(оплачено минус возвращено; возврат в выручку не попадает). Суммы по разным валютам не складываются:
рядом лежит `by_status[*].other` с разбивкой по коду валюты.
