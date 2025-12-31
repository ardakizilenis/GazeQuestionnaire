TYPE_COLOR_THEMES: dict[str, dict[str, dict[str, str]]] = {
    "neon": {
        "info":     {"bg": "#0F1838", "accent": "#66F0FF", "fg": "#EAF2FF"},
        "yesno":    {"bg": "#0F172A", "accent": "#3B82F6", "fg": "#EAF2FF"},
        "mcq":      {"bg": "#071A18", "accent": "#39FF9A", "fg": "#EAF2FF"},
        "likert":   {"bg": "#1B0B22", "accent": "#FF4FD8", "fg": "#FFE6FB"},
        "textgrid": {"bg": "#231A05", "accent": "#F59E0B", "fg": "#FFF7ED"},
        "sp_yesno": {"bg": "#0B1330", "accent": "#9B7CFF", "fg": "#EAF2FF"},
        "sp_mcq":   {"bg": "#0B1330", "accent": "#39FF9A", "fg": "#EAF2FF"},
        "sp_likert":{"bg": "#0B1330", "accent": "#FB7185", "fg": "#FFE4E6"},
    },

    "retro_terminal": {
        "info":     {"bg": "#06180E", "accent": "#00FF66", "fg": "#C8FFD9"},
        "yesno":    {"bg": "#03140A", "accent": "#00E85A", "fg": "#BFFFD0"},
        "mcq":      {"bg": "#072014", "accent": "#7CFF00", "fg": "#D7FFB8"},
        "likert":   {"bg": "#04160C", "accent": "#00FFA2", "fg": "#C6FFE9"},
        "textgrid": {"bg": "#051A10", "accent": "#FFD700", "fg": "#FFF6B3"},
        "sp_yesno": {"bg": "#04140B", "accent": "#00FF66", "fg": "#C8FFD9"},
        "sp_mcq":   {"bg": "#04140B", "accent": "#7CFF00", "fg": "#D7FFB8"},
        "sp_likert":{"bg": "#04140B", "accent": "#00FFA2", "fg": "#C6FFE9"},
    },

    "clinical": {
        "info":     {"bg": "#F3F7FF", "accent": "#2563EB", "fg": "#0F172A"},
        "yesno":    {"bg": "#EEF6FF", "accent": "#1D4ED8", "fg": "#0F172A"},
        "mcq":      {"bg": "#F0FDF9", "accent": "#0EA5A4", "fg": "#0F172A"},
        "likert":   {"bg": "#FFF5F7", "accent": "#E11D48", "fg": "#0F172A"},
        "textgrid": {"bg": "#FFFBF2", "accent": "#F59E0B", "fg": "#0F172A"},
        "sp_yesno": {"bg": "#F4F6FF", "accent": "#7C3AED", "fg": "#0F172A"},
        "sp_mcq":   {"bg": "#F0FDF9", "accent": "#059669", "fg": "#064E3B"},
        "sp_likert":{"bg": "#FFF1F2", "accent": "#FB7185", "fg": "#0F172A"},
    },

    "oled_dark": {
        "info":     {"bg": "#000000", "accent": "#3B82F6", "fg": "#E5E7EB"},
        "yesno":    {"bg": "#000000", "accent": "#60A5FA", "fg": "#E5E7EB"},
        "mcq":      {"bg": "#000000", "accent": "#22C55E", "fg": "#DCFCE7"},
        "likert":   {"bg": "#000000", "accent": "#F472B6", "fg": "#FCE7F3"},
        "textgrid": {"bg": "#000000", "accent": "#F59E0B", "fg": "#FFF7ED"},
        "sp_yesno": {"bg": "#000000", "accent": "#A78BFA", "fg": "#E5E7EB"},
        "sp_mcq":   {"bg": "#000000", "accent": "#34D399", "fg": "#D1FAE5"},
        "sp_likert":{"bg": "#000000", "accent": "#FB7185", "fg": "#FFE4E6"},
    }
}
