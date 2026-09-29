import 'package:flutter/material.dart';

/// Background colors for task bars.
/// Content tasks use the color of the PDF page they open;
/// every other task gets a soft color from a shared palette.
/// accent = border / checkbox ring, tint = bar background.
class TaskTheme {
  final Color accent;
  final Color tint;
  const TaskTheme(this.accent, this.tint);

  /// Darker shade of the accent, readable as text on the tint.
  Color get ink {
    final hsl = HSLColor.fromColor(accent);
    return hsl.withLightness((hsl.lightness * 0.7).clamp(0.0, 1.0)).toColor();
  }

  // Content tasks: first keyword found in the title wins.
  static const _byKeyword = <String, TaskTheme>{
    'knowledge': TaskTheme(Color(0xFFD9A900), Color(0xFFFFF6D8)), // gold
    'quran':     TaskTheme(Color(0xFF1B7A3E), Color(0xFFE9F4EC)), // green
    'dhikr':     TaskTheme(Color(0xFF1E6FD9), Color(0xFFE7F0FC)), // blue
    'dua':       TaskTheme(Color(0xFFE2700A), Color(0xFFFDEEDF)), // orange
    'seerah':    TaskTheme(Color(0xFF6E3AA8), Color(0xFFF1EAF8)), // navy
    'hadith':    TaskTheme(Color(0xFF1A2B6B), Color(0xFFEBEEF7)), // navy
    'prophet':   TaskTheme(Color(0xFF1A2B6B), Color(0xFFEBEEF7)), // navy
  };

  // Other tasks: colors chosen to sit well beside the ones above
  // without repeating them.
  static const _palette = <TaskTheme>[
    TaskTheme(Color(0xFF0F8A8A), Color(0xFFE3F4F3)), // teal
    TaskTheme(Color(0xFF7B4FA0), Color(0xFFF2EBF8)), // plum
    TaskTheme(Color(0xFFC2476B), Color(0xFFFCEBF0)), // rose
    TaskTheme(Color(0xFF5F7F3A), Color(0xFFEFF4E7)), // sage
    TaskTheme(Color(0xFF8A6A3D), Color(0xFFF6F0E6)), // sand
  ];

  static TaskTheme forTitle(String title) {
    final t = title.toLowerCase().replaceAll(RegExp(r'[^a-z]'), '');
    for (final entry in _byKeyword.entries) {
      if (t.contains(entry.key)) return entry.value;
    }
    // Same title always gets the same color, on every device and launch.
    var hash = 0;
    for (final c in t.codeUnits) {
      hash = (hash * 31 + c) & 0x7fffffff;
    }
    return _palette[hash % _palette.length];
  }
}
