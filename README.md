This package can be used to host a wiki on a [flask-view-tree](https://github.com/fenhl/flask-view-tree)-based website.

# Usage

First, symlink `wiki` inside your template folder to the `templates` directory in this repository, or write your own versions of these templates. If you choose the first option, make sure you have a template called `base.html.j2` that the wiki templates can extend.

There are two ways to integrate flask-wiki into your website:

* If you want your website's index page (`/`) to be the wiki main page, just call `flask_wiki.index(app)` instead of writing an index node decorated with `flask_view_tree.index(app)`.
* If you want the wiki main page to be a subpage of a `view`, register it by calling `flask_wiki.child(view)` instead of writing a child view decorated with `view.child()`. The node name is optional and defaults to `'wiki'`.

Both of these functions have some required keyword-only arguments:

* `md` should be an instance of `flaskext.markdown.Markdown`. An extension that can parse Discord mentions will be registered on it.
* `user_class` should be a subclass of `flask_login.UserMixin` with the class method `by_tag` which takes a Discord username and discriminator and returns an instance, and the following instance attributes (or properties):
    * `name` for the Discord nickname
    * `profile_url` for the page to which a Discord mention should link
    * `snowflake` for the Discord user ID
    * optionally, a `__html__` or `__str__` representation
* `wiki_name` will be used in `<title>` tags as the name of the wiki.

Exactly one of the following keyword-only arguments must be provided:

* `db`, an instance of `flask_sqlalchemy.SQLAlchemy` whose `wiki` table will be used to store articles, and whose `wiki_namespaces` table will be used to track which namespaces exist.
* `wiki_root`, an instance of `pathlib.Path` representing the directory where wiki articles will be saved. Each namespace will be in its own subdirectory. Edit history will not be saved.

The script `flask_wiki/migrate.py` in this repository can be used to migrate a wiki database from the `wiki_root` backend to the `db` backend.

There are also the following optional keyword arguments:

* `current_user` is a function that returns the user currently viewing this page, as an instance of `user_class`. Defaults to returning `flask.g.user`. Only used by the `db` backend.
* `edit_decorators` is a list of decorators that will be added to the edit view (which is also used to create a new article). It defaults to an empty list.
* `mentions_to_tags` is a function that takes a Markdown string and returns the same string except with user mentions replaced with a more user-friendly syntax. By default this converts Discord mentions like `<@86841168427495424>` to Discord tags like `@Fenhl#4813`.
* `tags_to_mentions` is the inverse of `mentions_to_tags`.
* `user_class_constructor` is a function that constructs an instance of `user_class` from the snowflake in a user mention. It defaults to `user_class`.

Any remaining keyword arguments will be passed through to `flask_view_tree.index` or `view.child`.

## The wiki object

The view function node representing the wiki index has a few extra attributes defined on it. It can be accessed as the return value of the `flask_wiki.child` or `flask_wiki.index` call, or as `g.wiki`.

* `wiki.MarkdownField` is a subclass of `flask_pagedown.fields.PageDownField` that handles `mentions_to_tags` and `tags_to_mentions` automatically.
* `wiki.WikiEditForm()` returns an instance of a subclass of `flask_wtf.FlaskForm` with the fields `source` (a `MarkdownField`) and `submit_wiki_edit_form` (a `wtforms.SubmitField`).
* `wiki.exists(namespace, title)` returns whether that article exists.
* `wiki.history(namespace, title)` returns an iterable of revisions of that article, in chronological order. The method only exists if the `db` backend is used. A revision has the following attributes:
    * `author`, either `None` or an instance of `user_class` representing the user who submitted this revision
    * `id`, an `int` uniquely identifying this revision
    * `namespace` of the article
    * `summary`, either `None` or a `str`
    * `text`
    * `timestamp`, a timezone-aware `datetime`
    * `title` of the article
* `wiki.mentions_to_tags` is the function passed to the setup function, or its default fallback.
* `wiki.namespace_exists(namespace)` returns whether that namespace exists.
* `wiki.namespaces()` returns an iterator over pairs of namespaces and all articles in that namespace.
* `wiki.redirect_namespaces` is a dictionary mapping namespaces to functions that take an article name and return the URL to which the namespaced article node should redirect. By default, all articles in the `wiki` namespace are redirected to their respective unnamespaced article node.
* `wiki.save(namespace, title, text, author=None, summary=None)` saves that text as that article's new Markdown source. `author`, if given, should be an instance of `user_class`. `author` and `summary` are ignored by the `wiki_root` backend.
* `wiki.source(namespace, title)` returns that article's Markdown source. Raises FileNotFoundError if the article doesn't exist.
* `wiki.tags_to_mentions` is the function passed to the setup function, or its default fallback.
