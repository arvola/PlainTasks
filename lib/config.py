
default_config = {
    'pending_task': '☐',
    'completed_task': '✔',
    'cancelled_task': '✘',
    'date_format': '%y-%m-%d %H:%M',
    'completed_tag': 'done',
    'cancelled_tag': 'cancelled',
    'completed_date': True,
    'cancelled_date': True,
    'archive_section': 'Archive',
    'archive_cancelled_tasks': True
}

class Config:
    def __init__(self, view):
        self._settings = view.settings()

    def __getattr__(self, name):
        value = self._settings.get(name)
        if value is None:
            value = default_config[name]
        if value is None:
            raise AttributeError("Setting '%s' does not exist" % name)
        return value

    def indent(self):
        """ Returns one level of indent as a string.
        """
        return " " * self._settings.get("tab_size")

_config = None

def get_config(view):
    global _config
    if _config is None:
        _config = Config(view)
    return _config