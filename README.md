# Олимпиады — льготы при поступлении

Бесплатное приложение для школьников: олимпиады перечня РСОШ и ВсОШ, сроки этапов, льготы при поступлении в вузы.

**Открыть приложение:** https://anilibriabro.github.io/olympiads-data/
- на iPhone: откройте ссылку в Safari → кнопка «Скачать для iPhone» ([файл напрямую](https://anilibriabro.github.io/olympiads-data/Olimpiady-iPhone.mobileconfig)) → Настройки → «Профиль загружен» → «Установить». Или: «Поделиться» → «На экран Домой»;
- на Android: по ссылке есть кнопка «Скачать» (приложение с напоминаниями) или [APK напрямую](https://github.com/AnilibriaBro/olympiads-data/releases/latest/download/Olimpiady.apk);
- на компьютере: работает прямо в браузере.

## Что в репозитории

- корень (`index.html`, `assets/`, `sw.js`) — веб-версия приложения, её показывает GitHub Pages;
- `data/data.json` — данные, которые приложение скачивает при запуске;
- `data/ics/` — календари со сроками каждой олимпиады (подписка с iPhone);
- `scripts/` — сборщик данных. Источники: [rsr-olymp.ru](https://rsr-olymp.ru/) (перечень и уровни), [olimpiada.ru](https://olimpiada.ru/) (даты этапов).

Данные обновляются каждый день в 04:00 по Москве (`.github/workflows/update-data.yml`).
Запустить вручную: вкладка Actions → «Обновление данных» → Run workflow.
