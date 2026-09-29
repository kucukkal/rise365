import 'api_service.dart';

class AuthApi {
  static Future<Map<String, dynamic>> sendOtp({
    required String phone,
    required String signupCode,
  }) async {
    final response = await ApiService.dio.post('/auth/send-otp', data: {
      'phone': phone,
      'signup_code': signupCode,
    });
    return response.data;
  }

  static Future<Map<String, dynamic>> verifyOtp({
    required String phone,
    required String code,
  }) async {
    final response = await ApiService.dio.post('/auth/verify-otp', data: {
      'phone': phone,
      'code': code,
    });
    return response.data;
  }

  static Future<Map<String, dynamic>> register({
    required String phone,
    required String name,
    required String programLevelId,
    String? firstName,
    String? lastName,
  }) async {
    final response = await ApiService.dio.post('/auth/register', data: {
      'phone': phone,
      'name': name,
      'program_level_id': programLevelId,
      if (firstName != null) 'first_name': firstName,
      if (lastName != null) 'last_name': lastName,
    });
    if (response.data['access_token'] != null) {
      await ApiService.saveToken(response.data['access_token']);
    }
    return response.data;
  }
}
