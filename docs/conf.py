import os
import sys
sys.path.insert(0, os.path.abspath("../"))

project = 'cpzonoff'
copyright = '2023, Watanabe Takashi'
author = 'Watanabe Takashi'

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon', 'sphinx_click.ext']

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
language = 'ja'
html_theme = 'bizstyle'
html_static_path = ['_static']
