from .author import AuthorAutoCompleteQuery
from .topic import TopicAutoCompleteQuery


class AutoComplete(AuthorAutoCompleteQuery, TopicAutoCompleteQuery):
    """Inherits the queries of word completion"""
