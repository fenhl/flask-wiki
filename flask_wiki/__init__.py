import re

import flask # PyPI: Flask
import flask_pagedown.fields # PyPI: Flask-PageDown
import flask_wtf # PyPI: Flask-WTF
import flaskext.markdown # PyPI: Flask-Markdown
import jinja2 # PyPI: Jinja2
import markdown # PyPI: Markdown
import markdown.inlinepatterns # PyPI: Markdown
import markdown.util # PyPI: Markdown

import flask_view_tree # https://github.com/fenhl/flask-view-tree

DISCORD_MENTION_REGEX = '<@!?([0-9]+)>'
DISCORD_TAG_REGEX = '@([^#]{2,32})#([0-9]{4}?)'

def child(node, name='wiki', display_string=None, *, md, user_class, wiki_root, **options):
    return setup(md, user_class, wiki_root, node.child(name, display_string, **options))

def index(app, *, md, user_class, wiki_root, **options):
    return setup(md, user_class, wiki_root, flask_view_tree.index(app, **options))

def render_template(template_name, **kwargs):
    if template_name is None:
        template_path = f'{flask.request.endpoint.replace(".", "/")}.html.j2'
    else:
        template_path = f'{template_name.replace(".", "/")}.html.j2'
    return jinja2.Markup(flask.render_template(template_path, **kwargs))

def setup(md, user_class, wiki_name, wiki_root, decorator):
    class DiscordMentionPattern(markdown.inlinepatterns.LinkInlineProcessor):
        def handleMatch(self, m, data):
            user = user_class(m.group(1))
            el = markdown.util.etree.Element('a')
            el.text = f'@{user.name}'
            el.set('href', user.profile_url)
            return el, m.start(0), m.end(0)

    class DiscordMentionExtension(markdown.Extension):
        def extendMarkdown(self, md, md_globals):
            config = self.getConfigs()
            md.inlinePatterns.add('discord-mention', DiscordMentionPattern(DISCORD_MENTION_REGEX, md), '<reference')

    md.register_extension(DiscordMentionExtension)

    @decorator
    def wiki_index():
        return render_template('wiki.index', wiki_name=wiki_name)

    wiki_index.redirect_namespaces = {'wiki': lambda title: flask.g.view_node.parent.url}

    @wiki_index.children()
    def wiki_article(title):
        if wiki_index.exists('wiki', title):
            return render_template('wiki.article', title=title, namespace='wiki', wiki_name=wiki_name)
        else:
            return render_template('wiki.404', title=title, namespace='wiki', wiki_name=wiki_name), 404

    @wiki_article.children()
    def wiki_article_namespaced(title, namespace):
        if namespace in wiki_index.redirect_map:
            return flask.redirect(wiki_index.redirect_namespaces[namespace](title))
        elif wiki_index.exists(namespace, title):
            return render_template('wiki.article', title=title, namespace=namespace, wiki_name=wiki_name)
        else:
            return render_template('wiki.404', title=title, namespace=namespace, wiki_name=wiki_name), 404

    class MarkdownField(flask_pagedown.fields.PageDownField):
        def _value(self):
            if self.raw_data:
                return self.raw_data[0]
            elif self.data is not None:
                return mentions_to_tags(self.data)
            else:
                return ''

        def process_formdata(self, valuelist):
            if valuelist:
                self.data = tags_to_mentions(valuelist[0])

    def WikiEditForm(namespace, title, source):
        class Form(flask_wtf.FlaskForm):
            source = MarkdownField('Text', default=source)
            submit_wiki_edit_form = wtforms.SubmitField('Speichern')

        return Form()

    @wiki_article_namespaced.child('edit')
    def wiki_article_edit(title, namespace):
        source = wiki_index.source(namespace, title)
        wiki_edit_form = WikiEditForm(source)
        if wiki_edit_form.submit_wiki_edit_form.data and wiki_edit_form.validate():
            wiki_index.save(namespace, title, wiki_edit_form.source.data)
            return flask.redirect(flask.g.view_node.parent.url)
        return render_template('wiki.edit', title=title, namespace=namespace, wiki_name=wiki_name, wiki_edit_form=wiki_edit_form)

    @wiki_article_namespaced.child('history')
    def wiki_article_history(title, namespace):
        return render_template('wiki.history', title=title, namespace=namespace)

    @app.before_request
    def current_time():
        flask.g.wiki = wiki_index

    def mentions_to_tags(text):
        while True:
            match = re.search(DISCORD_MENTION_REGEX, text)
            if not match:
                return text
            text = f'{text[:match.start()]}@{user_class(match.group(1))}{text[match.end():]}'

    def tags_to_mentions(text):
        while True:
            match = re.search(DISCORD_TAG_REGEX, text)
            if not match:
                return text
            text = f'{text[:match.start()]}<@{user_class.by_tag(match.group(1), int(match.group(2))).snowflake}>{text[match.end():]}'

    def exists(namespace, title):
        article_path = wiki_root / namespace / f'{title}.md'
        return article_path.exists()

    def namespaces():
        for namespace_dir in sorted(wiki_root.iterdir()):
            yield namespace_dir.name, sorted(article.stem for article in namespace_dir.iterdir())

    def save(namespace, title, text):
        article_path = wiki_root / namespace / f'{title}.md'
        with article_path.open('w') as article_f:
            article_f.write(text)

    def source(namespace, title):
        article_path = wiki_root / namespace / f'{title}.md'
        with article_path.open() as article_f:
            return article_f.read()

    wiki_index.exists = exists
    wiki_index.namespaces = namespaces
    wiki_index.save = save
    wiki_index.source = source

    return wiki_index
