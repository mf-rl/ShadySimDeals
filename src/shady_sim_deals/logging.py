"""Small game-safe structured logger."""

import json
import os
import traceback


class ModLogger:
    PREFIX = "[ShadySimDeals]"

    def __init__(self, path=None):
        self._path = path or os.path.join(
            os.path.expanduser("~"),
            "Documents",
            "Electronic Arts",
            "The Sims 4",
            "shady_sim_deals.log",
        )

    def log(self, event, **fields):
        record = {"event": str(event)}
        record.update(fields)
        line = "{} {}\n".format(self.PREFIX, json.dumps(record, sort_keys=True))
        try:
            with open(self._path, "a") as handle:
                handle.write(line)
        except Exception:
            pass

    def exception(self, event, **fields):
        fields["traceback"] = traceback.format_exc()
        self.log(event, **fields)
