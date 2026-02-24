import json
import os

class Translations:
    def __init__(self, languages_dir='static/languages'):
        self.languages_dir = languages_dir
        self.strings = {}
        self.available_languages = {}
        self._load_all_languages()
    
    def _load_all_languages(self):
        """Load all available language files"""
        if not os.path.exists(self.languages_dir):
            return
        
        for file in os.listdir(self.languages_dir):
            if file.endswith('.json'):
                lang_code = file[:-5]  # Remove .json
                try:
                    with open(os.path.join(self.languages_dir, file), 'r', encoding='utf-8') as f:
                        self.strings[lang_code] = json.load(f)
                        # Store friendly names
                        self.available_languages[lang_code] = self._get_language_name(lang_code)
                except Exception as e:
                    print(f"Error loading language file {file}: {e}")
    
    def _get_language_name(self, lang_code):
        """Get friendly name for language code"""
        names = {
            'en': 'English',
            'cs': 'Čeština'
        }
        return names.get(lang_code, lang_code.upper())
    
    def get(self, key, language='en', default=''):
        """
        Get translation string using dot notation
        Example: trans.get('auth.login_title', 'en')
        """
        if language not in self.strings:
            language = 'en'  # Fallback to English
        
        keys = key.split('.')
        value = self.strings.get(language, {})
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value else default
    
    def get_all(self, language='en'):
        """Get all translations for a language"""
        return self.strings.get(language, {})
    
    def get_available_languages(self):
        """Get dict of available languages"""
        return self.available_languages
    
    def language_exists(self, lang_code):
        """Check if language exists"""
        return lang_code in self.strings


# Initialize translations
translations = Translations()
