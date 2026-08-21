# importing each module registers its Mod subclass via @register
from . import (boot_animation, splash_logo, font_swap, airpods_fix,  # noqa: F401
               sbc_xq, bt_monitor, nvp_flags,
               wm1_settings, contents_cleaner, full_backup, storage_info,
               boot_log, reboot_util, clock_fix)
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
