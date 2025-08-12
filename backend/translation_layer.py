import os
import json
import logging
from datetime import datetime
# Import the official Google Cloud Translate library
from google.cloud import translate_v2 as translate

class TranslationLayer:
    def __init__(self):
        self.logger = logging.getLogger("TRANSLATION_LAYER")
        self.logger.setLevel(logging.INFO)
        try:
            # Initialize the official client
            self.translator = translate.Client()
            self.cache_file = "translation_cache.json"
            self.cache = self.load_cache()
            self.logger.info("TranslationLayer with google-cloud-translate initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Cloud Translate client: {e}")
            self.logger.error("Please ensure you have authenticated with Google Cloud SDK. Run 'gcloud auth application-default login'")
            self.translator = None

    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading translation cache: {e}")
                return {}
        return {}

    def save_cache(self):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving translation cache: {e}")

    def translate(self, text, target_language='en'):
        if not text or not self.translator:
            return text

        cache_key = f"{text}_{target_language}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            # The official library returns a dictionary
            result = self.translator.translate(text, target_language=target_language)
            translation = result['translatedText']
            
            self.cache[cache_key] = translation
            self.save_cache()
            return translation
        except Exception as e:
            self.logger.error(f"Translation error with google-cloud-translate: {e}")
            return text # Return original text on failure

    def translate_response(self, response, target_language='en'):
        if not response or not isinstance(response, dict):
            return response

        translated_response = {}
        for key, value in response.items():
            if isinstance(value, str):
                translated_response[key] = self.translate(value, target_language)
            elif isinstance(value, dict):
                translated_response[key] = self.translate_response(value, target_language)
            elif isinstance(value, list):
                translated_response[key] = [
                    self.translate_response(item, target_language) if isinstance(item, dict)
                    else self.translate(item, target_language) if isinstance(item, str)
                    else item for item in value
                ]
            else:
                translated_response[key] = value
        return translated_response
