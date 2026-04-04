<!-- これはサブエージェントが生成しました -->
---
title: "{{ title }}"
tags:
	{% if tags %}
{% for t in tags %}
	- "{{ t }}"
{% endfor %}
	{% else %}
	- []
	{% endif %}
source_refs:
{% for ref in source_refs %}
	- "{{ ref }}"
{% endfor %}
---

# {{ title }}

{% if intro %}
{{ intro }}
{% endif %}

{% for section in sections %}

## {{ section.heading }}

{{ section.content }}

{% endfor %}

<!--
実行/検証:
Python で Jinja2 を使ってレンダリングするか、tools/docagent/generate.py のテンプレートとして使用して動作確認してください。
例:
from jinja2 import Template
tpl = Template(open('tools/docagent/templates/basic_page.tpl.md').read())
print(tpl.render(title='Test', tags=['a','b'], source_refs=['src.py'], intro='導入', sections=[{'heading':'h1','content':'本文'}]))
-->
