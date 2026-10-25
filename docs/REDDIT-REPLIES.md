# Reddit replies — status

**Правило:** владелец разрешил публикацию 26.10.2026. Агент публикует, но не выдаёт себя за владельца и не спорит.

---

## 1. Ответ SashSail — тред «1,900 x402 APIs» (1x9xgci)

**Наш первый комментарий:** https://www.reddit.com/r/AI_Agents/comments/1x9xgci/comment/19rmf1w5szf44/
**Его ответ:** «Duplicates can’t come from our side… 651 purchases failed after payment: 127 settled, 515 never had. Details…»

**Опубликованный ответ (26.10.2026, 01:26 MSK):**
https://www.reddit.com/r/AI_Agents/comments/1x9xgci/comment/19rnd4diwds1x/

Текст:

> Your 651 / 127 / 515 split is the cleanest version of this I have seen.
>
> The 515 are not a loss, and adding them to the 127 would overstate the problem by about 4x. The audit needs three states, not two: settled + delivered, settled + no delivery, and not settled / unproven. A single "failed" bucket is what turns a 19.5% settlement problem into a 100% loss claim.
>
> Did the 127 eventually get refunded or replayed? And when your later pass finds the transfer but no delivery, do you keep it as "settled + unproven" rather than counting it as failed? That is the distinction I care about — don't let "couldn't see it" become "didn't happen".
>
> The browser version of the audit keeps those buckets separate (no upload): https://mrpkk.github.io/nidhipati/free-spend-audit.html

**Статус:** виден в треде, не removed, score 1 на момент публикации. Ждём ответа SashSail.

---

## 2. Что не публиковать

- Не отвечать на старые комментарии повторно.
- Не утверждать, что «мы нашли у него дубли» — его данные говорят обратное.
- Не спорить о 127/515: это его измерение, оно полезнее нашего предположения.
