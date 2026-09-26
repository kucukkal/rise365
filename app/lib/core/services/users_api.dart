import 'api_service.dart';

class UsersApi {
  static Future<Map<String, dynamic>> getProfile() async {
    final response = await ApiService.dio.get('/users/me');
    return response.data;
  }

  static Future<Map<String, dynamic>> getProgress() async {
    final response = await ApiService.dio.get('/users/progress');
    return response.data;
  }

  static Future<void> updateFcmToken(String token) async {
    await ApiService.dio.put('/users/fcm-token', queryParameters: {'fcm_token': token});
  }
}