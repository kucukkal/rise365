import 'dart:async';
import 'package:flutter/material.dart';

/// Tracks which prayer is currently active (within prayer time window)
class PrayerTimeService {
  static final PrayerTimeService _instance = PrayerTimeService._internal();
  factory PrayerTimeService() => _instance;
  PrayerTimeService._internal();

  // Notifier for active prayer name
  final ValueNotifier<String?> activePrayerNotifier = ValueNotifier(null);

  Timer? _timer;
  List<Map<String, dynamic>> _prayers = [];

  void startMonitoring(List<Map<String, dynamic>> prayers) {
    _prayers = prayers;
    _timer?.cancel();
    _checkPrayerTimes();
    // Check every minute
    _timer = Timer.periodic(const Duration(minutes: 1), (_) {
      _checkPrayerTimes();
    });
  }

  void _checkPrayerTimes() {
    final now = TimeOfDay.now();
    String? activePrayer;

    for (final prayer in _prayers) {
      if (prayer['is_completed'] == true) continue;

      final timeStr = prayer['time'] as String? ?? '';
      if (timeStr.isEmpty) continue;

      try {
        final prayerTime = _parseTime(timeStr);
        final diffMinutes = _diffMinutes(now, prayerTime);

        // Prayer is "active" if within 0-30 minutes after prayer time
        if (diffMinutes >= 0 && diffMinutes <= 30) {
          activePrayer = prayer['name'] as String?;
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (activePrayerNotifier.value != activePrayer) {
      activePrayerNotifier.value = activePrayer;
    }
  }

  TimeOfDay _parseTime(String timeStr) {
    // Parse "5:12 AM" or "1:07 PM"
    final parts = timeStr.split(' ');
    final timeParts = parts[0].split(':');
    int hour = int.parse(timeParts[0]);
    final minute = int.parse(timeParts[1]);
    final isPM = parts.length > 1 && parts[1] == 'PM';
    final isAM = parts.length > 1 && parts[1] == 'AM';
    if (isPM && hour != 12) hour += 12;
    if (isAM && hour == 12) hour = 0;
    return TimeOfDay(hour: hour, minute: minute);
  }

  int _diffMinutes(TimeOfDay now, TimeOfDay prayer) {
    final nowMins = now.hour * 60 + now.minute;
    final prayerMins = prayer.hour * 60 + prayer.minute;
    return nowMins - prayerMins;
  }

  void stop() {
    _timer?.cancel();
    activePrayerNotifier.value = null;
  }
}

final prayerTimeService = PrayerTimeService();
