"""Ask Tiresias: a grounded text-to-SQL chat over the Portland marts.

The engine, prompts, SQL guard and abuse guards live in the pinned ``tiresias``
library; this page points it at ``tiresias.yml``. Without an ``ANTHROPIC_API_KEY``
the page shows a notice and stops. Caps can be tuned with ``TIRESIAS_MAX_*``.
"""

from pathlib import Path

from tiresias.chat import render_chat
from tiresias.config import load_config

render_chat(load_config(Path(__file__).resolve().parents[1] / "tiresias.yml"))
