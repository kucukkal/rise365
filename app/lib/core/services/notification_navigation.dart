import 'package:flutter/material.dart';

class NotificationNavigation {
  final int tabIndex;
  final String frequency; // daily, weekly, monthly, prayer

  const NotificationNavigation({
    required this.tabIndex,
    this.frequency = 'daily',
  });
}

/// Global notifier for switching tabs from notifications
final ValueNotifier<NotificationNavigation> notificationTabNotifier =
    ValueNotifier<NotificationNavigation>(
        const NotificationNavigation(tabIndex: 0));

void navigateToTab(int index, {String frequency = 'daily'}) {
  notificationTabNotifier.value =
      NotificationNavigation(tabIndex: index, frequency: frequency);
}
