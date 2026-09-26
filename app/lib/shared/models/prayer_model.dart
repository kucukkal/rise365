class PrayerModel {
  final String name;
  final String displayName;
  final String arabicName;
  final String time;
  bool isCompleted;
  bool isLocked;
  bool windowExpired;
  int? minutesLeft;
  final int points;
  final bool evradRequired;
  bool evradCompleted;
  final String evradName;
  final int evradPoints;

  PrayerModel({
    required this.name,
    required this.displayName,
    required this.arabicName,
    required this.time,
    this.isCompleted = false,
    this.isLocked = false,
    this.windowExpired = false,
    this.minutesLeft,
    required this.points,
    this.evradRequired = false,
    this.evradCompleted = false,
    this.evradName = '',
    this.evradPoints = 20,
  });

  factory PrayerModel.fromJson(Map<String, dynamic> json) {
    return PrayerModel(
      name: json['name']?.toString() ?? '',
      displayName: json['display_name']?.toString() ?? '',
      arabicName: json['arabic_name']?.toString() ?? '',
      time: json['time']?.toString() ?? '',
      isCompleted: json['is_completed'] ?? false,
      isLocked: json['is_locked'] ?? false,
      windowExpired: json['window_expired'] ?? false,
      minutesLeft: json['minutes_left'],
      points: json['points'] ?? 10,
      evradRequired: json['evrad_required'] ?? false,
      evradCompleted: json['evrad_completed'] ?? false,
      evradName: json['evrad_name']?.toString() ?? '',
      evradPoints: json['evrad_points'] ?? 20,
    );
  }
}
