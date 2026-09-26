enum TaskFrequency { daily, weekly, monthly }
enum TaskInfoType { none, text, image, video }

class TaskModel {
  final String id;
  final String title;
  final String? description;
  final TaskFrequency frequency;
  bool isCompleted;
  final int points;
  final TaskInfoType infoType;
  final String? infoContent;

  TaskModel({
    required this.id,
    required this.title,
    this.description,
    required this.frequency,
    this.isCompleted = false,
    required this.points,
    this.infoType = TaskInfoType.none,
    this.infoContent,
  });
}