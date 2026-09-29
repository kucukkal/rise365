import 'package:flutter/material.dart';

/// Colors for each prayer card, following the sky through the day.
/// accent = border / icon / checkbox, tint = card background.
class PrayerTheme {
  final Color accent;
  final Color tint;
  final IconData icon;
  const PrayerTheme(this.accent, this.tint, this.icon);

  /// Darker shade of the accent, readable as text on the tint.
  Color get ink {
    final hsl = HSLColor.fromColor(accent);
    return hsl.withLightness((hsl.lightness * 0.7).clamp(0.0, 1.0)).toColor();
  }

  static const _byName = <String, PrayerTheme>{
    // Dawn: soft violet sky before sunrise
    'fajr': PrayerTheme(
        Color(0xFF7A5CC2), Color(0xFFF1ECFA), Icons.wb_twilight_rounded),
    // Midday: clear bright sky under the high sun
    'dhuhr': PrayerTheme(
        Color(0xFF1F8FD6), Color(0xFFE6F3FC), Icons.wb_sunny_rounded),
    // Afternoon: warm golden light
    'asr': PrayerTheme(
        Color(0xFFD98E04), Color(0xFFFDF3DF), Icons.light_mode_rounded),
    // Sunset: coral and rose
    'maghrib': PrayerTheme(
        Color(0xFFE0604A), Color(0xFFFCEBE6), Icons.wb_twilight_rounded),
    // Night: deep midnight blue
    'isha': PrayerTheme(
        Color(0xFF1B2152), Color(0xFFD0D5EC), Icons.nightlight_round),

    // Voluntary prayers (higher levels)
    // Duha, mid-morning: fresh morning teal
    'duha': PrayerTheme(
        Color(0xFF16A394), Color(0xFFE3F6F3), Icons.wb_sunny_outlined),
    // Awwabin, after Maghrib: dusky plum
    'awwabin': PrayerTheme(
        Color(0xFF9C4F8F), Color(0xFFF7EAF4), Icons.wb_twilight_rounded),
    // Qiyam, late night: deep indigo
    'qiyam': PrayerTheme(
        Color(0xFF45308A), Color(0xFFEDE9F7), Icons.bedtime_rounded),
  };

  /// The five daily prayers, in order, for picking the sky of the moment.
  static const dailyOrder = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha'];

  static const _fallback = PrayerTheme(
      Color(0xFF1B7A3E), Color(0xFFE9F4EC), Icons.nightlight_round);

  static PrayerTheme forName(String name) =>
      _byName[name.toLowerCase().trim()] ?? _fallback;
}
