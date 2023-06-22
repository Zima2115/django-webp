# -*- coding: utf-8 -*-
import os
import logging
import requests
from io import BytesIO
from PIL import Image

from django import template
from django.conf import settings
from django.core.files.base import ContentFile
from django.contrib.staticfiles import finders
from django.core.files.storage import default_storage
from django.templatetags.static import static

from django.conf import settings
from django_webp.utils import WEBP_STATIC_URL, WEBP_STATIC_ROOT, WEBP_DEBUG

base_path = settings.BASE_DIR
register = template.Library()


class WEBPImageConverter:

    def generate_path(self, image_path):
        """ creates all folders necessary until reach the file's folder """
        folder_path = os.path.dirname(image_path)
        if not os.path.isdir(folder_path):
            os.makedirs(folder_path)

    def get_static_image(self, image_url):
        if "https://" in image_url:
            return image_url
        else:
            return static(image_url)

    def get_generated_image(self, image_url):
        """ Returns the url to the webp gerenated image,
        if the image doesn't exist or the generetion fails,
        it returns the regular static url for the image """
        
        if "https://" in image_url:
            # Split the text by forward slashes and gets the last part (characters after the last slash)
            raw_filename = image_url.split('/')[-1]
            real_url = os.path.join("online_images/", os.path.splitext(raw_filename)[0] + '.webp')
        else:
            real_url = os.path.splitext(image_url)[0] + '.webp'
            
        generated_path = os.path.join(WEBP_STATIC_ROOT, real_url).lstrip('/')
        real_url = WEBP_STATIC_URL + real_url
    

        # Looks for image if hosted locally/checks if link provided is still valid
        if "https://" in image_url:
            pass
        else:
            image_path = finders.find(image_url)
            if not image_path:
                return self.get_static_image(image_url)
            
        if "https://" in image_url:
            if not self.generate_webp_image(generated_path, image_url):
                print(f"Failed to generate from URL: {image_url}")
                return self.get_static_image(image_url)
        else:
            if not self.generate_webp_image(generated_path, image_path):
                return self.get_static_image(image_url)
            
        return real_url   

    def generate_webp_image(self, generated_path, image_path, is_url=True):
        
        full_imgpath = os.path.join(str(base_path), generated_path)
        
        ## Prevents duplicates of generated images by checking if the already exist in a directory
        # Checks for locally hosted images
        if os.path.exists(full_imgpath) and "https://" not in image_path:
            return True
        
        # Checks for non-locally hosted images
        if "https://" in image_path:
            if os.path.exists(full_imgpath):
                return True

        ## Generating images if they do not exist in a directory
        
        # Getting the image data
        if "https://" in image_path:
            response = requests.get(image_path)
            try:
                image = Image.open(BytesIO(response.content))
            except:
                print(f"Error: Failed to read the image file from URL: {image_path}")
                return False
        else:
            try:
                image = Image.open(image_path)
            except FileNotFoundError:
                return False
        
        # Using the image data to save a webp version of it to static files
        try:
            self.generate_path(generated_path)
            buffer = BytesIO() # we use a buffer to store the contents of our conversion before saving to disk
            image.save(buffer, 'WEBP')
            content_file = ContentFile(buffer.getvalue())
            default_storage.save(full_imgpath, content_file)
            image.close()
            return True
        except KeyError:
            logger = logging.getLogger(__name__)
            logger.warn('WEBP is not installed in pillow')
        except (IOError, OSError):
            logger = logging.getLogger(__name__)
            logger.warn('WEBP image could not be saved in %s' % generated_path)
            
        return False


@register.simple_tag(takes_context=True)
def webp(context, value, force_static=WEBP_DEBUG):
    converter = WEBPImageConverter()

    supports_webp = context.get('supports_webp', False)
    if not supports_webp or force_static:
        return converter.get_static_image(value)

    return converter.get_generated_image(value)
