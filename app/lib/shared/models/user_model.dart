class UserModel {
  final String id;
  final String name;
  final String phone;
  final String programLevel;
  final int totalPoints;
  final double completionRate;

  const UserModel({
    required this.id,
    required this.name,
    required this.phone,
    required this.programLevel,
    this.totalPoints = 0,
    this.completionRate = 0.0,
  });

  String get achievementLevel {
    if (completionRate >= 91) return 'Diamond';
    if (completionRate >= 81) return 'Sapphire';
    if (completionRate >= 71) return 'Gold';
    if (completionRate >= 60) return 'Silver';
    if (completionRate >= 50) return 'Bronze';
    return 'Starter';
  }
}