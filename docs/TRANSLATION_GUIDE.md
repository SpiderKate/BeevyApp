# 🌍 Translation System Guide

## Přehled systému

BeevyApp má **kompletní vícejazykový systém** s podporou angličtiny (en) a češtiny (cs). Všechny uživatelské texty - templaty, flash zprávy, tlačítka - jsou automaticky překládány podle jazyka zvoleného uživatelem.

---

## 📁 Struktura překladového systému

```
BeevyApp/
├── translations.py                    # Hlavní modul pro správu překladů
├── static/languages/                  # Složka s jazykovými soubory
│   ├── en.json                       # Anglické překlady
│   └── cs.json                       # České překlady
├── templates/                         # Šablony používají translations systém
│   ├── base.html
│   ├── login.html
│   ├── ... atd
│   └── [všechny šablony]
└── app.py                            # Hlavní aplikace s flash() wrapper
```

---

## 🎯 Jak funguje překlad

### 1. V šablonách (Templates)
```jinja2
<!-- Překlad v šablonách -->
<button>{{ g.trans.get('buttons.save', g.user_language) }}</button>
<p>{{ g.trans.get('messages.welcome', g.user_language) }}</p>
```

### 2. Ve flash zprávách (Python)
```python
# Automatický překlad - bez jakýchkoli změn v kódu!
flash("Successfully logged in.", "success")
# → Automaticky se přeloží: "Úspěšně přihlášeni."
```

### 3. Jazykové soubory (JSON)
```json
{
  "nav": {
    "logout": "Logout",
    "settings": "Settings"
  },
  "buttons": {
    "save": "Save",
    "cancel": "Cancel"
  },
  "flash": {
    "login_success": "Successfully logged in.",
    "password_incorrect": "Current password is incorrect."
  }
}
```

---

## ➕ Jak přidat nový jazyk

### Krok 1: Vytvořit JSON soubor
Vytvořte nový soubor v `static/languages/` s kódem jazyka (např. pro francouzštinu: `fr.json`):

```bash
static/languages/
├── en.json
├── cs.json
└── fr.json          # Nový jazyk
```

### Krok 2: Zkopírovat strukturu
Zkopírujte strukturu z `en.json` a přeložte všechny hodnoty:

```json
{
  "nav": {
    "logout": "Déconnexion",
    "settings": "Paramètres",
    "profile": "Profil",
    "shop": "Boutique",
    "draw": "Dessiner",
    "user_page": "Ma Page"
  },
  "buttons": {
    "save": "Enregistrer",
    "cancel": "Annuler",
    ...
  },
  "flash": {
    "login_success": "Connecté avec succès.",
    "password_incorrect": "Le mot de passe actuel est incorrect.",
    ...
  }
  ... (zbývající sekce)
}
```

### Krok 3: Registrovat jazyk v `translations.py`
Otevřete `translations.py` a přidejte jazyk do slovníku dostupných jazyků:

```python
# V translations.py sekce AVAILABLE_LANGUAGES

AVAILABLE_LANGUAGES = {
    'en': 'English',
    'cs': 'Čeština (Czech)',
    'fr': 'Français (French)'  # Nový jazyk
}
```

### Krok 4: Přidat do UI (nastavení)
Aktualizujte šablonu [templates/settingsAccount.html](../templates/settingsAccount.html):

```html
<select name="language" id="language">
    <option value="en" {% if user_language == 'en' %}selected{% endif %}>English</option>
    <option value="cs" {% if user_language == 'cs' %}selected{% endif %}>Čeština (Czech)</option>
    <option value="fr" {% if user_language == 'fr' %}selected{% endif %}>Français (French)</option>
</select>
```

### Krok 5: Otestovat
1. Spusťte aplikaci:
```bash
python app.py
```

2. Zaregistrujte se nebo se přihlašte
3. Jděte na Settings → Account
4. Vyberte nový jazyk
5. Zkuste akci, která zobrazí flash zprávu (např. login)

---

## 📝 Struktura JSON souborů

### Aktuální sekce v `en.json` a `cs.json`:

| Sekce | Obsahuje | Příklady klíčů |
|-------|----------|--|
| **nav** | Navigační prvky | logout, settings, profile, shop |
| **home** | Domovská stránka | title, subtitle, login, register |
| **auth** | Ověřování | login_button, register_button, password |
| **settings** | Nastavení | theme, language, avatar, bio |
| **shop** | Obchod | price, artist, buy_for |
| **draw** | Kreslení | shapes, rectangle, circle, brush |
| **art** | Umění/Galerie | title, description, slots, examples |
| **messages** | Obecné zprávy | no_artworks, download_original, optional |
| **buttons** | Tlačítka | save, cancel, delete, back, clear |
| **flash** | Flash notifikace | login_success, password_incorrect, etc. |

---

## 🔍 Jak přidat nový překlad

### V šablonách:
1. Identifikujte text: `"Download Original"`
2. Přidejte klíč do `en.json` a `cs.json`:
```json
{
  "shop": {
    "download_original": "Download Original"
  }
}
```
3. V šabloně použijte:
```jinja2
{{ g.trans.get('shop.download_original', g.user_language) }}
```

### Ve flash zprávách:
1. Identifikujte text: `"Settings saved successfully."`
2. Přidejte do `FLASH_MESSAGE_KEYS` v `app.py`:
```python
FLASH_MESSAGE_KEYS = {
    "Settings saved successfully.": "flash.settings_saved",
    # Nový klíč
}
```
3. Přidejte překlad do JSON:
```json
{
  "flash": {
    "settings_saved": "Settings saved successfully."
  }
}
```
4. V Python kódu stačí normálně: `flash("Settings saved successfully.", "success")`

---

## ⚙️ Jak ověřit překlady

### Test Python
```bash
cd c:\Users\katen\OneDrive\Dokumenty\GitHub\BeevyApp
.venv\Scripts\python.exe -c "from translations import translations; print(translations.get_available_languages())"
```

### Test konkrétního klíče
```bash
.venv\Scripts\python.exe -c "from translations import translations; print('EN:', translations.get('nav.logout', 'en')); print('CS:', translations.get('nav.logout', 'cs'))"
```

### Ověřit validitu JSON
```bash
.venv\Scripts\python.exe -c "import json; json.load(open('static/languages/en.json'))"
```

---

## 🐛 Běžné chyby

### Chyba: "KeyError: 'art'"
**Příčina:** JSON soubor má syntaktickou chybu (chybí čárka, uvozovka, atd.)  
**Řešení:** Ověřte JSON syntaxi pomocí validátoru (https://jsonlint.com/)

### Chyba: Překlad se nezobrazuje
**Příčina:** Klíč není v JSON souboru  
**Řešení:** Přidejte klíč do všech jazykových souborů (en.json, cs.json, atd.)

### Chyba: Flash zpráva se neobjeví
**Příčina:** Zpráva není v `FLASH_MESSAGE_KEYS`  
**Řešení:** Přidejte mapování v `app.py`

---

## 📊 Statistika překladů

**Počet překladových klíčů:**
- **nav**: 6 položek
- **home**: 8 položek
- **auth**: 10 položek
- **settings**: 13 položek
- **shop**: 8 položek
- **draw**: 16 položek
- **art**: 18 položek
- **messages**: 23 položek
- **buttons**: 10 položek
- **flash**: 33 položek

**Celkem: ~145 překladových klíčů** za 2 jazyky

---

## 🚀 Příklady použití

### Příklad 1: Nový jazyk - Němčina (de)
1. Vytvořte `static/languages/de.json`
2. Přeložte všechny klíče do němčiny
3. V `translations.py` přidejte: `'de': 'Deutsch'`
4. V `settingsAccount.html` přidejte volbu pro němčinu
5. Test: Přihlasťe se, vyberte němčinu, všechno by mělo být v němčině

### Příklad 2: Nová flash zpráva
Potřebujete přidat zprávu "Payment successful. Thank you!":
1. V `en.json` přidejte:
```json
{
  "flash": {
    "payment_success": "Payment successful. Thank you!"
  }
}
```
2. V `cs.json` přidejte:
```json
{
  "flash": {
    "payment_success": "Platba byla úspěšná. Děkuji!"
  }
}
```
3. V `app.py` přidejte do `FLASH_MESSAGE_KEYS`:
```python
"Payment successful. Thank you!": "flash.payment_success",
```
4. V Python kódu jednoduše: `flash("Payment successful. Thank you!", "success")`

---

## 📚 Další zdroje

- [translations.py](../translations.py) - Implementace translačního systému
- [app.py](../app.py) - Flash wrapper a integraci
- [static/languages/](../static/languages/) - Jazykové soubory
- [templates/](../templates/) - Šablony s překlady
- [THEME_SYSTEM_GUIDE.md](THEME_SYSTEM_GUIDE.md) - Průvodce motivy
- [BACKUP_SETUP.md](BACKUP_SETUP.md) - Průvodce zálohováním

---

## ✅ Kontrolní seznam pro nový jazyk

- [ ] Vytvořen `static/languages/[lang_code].json`
- [ ] Všechny klíče z `en.json` jsou přeloženy
- [ ] JSON syntaxe je správná
- [ ] Jazyk zaregistrován v `translations.py` → `AVAILABLE_LANGUAGES`
- [ ] Možnost vybrat jazyk v `settingsAccount.html`
- [ ] Testovány překlady (flash zprávy, tlačítka, text)
- [ ] Databáze uživatelů ukládá jazykovou preferencí ✓

---

**Poslední aktualizace:** 7. února 2026  
**Jazyky:** English (en), Čeština (cs)
