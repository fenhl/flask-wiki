This package can be used to host a wiki on a [flask-view-tree](https://github.com/fenhl/flask-view-tree)-based website.

# Usage

First, symlink `wiki` inside your template folder to the `templates` directory in this repository, or write your own versions of these templates. If you choose the first option, make sure you have a template called `base.html.j2` that the wiki templates can extend.

There are two ways to integrate flask-wiki into your website:

* If you want your website's index page (`/`) to be the wiki main page, just call `flask_wiki.index(app)` instead of writing an index node decorated with `flask_view_tree.index(app)`.
* If you want the wiki main page to be a subpage of a `view`, register it by calling `flask_wiki.child(view)` instead of writing a child view decorated with `view.child()`. The node name is optional and defaults to `'wiki'`.

Both of these functions have some required keyword-only arguments:

* `md` should be an instance of `flaskext.markdown.Markdown`. An extension that can parse Discord mentions will be registered on it.
* `user_class` should be a subclass of `flask_login.UserMixin` with the class method `by_tag` which takes a Discord username and discriminator and returns an instance, and the instance attributes (or properties) `name` (for the Discord nickname) and `profile_url` (for the page to which a Discord mention should link).
* `wiki_name` will be used in `<title>` tags as the name of the wiki.
* `wiki_root` should be an instance of `pathlib.Path` representing the directory where wiki articles will be saved. Each namespace will be in its own subdirectory.

As well as some optional ones:

* `edit_decorators` is a list of decorators that will be added to the edit view (which is also used to create a new article). It defaults to an empty list.
* `mentions_to_tags` is a function that takes a Markdown string and returns the same string except with user mentions replaced with a more user-friendly syntax. By default this converts Discord mentions like `<@86841168427495424>` to Discord tags like `@Fenhl#4813`.
* `tags_to_mentions` is the inverse of `mentions_to_tags`.
* `user_class_constructor` is a function that constructs an instance of `user_class` from the snowflake in a user mention. It defaults to `user_class`.

## The wiki object

The view function node representing the wiki index has a few extra attributes defined on it. It can be accessed as the return value of the `flask_wiki.child` or `flask_wiki.index` call, or as `g.wiki`.

* `wiki.exists(namespace, title)` returns whether that article exists.
* `wiki.namespace_exists(namespace)` returns whether that namespace exists.
* `wiki.namespaces()` returns an iterator over pairs of namespaces and all articles in that namespace.
* `wiki.redirect_namespaces` is a dictionary mapping namespaces to functions that take an article name and return the URL to which the namespaced article node should redirect. By default, all articles in the `wiki` namespace are redirected to their respective unnamespaced article node.
* `wiki.save(namespace, title, text)` save that text as that article's new Markdown source.
* `wiki.source(namespace, title)` returns that article's Markdown source. Raises FileNotFoundError if the article doesn't exist.
