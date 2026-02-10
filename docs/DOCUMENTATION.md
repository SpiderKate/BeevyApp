OBSAH

Úvod
1	Analýza aplikace
1.1	Cíl aplikace
1.2	Účel a smysl aplikace
1.3	Cílová skupina uživatelů
1.4	Uživatelské role
1.5	Základní požadavky na aplikaci
1.6	Funkční požadavky aplikace
1.7	Nefunkční požadavky aplikace
2	Použité technologie
2.1	Backend aplikace
2.2	Frontend aplikace
2.3	Databáze
2.4	Správa souborů a nahrávání obsahu
3	Architektura aplikace
3.1	Struktura projektu
3.2	Architektura aplikace a tok dat
3.3	Oddělení jednotlivých částí aplikace
3.4	Databázový návrh
4	Implementace aplikace
4.1	Registrace a přihlášení uživatelů
4.2	Nahrávání a správa uměleckých děl
4.3	Prodej a nákup digitálního umění
4.4	Společný kreslící canvas
4.5	Komunitní sekce aplikace
4.6	Nabízení uměleckých služeb
5	Testování aplikace
5.1	Přístup k testování
5.2	Testovací prostředí
5.3	Testování uživatelských účtů
5.4	Testování nahrávání obsahu
5.5	Testování prodeje a nákupu
5.6	Testování společného canvasu
5.7	Testování komunitní sekce
5.8	Vyhodnocení testování
6	Uživatelská dokumentace
6.1	Přístup do aplikace
6.2	Registrace a přihlášení
6.3	Uživatelský profil
6.4	Nahrávání uměleckých děl
6.5	Prodej a nákup obsahu
6.6	Společný kreslící canvas
6.7	Komunitní sekce
6.8	Nabízení služeb
6.9	Doporučení pro uživatele
7	Možnosti dalšího rozvoje aplikace
7.1	Rozšíření uživatelských účtů
7.2	Platební systém
7.3	Rozvoj komunitních funkcí
7.4	Vylepšení společného canvasu
7.5	Optimalizace výkonu a škálovatelnost
7.6	Uživatelská zpětná vazba
Závěr
Seznam použité literatury
Přílohy

---

**Úvod**
Krátký popis projektu: BeevyApp je webová aplikace pro sdílení, prodej a společné kreslení digitálního umění. Aplikace poskytuje uživatelské účty, upload obrázků, generování náhledů s vodoznakem a metadata, tržiště (shop), a společný kreslící prostor (canvas) v reálném čase.

**1 Analýza aplikace**

1.1 Cíl aplikace
- Umožnit uživatelům vystavovat a prodávat digitální umění.
- Podpořit spolupráci pomocí společného kreslícího canvasu.
- Poskytnout bezpečné nahrávání a správu souborů s ochrannými metadaty.

1.2 Účel a smysl aplikace
- Vytvořit komunitní místo pro autory a kupující digitálního umění.
- Zjednodušit publikaci a prodej děl bez nutnosti externích tržišť.

1.3 Cílová skupina uživatelů
- Digitální umělci, ilustrátoři, hobby autoři.
- Kupující hledající originální digitální tvorbu.
- Komunity, které chtějí společně kreslit online.

1.4 Uživatelské role
- Anonymní návštěvník: prohlíží veřejné stránky.
- Registrovaný uživatel: nahrává, spravuje vlastní díla, účastní se canvasu, kupuje.
- Admin / správce: spravuje uživatele, moderuje obsah, provádí údržbu DB a backupy.

1.5 Základní požadavky na aplikaci
- Webové rozhraní pro práci s uživatelskými účty.
- Nahrávání obrázků (PNG/JPG/JPEG) s limitem velikosti.
- Předzobrazení (thumbnail/preview) a vodoznak pro ochranu obsahu.
- Ukládání metadat do PNG text chunků.
- Realtime kreslení pomocí WebSocket (Socket.IO).
- Jednoduché tržiště s evidencí vlastnictví (ownership).

1.6 Funkční požadavky aplikace
- Registrace a přihlášení uživatelů s hashováním hesel (bcrypt).
- Správa řešení se sessions a CSRF ochranou (Flask-WTF, CSRFProtect).
- Nahrávání souborů: ověření typu souboru, validace obrázku (Pillow), ukládání originálu a vytvoření watermarked preview.
- Metadata: ukládání autora, data nahrání a dalších informací do PNG.
- Marketplace (shop): přidání položek do prodeje, správa ownershipu tabulkou `art_ownership`.
- Společný canvas: stránka `draw.html` + `static/script/draw.js` využívá Socket.IO pro synchronizaci kreslení mezi uživateli.
- Uživatelský profil, nastavení, obnova hesla a základní bezpečnostní mechanismy.

1.7 Nefunkční požadavky aplikace
- Výkon: limity uploadů, omezení velikosti session, nasazení na WSGI nebo eventlet pro SocketIO.
- Bezpečnost: CSRF, hashování hesel, validace obsahu, omezení typů souborů.
- Udržovatelnost: strukturovaný projekt, migrations složka, zálohy DB (`beevy.db.bak*`).

**2 Použité technologie**

2.1 Backend aplikace
- Python 3 + Flask (Flask==3.1.2).
- Flask-SocketIO pro realtime komunikaci.
- Flask-WTF a CSRFProtect pro formuláře a ochranu.
- bcrypt / Flask-Bcrypt pro hashování hesel.
- python-dotenv pro konfiguraci prostředí (`SECRET_KEY`).
- Pillow (PIL) pro zpracování obrázků, vodoznaky a práci s PNG metadata.

2.2 Frontend aplikace
- Šablony Jinja2 (soubory v `templates/`).
- HTML/CSS ve `static/css/` (např. `draw.css`, `styles.css`).
- JavaScript: klient pro canvas v `static/script/draw.js` a Socket.IO klient.
- Ikony a obrázky ve `static/images/`.

2.3 Databáze
- SQLite (`beevy.db`) je používána jako lokální databáze.
- Migrations a zálohy jsou v adresáři `migrations/` a soubory záloh `beevy.db.bak.*`.

2.4 Správa souborů a nahrávání obsahu
- Upload složky: `static/uploads/` s podsložkami `avatar/`, `shop/examples`, `shop/original`, `shop/thumbs`.
- Limity velikosti (konfigurované v `app.config["MAX_CONTENT_LENGTH"]` a `MAX_FILE_SIZE`).
- Bezpečnost: `secure_filename()` a kontrola přípon přes `ALLOWED_EXTENSIONS`.
- Funkce `process_uploaded_image()` vytváří originál s metadata a watermarked preview (funkce v `app.py`).

**3 Architektura aplikace**

3.1 Struktura projektu
- Hlavní soubor aplikace: [app.py](app.py)
- Šablony: [templates/](templates/)
- Statické soubory: [static/](static/)
- Nahrané soubory: [static/uploads/](static/uploads/)
- Migrace a zálohy: [migrations/], `beevy.db.bak.*`
- Testy: [tests/]

3.2 Architektura aplikace a tok dat
- Uživatelský request → Flask route v `app.py` → zpracování formuláře / upload → DB operace (sqlite3) → uložený soubor do `static/uploads/` → vznik náhledu/vodoznaku přes Pillow → metadata uložena v PNG.
- Realtime: klient (draw.js) odesílá události přes Socket.IO → server (Flask-SocketIO) vysílá události do ostatních klientů ve stejné místnosti (room).

3.3 Oddělení jednotlivých částí aplikace
- Prezentační vrstva: Jinja2 šablony.
- Logika: `app.py` obsahuje kontrolery, validační a utility funkce (image processing, ownership checks).
- Perzistence: SQLite DB, jednoduché SQL dotazy přímo z `app.py`.
- Asynchronní/Realtime: Socket.IO (eventlet/async) pro canvas.

3.4 Databázový návrh
- Hlavní tabulky (přehled):
  - `users` — uživatelské účty (username, email, password hash, avatar_path, last_login_at, deleted flag,...)
  - `art` — záznamy o uměleckých dílech (cesta k souboru, název, popis, cena, owner_id,...)
  - `art_ownership` — vlastnictví uměleckých děl (art_id, owner_id)
  - Další pomocné tabulky pro transakce, komunikaci nebo služby dle implementace.
- Migrace: viz `migrations/migration_log.txt` a `scripts/migrate_db.py`.

**4 Implementace aplikace**

4.1 Registrace a přihlášení uživatelů
- Registrace: route `/register` (část v `app.py`) přijímá `username`, `password`, `name`, `surname`, `email`, `dob` a ukládá hashed heslo přes bcrypt.
- Přihlášení: `/login` kontroluje zadané jméno/e-mail, ověřuje bcrypt hash, nastavuje `session['username']` a aktualizuje `last_login_at`.
- Session management: `app.permanent_session_lifetime = timedelta(days=7)`.
- Ochrana: CSRF tokeny, kontrola existujících uživatelů, odkazy na obnovu účtu/další kroky.

4.2 Nahrávání a správa uměleckých děl
- Funkce validace: `allowed_file()` a `validate_image()` (použití Pillow pro verifikaci obrazu).
- Ukládání: `process_uploaded_image()` ukládá originál do `static/uploads/shop/original` a vytvoří watermarked preview v `static/uploads/shop/examples` nebo `thumbs`.
- Metadata: `add_metadata()` a `watermark_text_with_metadata()` vkládají textové PNG chunky a kreslí vodotisk na obrázek.
- Uživatelské avatary: ukládány v `uploads/avatar` (funkce `save_uploaded_file()` zajišťuje bezpečný název a uložení).
- Kontrola vlastníka: `user_owns_art(user_id, art_id)` kontroluje tabulku `art_ownership`.

4.3 Prodej a nákup digitálního umění
- Tržiště (shop): šablony `shop.html`, `owned_detail.html` a další poskytují rozhraní.
- Ownership a stav: při nákupu by se vytvořil záznam v `art_ownership` a případně aktualizovalo metadata.
- Platební systém: není v projektu plně integrován (viz sekce rozvoje). Prozatím se počítá s interním záznamem transakcí nebo směrováním na externí platební bránu.

4.4 Společný kreslící canvas
- Klient: `templates/draw.html` obsahuje `<canvas>` a toolbar (tvary, štětec, eraser, velikost), a připojuje `static/script/draw.js`.
- Realtime: Socket.IO knihovna na klientu a serveru (Flask-SocketIO) předává události o tahu/mazání/clear/save.
- Ukládání: tlačítko "Save as image" umožňuje lokální uložení nebo další serverové ukládání přes API (TODO poznámky v kódu).

4.5 Komunitní sekce aplikace
- Šablony `index.html`, `userPage.html`, a další poskytují prostor pro zobrazení děl, profilů a případně komentářů.
- Moderace a mazání: existuje flag `deleted` v `users` (viz přihlášení) a generování speciálních uživatelských jmen pro smazané uživatele (`generate_deleted_username()`).

4.6 Nabízení uměleckých služeb
- Systém pro nabídku služeb může být založen na obdobné struktuře jako shop — položky ke koupi, textové popisy a kontaktní údaje.
- V současné implementaci jsou šablony a základy pro rozšíření; obchodní logika by vyžadovala nové DB tabulky pro objednávky.

**5 Testování aplikace**

5.1 Přístup k testování
- Projekt obsahuje adresář `tests/` s několika testy: `test_delete_behavior.py`, `test_editprocess.py`, `test_metadata.py`, `test_migration.py`.

5.2 Testovací prostředí
- Používá se `pytest` dle `requirements.txt`.
- Doporučené: virtuální prostředí (venv) a nastavení dočasné DB pro testy.

5.3 Testování uživatelských účtů
- Testy ověřují registraci, přihlášení, chování s "deleted" účty a session chování.

5.4 Testování nahrávání obsahu
- Testy validují zpracování obrázků, generování náhledů a přidávání metadata.

5.5 Testování prodeje a nákupu
- Prozatím omezené; lze simulovat záznamy v tabulce `art_ownership` a ověřit logiku `user_owns_art()`.

5.6 Testování společného canvasu
- Vyžaduje integrační testy se Socket.IO — simulace událostí a kontrola broadcastů.

5.7 Testování komunitní sekce
- Testy zaměřené na šablony a přístupová práva k uživatelským stránkám.

5.8 Vyhodnocení testování
- Celková doporučení: rozšířit coverage testů pro transakce a realtime scénáře.

**6 Uživatelská dokumentace**

6.1 Přístup do aplikace
- Spusťte aplikaci dle README (`python app.py` nebo přes SocketIO runner). Nastavte `SECRET_KEY` v `.env`.

6.2 Registrace a přihlášení
- Otevřete `/register` pro vytvoření účtu; po registraci přihlaste přes `/login`.

6.3 Uživatelský profil
- Po přihlášení přejděte na `userPage` (odkazy v hlavním menu). Zde spravujete avatar, díla a nastavení.

6.4 Nahrávání uměleckých děl
- Použijte formulář nahrávání ve `create_art.html` (šablona). Podporované formáty: PNG, JPG, JPEG. Velikost souboru omezena konfigurací.
- Po nahrání systém uloží originál, vodoznakovaný náhled a přidá metadata.

6.5 Prodej a nákup obsahu
- Přidejte dílo do shopu přes rozhraní (pokud dostupné). Při koupi se aktualizuje vlastnictví (vnitřní DB záznamy).

6.6 Společný kreslící canvas
- Otevřete `/draw` nebo odpovídající stránku; zvolte nástroj, barvu a velikost. Kreslení se posílá ostatním uživatelům v místnosti.
- Tlačítko "Save as image" ukládá snímek canvasu.

6.7 Komunitní sekce
- Využijte `index.html` a profilových stránek pro prohlížení a interakci s autory.

6.8 Nabízení služeb
- V současné verzi lze nabízet služby ručně v popisku profilu; doporučené rozšíření dle sekce 7.

6.9 Doporučení pro uživatele
- Nahrávejte originály v co nejvyšší kvalitě (PNG), používejte popisky a tagy pro lepší dohledatelnost.

**7 Možnosti dalšího rozvoje aplikace**

7.1 Rozšíření uživatelských účtů
- Role, verifikace, víceúrovňové profily, portfolio sekce.

7.2 Platební systém
- Integrace platebních bran (Stripe, PayPal), evidování transakcí a automatické převody vlastnictví.

7.3 Rozvoj komunitních funkcí
- Komentáře, lajky, sledování autorů, moderované diskuse, reporty obsahu.

7.4 Vylepšení společného canvasu
- Historie akcí, vracení zpět, vrstvy, export projektů, persistentní ukládání do DB nebo storage.

7.5 Optimalizace výkonu a škálovatelnost
- Přechod z SQLite na PostgreSQL/MySQL pro větší projekty, CDN pro statické soubory, horizontální škálování Socket.IO.

7.6 Uživatelská zpětná vazba
- Mechanismy sběru zpětné vazby, A/B testování nových funkcí.

**Závěr**
BeevyApp kombinuje základní funkce tržiště s nástroji pro spolupráci a ochranou nahraného obsahu. Projekt poskytuje solidní základ pro další rozšíření směrem k plnohodnotné platformě pro digitální umění.

**Seznam použité literatury**
- Dokumentace Flask, Flask-SocketIO, Pillow, bcrypt, Jinja2.
- Interní soubory projektu: [app.py](app.py), [templates/](templates/), [static/](static/), [requirements.txt](requirements.txt).

**Přílohy**
- Výpis důležitých souborů: `app.py`, `requirements.txt`, `migrations/migration_log.txt`, `tests/`.
- Seznam záloh DB: `beevy.db.bak.*`.

---

Poznámky: Dokument je generován na základě obsahu projektu v pracovním adresáři. Pro hlubší technickou dokumentaci (přesné SQL schéma, API endpoints s parametry, úplné sekvence v Socket.IO) doporučuji doplnit skripty migrací a detailní popisy rout v `app.py`.
