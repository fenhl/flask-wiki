import re

import flask # PyPI: Flask
import flask_pagedown.fields # PyPI: Flask-PageDown
import flask_wtf # PyPI: Flask-WTF
import flaskext.markdown # PyPI: Flask-Markdown
import jinja2 # PyPI: Jinja2
import markdown # PyPI: Markdown
import markdown.inlinepatterns # PyPI: Markdown
import markdown.util # PyPI: Markdown
import wtforms # PyPI: WTForms

import flask_view_tree # https://github.com/fenhl/flask-view-tree

DISCORD_MENTION_REGEX = '<@!?([0-9]+)>'
DISCORD_TAG_REGEX = '@([^#]{2,32})#([0-9]{4})'

def child(view, name='wiki', display_string=None, *, edit_decorators=[], md, mentions_to_tags=None, tags_to_mentions=None, user_class, user_class_constructor=None, wiki_name, wiki_root, **options):
    return setup(view.view_func_node.app, edit_decorators, md, mentions_to_tags, tags_to_mentions, user_class, user_class_constructor, wiki_name, wiki_root, view.child(name, display_string, **options))

def index(app, *, edit_decorators=[], md, mentions_to_tags=None, tags_to_mentions=None, user_class, user_class_constructor=None, wiki_root, **options):
    return setup(app, edit_decorators, md, mentions_to_tags, tags_to_mentions, user_class, user_class_constructor, wiki_name, wiki_root, flask_view_tree.index(app, **options))

def render_template(template_name, **kwargs):
    if template_name is None:
        template_path = f'{flask.request.endpoint.replace(".", "/")}.html.j2'
    else:
        template_path = f'{template_name.replace(".", "/")}.html.j2'
    return jinja2.Markup(flask.render_template(template_path, **kwargs))

def setup(app, edit_decorators, md, mentions_to_tags, tags_to_mentions, user_class, user_class_constructor, wiki_name, wiki_root, decorator):
    if user_class_constructor is None:
        user_class_constructor = user_class

    class DiscordMentionPattern(markdown.inlinepatterns.LinkInlineProcessor):
        def handleMatch(self, m, data):
            user = user_class_constructor(m.group(1))
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
        if namespace in wiki_index.redirect_namespaces:
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

    def WikiEditForm(prev_source):
        class Form(flask_wtf.FlaskForm):
            source = MarkdownField('Text', default=prev_source)
            submit_wiki_edit_form = wtforms.SubmitField('Save')

        return Form()

    @wiki_article_namespaced.child('edit', methods=['GET', 'POST'], decorators=edit_decorators)
    def wiki_article_edit(title, namespace):
        exists = wiki_index.exists(namespace, title)
        if exists:
            source = wiki_index.source(namespace, title)
        elif wiki_index.namespace_exists(namespace):
            source = ''
        else:
            return render_template('wiki.namespace-404', namespace=namespace, wiki_name=wiki_name), 404
        wiki_edit_form = WikiEditForm(source)
        if wiki_edit_form.submit_wiki_edit_form.data and wiki_edit_form.validate():
            wiki_index.save(namespace, title, wiki_edit_form.source.data)
            return flask.redirect(flask.g.view_node.parent.url)
        return render_template('wiki.edit', exists=exists, title=title, namespace=namespace, wiki_name=wiki_name, wiki_edit_form=wiki_edit_form)

    @wiki_article_namespaced.child('history')
    def wiki_article_history(title, namespace):
        return render_template('wiki.history', title=title, namespace=namespace)

    @app.before_request
    def current_time():
        flask.g.wiki = wiki_index

    if mentions_to_tags is None:
        def mentions_to_tags(text):
            while True:
                match = re.search(DISCORD_MENTION_REGEX, text)
                if not match:
                    return text
                text = f'{text[:match.start()]}@{user_class_constructor(match.group(1))}{text[match.end():]}'

    if tags_to_mentions is None:
        def tags_to_mentions(text):
            while True:
                match = re.search(DISCORD_TAG_REGEX, text)
                if not match:
                    return text
                text = f'{text[:match.start()]}<@{user_class.by_tag(match.group(1), int(match.group(2))).snowflake}>{text[match.end():]}'

    def exists(namespace, title):
        article_path = wiki_root / namespace / f'{title}.md'
        return article_path.exists()

    def namespace_exists(namespace):
        return (wiki_root / namespace).exists()

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

    wiki_index.MarkdownField = MarkdownField
    wiki_index.WikiEditForm = WikiEditForm
    wiki_index.exists = exists
    wiki_index.mentions_to_tags = mentions_to_tags
    wiki_index.namespace_exists = namespace_exists
    wiki_index.namespaces = namespaces
    wiki_index.save = save
    wiki_index.source = source
    wiki_index.tags_to_mentions = tags_to_mentions

    return wiki_index
