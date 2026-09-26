import 'api_service.dart';

class TasksApi {
  static Future<List<dynamic>> getTasks({String? frequency}) async {
    final response = await ApiService.dio.get(
      '/tasks/',
      queryParameters: frequency != null ? {'frequency': frequency} : null,
    );
    return response.data;
  }

  static Future<Map<String, dynamic>> completeTask(String taskId) async {
    final response = await ApiService.dio.post('/tasks/complete', data: {
      'task_id': taskId,
    });
    return response.data;
  }
}