# importing each module registers its Mod subclass via @register
from . import (boot_animation, splash_logo, font_swap, airpods_fix,  # noqa: F401
               sbc_xq, bt_monitor, nvp_flags,
               wm1_settings, contents_cleaner, full_backup, storage_info,
               boot_log, reboot_util, clock_fix, library_stats, find_duplicates)
# ui_recolor RE-ENABLED 2026-08-20: NOT integrity-checked after all — the earlier bootloop was collapsing
# all 5 icon presets to one identical value. Proven-safe recipe (accent + DEFAULT icon, others distinct)
# verified booting on-device. Text stays white (C++ viewstyle theme; deep RE target).
from . import ui_recolor  # noqa: F401
# ui_themer (2026-08-20): the C++ "viewstyle" text/bg palette IS themeable after all — reached via
# Ghidra (headless). Redirects the QML palette bindings every screen reads. Any-color, per-element.
from . import ui_themer  # noqa: F401
# ldac_quality (2026-08-20): force LDAC 990 / disable ABR downgrade. Found via Ghidra — the ABR
# calls ldac_alter_qmode_priority(h,-1) to lower quality; patch beq.w->ble.w in the validity gate
# blocks only the -1 (downgrade) direction. libldacBTBC.so, reversible binpatch.
from . import ldac_quality  # noqa: F401
# marquee_speed (2026-08-20): tune the long-title scroll speed. QML divisors `/ 3.1` (X) `/ 3.9` (Y);
# higher = faster. Uses viewstyle.patch strmap. Reversible app edit.
from . import marquee_speed  # noqa: F401
# alt_theme (2026-08-20): flip viewstyle.mode "normal"->"reverse" (8 sites + default) to switch the
# whole UI to the firmware's second palette. Reversible; experimental (look = the reverse scheme).
from . import alt_theme  # noqa: F401
